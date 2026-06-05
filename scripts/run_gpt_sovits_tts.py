"""
GPT-SoVITS TTS 配音生成器
直接调用 GPT-SoVITS TTS 类进行推理（零样本音色克隆）
用法: python run_gpt_sovits_tts.py <项目路径> --ref-wav 路径 [--output 文件名]
"""
import sys, os, gc, warnings
warnings.filterwarnings("ignore")

GPT_SOVITS_DIR = "/tmp/GPT-SoVITS"
sys.path.insert(0, GPT_SOVITS_DIR)
sys.path.insert(0, os.path.join(GPT_SOVITS_DIR, "GPT_SoVITS"))
os.chdir(GPT_SOVITS_DIR)

import torch
import numpy as np
import soundfile as sf
from TTS_infer_pack.TTS import TTS_Config, TTS

# 防止 g2pw 检查（已 patch cleaner.py，使用 chinese.py 替代 chinese2.py）
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def run_tts(project_dir, ref_wav=None, output_name="配音_gpt.wav"):
    if ref_wav is None:
        ref_wav = os.path.join(project_dir, "参考音频_1.wav")

    # 读取文案
    text_path = os.path.join(project_dir, "文案.txt")
    tts_text = ""
    if os.path.exists(text_path):
        with open(text_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        tts_text = "".join(lines)
    if not tts_text:
        tts_text = "这是一台极品车况的二手车。"

    assert os.path.exists(ref_wav), f"参考音频不存在: {ref_wav}"

    print(f"[GPT-SoVITS] 参考音频: {ref_wav}")
    print(f"[GPT-SoVITS] 文案: {tts_text[:60]}...")

    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in tts_text)
    text_lang = "zh" if has_chinese else "en"

    # 加载配置
    config_path = os.path.join(GPT_SOVITS_DIR, "GPT_SoVITS/configs/tts_infer_custom.yaml")
    tts_config = TTS_Config(config_path)

    # 初始化 TTS
    print("[GPT-SoVITS] 初始化 TTS 引擎...")
    tts = TTS(tts_config)

    output_path = os.path.join(project_dir, output_name)
    print("[GPT-SoVITS] 推理中...")

    ref_wav_abs = os.path.abspath(ref_wav)

    # GPT-SoVITS 的 tts.run() 自动使用 ASR 从参考音频提取 prompt_text，所以传空字符串即可
    inputs = {
        "text": tts_text,
        "text_lang": text_lang,
        "ref_audio_path": ref_wav_abs,
        "prompt_text": "",
        "prompt_lang": text_lang,
        "top_k": 15,
        "top_p": 1.0,
        "temperature": 1.0,
        "text_split_method": "cut5",
        "batch_size": 1,
        "batch_threshold": 0.75,
        "split_bucket": True,
        "speed_factor": 1.0,
        "fragment_interval": 0.3,
        "seed": -1,
        "parallel_infer": True,
        "repetition_penalty": 1.35,
        "sample_steps": 32,
        "super_sampling": False,
        "streaming_mode": False,
        "return_fragment": False,
    }

    tts_generator = tts.run(inputs)
    sr, audio_data = next(tts_generator)

    # 处理多段 fragment
    for extra_sr, extra_audio in tts_generator:
        if isinstance(audio_data, np.ndarray) and isinstance(extra_audio, np.ndarray):
            audio_data = np.concatenate([audio_data, extra_audio])
        else:
            audio_data = extra_audio
        sr = extra_sr

    if isinstance(audio_data, torch.Tensor):
        audio_np = audio_data.cpu().numpy()
    else:
        audio_np = np.array(audio_data)

    if audio_np.ndim > 1:
        audio_np = audio_np.squeeze()

    sf.write(output_path, audio_np, int(sr))
    dur = len(audio_np) / sr
    print(f"[GPT-SoVITS] 配音已保存: {output_path} ({dur:.1f}s)")

    del tts
    gc.collect()
    if hasattr(torch, 'mps') and hasattr(torch.mps, 'empty_cache'):
        torch.mps.empty_cache()

    return 0


def main():
    if len(sys.argv) < 2:
        print("用法: python run_gpt_sovits_tts.py <项目路径> [--ref-wav 路径] [--output 文件名]")
        sys.exit(1)

    project_dir = os.path.abspath(sys.argv[1])
    ref_wav = None
    output_name = "配音_gpt.wav"

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--ref-wav" and i + 1 < len(sys.argv):
            ref_wav = os.path.abspath(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output_name = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    sys.exit(run_tts(project_dir, ref_wav, output_name))


if __name__ == "__main__":
    main()
