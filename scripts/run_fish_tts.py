"""
Fish Speech 1.5 TTS 配音生成器（完整版 v6 - 使用 v1.5 tokenizer）
"""
import sys, os, io, queue, warnings, gc, re, copy, json
from pathlib import Path

ENV_SITE = "/Users/nj/Documents/短视频创作/env/lib/python3.13/site-packages"
sys.path.insert(0, ENV_SITE)

import numpy as np
import soundfile as sf
import torch
import torchaudio
import hydra
from hydra import compose, initialize_config_dir
from hydra.utils import instantiate
from omegaconf import OmegaConf

warnings.filterwarnings("ignore")
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

from fish_speech.models.text2semantic.inference import (
    launch_thread_safe_queue, GenerateRequest, GenerateResponse, WrappedGenerateResponse,
    init_model, generate, generate_long,
)
from fish_speech.tokenizer import FishTokenizer, IM_END_TOKEN
from fish_speech.conversation import Conversation, Message
from fish_speech.content_sequence import TextPart, VQPart

OmegaConf.register_new_resolver("eval", eval)
MODEL_DIR = os.path.expanduser("~/.cache/fish-speech/models")


def load_vqgan(device):
    config_path = os.path.join(ENV_SITE, "fish_speech", "configs")
    hydra.core.global_hydra.GlobalHydra.instance().clear()
    with initialize_config_dir(config_dir=config_path, version_base="1.3"):
        cfg = compose(config_name="firefly_gan_vq")
    model = instantiate(cfg)
    ckpt_path = os.path.join(MODEL_DIR, "firefly-gan-vq-fsq-8x1024-21hz-generator.pth")
    sd = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    if "state_dict" in sd:
        sd = sd["state_dict"]
    if any("generator" in k for k in sd):
        sd = {k.replace("generator.", ""): v for k, v in sd.items() if "generator." in k}
    model.load_state_dict(sd, strict=False)
    model.eval()
    model.to(device)
    print(f"[VQGAN] Loaded on {device}")
    return model


def encode_ref_audio(vqgan, audio_path, device):
    audio, sr = sf.read(audio_path)
    audio_t = torch.from_numpy(audio).float()
    if sr != 44100:
        audio_t = torchaudio.functional.resample(audio_t, sr, 44100)
    if audio_t.ndim > 1:
        audio_t = audio_t.mean(dim=0)
    audio_t = audio_t.unsqueeze(0).unsqueeze(0).to(device)
    audio_len = torch.tensor([audio_t.shape[-1]], device=device)
    with torch.inference_mode():
        codes, feat_lens = vqgan.encode(audio_t, audio_len)
    print(f"[Encode] Ref: {codes.shape}")
    return codes.squeeze(0)  # (8, T)


def run_tts(project_dir, ref_wav=None, ref_text="", output_name="配音_fish.wav"):
    if ref_wav is None:
        ref_wav = os.path.join(project_dir, "参考音频.wav")
    output_path = os.path.join(project_dir, output_name)
    assert os.path.exists(ref_wav), f"错误: 参考音频 {ref_wav} 不存在"

    text_path = os.path.join(project_dir, "文案.txt")
    tts_text = ""
    if os.path.exists(text_path):
        with open(text_path, "r", encoding="utf-8") as f:
            tts_text = "".join(line.strip() for line in f if line.strip() and not line.startswith("#"))
    if not tts_text:
        tts_text = "这是一台极品车况的二手车。"

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[Fish TTS] 设备: {device}")
    
    precision = torch.float32
    vqgan = load_vqgan(device)
    
    print("[Fish TTS] 编码参考音频...")
    prompt_codes = encode_ref_audio(vqgan, ref_wav, device)
    
    # Load v1.5 tokenizer
    tokenizer = FishTokenizer.from_pretrained(MODEL_DIR)
    print(f"[Fish TTS] 分词器: semantic_ids=[{tokenizer.semantic_begin_id}, {tokenizer.semantic_end_id}]")
    
    print("[Fish TTS] 加载 LLaMA...")
    model, decode_fn = init_model(
        checkpoint_path=MODEL_DIR, device=device, precision=precision,
    )
    model.tokenizer = tokenizer

    # Build conversation
    prompt_text_list = [ref_text or "参考音频"]
    prompt_tokens_list = [prompt_codes.cpu()]
    
    base_conv = Conversation()
    
    # System: reference audio prompt
    tagged = [f"<|speaker:{i}|>{t}" for i, t in enumerate(prompt_text_list)]
    system_parts = [
        TextPart(text="convert the provided text to speech reference to the following:\n\nText:\n", cal_loss=False),
    ]
    system_parts.append(TextPart(text="\n".join(tagged), cal_loss=False))
    system_parts.append(TextPart(text="\n\nSpeech:\n", cal_loss=False))
    all_codes = torch.cat(prompt_tokens_list, dim=1)
    system_parts.append(VQPart(codes=all_codes, cal_loss=False))
    
    base_conv.append(
        Message(role="system", parts=system_parts, cal_loss=False, add_im_start=True, add_im_end=True)
    )
    base_conv.append(
        Message(role="user", parts=[TextPart(text=tts_text, cal_loss=False)], cal_loss=False, add_im_start=True, add_im_end=True)
    )
    
    conv_gen = copy.deepcopy(base_conv)
    conv_gen.append(
        Message(role="assistant", parts=[], cal_loss=False, modality="voice", add_im_start=True, add_im_end=False)
    )
    
    # Encode
    encoded, audio_masks, audio_parts = conv_gen.encode_for_inference(
        tokenizer, num_codebooks=model.config.num_codebooks
    )
    print(f"[Fish TTS] Encoded: {encoded.shape}")
    
    # Generate
    print("[Fish TTS] LLaMA 推理中...")
    codes_seq = generate(
        model=model,
        prompt=encoded.to(device),
        max_new_tokens=512,
        audio_masks=audio_masks.to(device) if audio_masks is not None else None,
        audio_parts=audio_parts.to(device) if audio_parts is not None else None,
        decode_one_token=decode_fn,
        num_samples=1,
        temperature=0.5,
        top_p=0.6,
        top_k=15,
    )
    
    if codes_seq is None or codes_seq.shape[-1] <= encoded.shape[-1]:
        print("[Fish TTS] 错误: 未生成新 tokens")
        return 1
    
    gen_codes = codes_seq[:, encoded.shape[-1]:]  # (9, gen_T)
    vq_codes = gen_codes[1:1+model.config.num_codebooks]  # (8, gen_T)
    print(f"[Fish TTS] 生成: {vq_codes.shape}")
    
    print("[Fish TTS] VQGAN 解码中...")
    with torch.inference_mode():
        vq_codes = vq_codes.unsqueeze(0).to(device)
        feat_lens = torch.tensor([vq_codes.shape[-1]], device=device)
        audio, audio_lens = vqgan.decode(indices=vq_codes, feature_lengths=feat_lens)
    
    audio_np = audio[0, 0].cpu().numpy()
    sr = vqgan.spec_transform.sample_rate
    sf.write(output_path, audio_np, sr)
    dur = len(audio_np) / sr
    print(f"[Fish TTS] 配音已保存: {output_path} ({dur:.1f}s)")
    
    gc.collect()
    return 0


def main():
    if len(sys.argv) < 2:
        print("用法: python run_fish_tts.py <项目路径> [--ref-wav 路径] [--ref-text 文字] [--output 文件名]")
        sys.exit(1)
    project_dir = os.path.abspath(sys.argv[1])
    ref_wav = None
    ref_text = ""
    output_name = "配音_fish.wav"
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--ref-wav" and i + 1 < len(sys.argv):
            ref_wav = os.path.abspath(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--ref-text" and i + 1 < len(sys.argv):
            ref_text = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output_name = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    sys.exit(run_tts(project_dir, ref_wav, ref_text, output_name))

if __name__ == "__main__":
    main()
