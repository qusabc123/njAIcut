"""
裁剪 AI 配音中的静音空隙
每句话独立保存为单独音频文件，输出时间戳供字幕对齐

策略：
  1. 裁剪前先对音频 +10dB 增益，使语音和静音边界更清晰
  2. 用能量阈值检测"原子"说话区间
  3. 用文案句数约束最终段数（段数多了在最短静音处合并，少了在最长静音处分割）
  4. 保存时用原始音频数据写入

用法: python cut_silence.py <项目路径> --input 文件 --output 前缀
  输出: 前缀_001.wav, 前缀_002.wav, ... + 前缀_timestamps.json
"""
import numpy as np
import soundfile as sf
import sys, os, json


def cut_silence(input_path, output_prefix, threshold=0.005, min_silence_ms=500,
                keep_head_ms=100, keep_tail_ms=100, gain_db=10, num_segments=None):
    data, sr = sf.read(input_path)
    total_samples = len(data)
    print(f"原始: {total_samples/sr:.1f}s, 采样率: {sr}Hz" +
          (f", 目标段数: {num_segments}" if num_segments else ""))

    # +10dB 增益，使语音和静音边界更清晰
    gain_linear = 10 ** (gain_db / 20)
    data_gained = data * gain_linear
    max_val = np.abs(data_gained).max()
    if max_val > 1.0:
        data_gained = data_gained / max_val * 0.95
    print(f"增益: +{gain_db}dB")

    frame_size = int(sr * 0.02)
    hop_size = int(sr * 0.005)
    min_atomic_frames = int(min_silence_ms / (hop_size / sr * 1000))

    # 按帧计算能量（使用增益后音频）
    num_frames = (total_samples - frame_size) // hop_size + 1
    energy = np.zeros(num_frames, dtype=np.float32)
    for i in range(num_frames):
        start = i * hop_size
        rms = np.sqrt(np.mean(data_gained[start:start + frame_size] ** 2))
        energy[i] = rms

    is_silent = energy < threshold

    # === 步骤1：检测"原子"说话区间 ===
    in_audio = False
    atomic = []  # [start_frame, end_frame]
    s = 0
    for i in range(len(is_silent)):
        if not is_silent[i] and not in_audio:
            s = i
            in_audio = True
        elif is_silent[i] and in_audio:
            if i - s >= min_atomic_frames:
                atomic.append([s, i])
            in_audio = False
    if in_audio:
        atomic.append([s, len(is_silent)])

    print(f"原子段: {len(atomic)} (静音阈值 {min_silence_ms}ms)")

    if not atomic:
        print("未检测到说话区间")
        return

    # === 步骤2：用文案句数约束 ===
    target_n = num_segments if num_segments else len(atomic)
    segments = [list(a) for a in atomic]

    # 辅助：计算段间帧数间隔
    def frame_gap(seg_list):
        gaps = []
        for i in range(len(seg_list) - 1):
            gap = seg_list[i+1][0] - seg_list[i][1]
            gaps.append((gap, i))
        return gaps

    while len(segments) > target_n:
        # 段数太多：在最短帧数间隔处合并
        gaps = frame_gap(segments)
        gaps.sort()
        _, merge_idx = gaps[0]
        segments[merge_idx][1] = segments[merge_idx + 1][1]
        del segments[merge_idx + 1]

    while len(segments) < target_n:
        # 段数太少：在最长帧数间隔处拆开
        gaps = frame_gap(segments)
        gaps.sort(reverse=True)
        _, split_idx = gaps[0]
        mid = (segments[split_idx][1] + segments[split_idx + 1][0]) // 2
        segments[split_idx][1] = mid
        segments.insert(split_idx + 1, [mid, segments[split_idx][1]])

    print(f"最终段数: {len(segments)} (目标: {target_n})")

    # === 步骤3：保存（使用原始音频） ===
    timestamps = []
    output_dir = os.path.dirname(output_prefix) if os.path.dirname(output_prefix) else '.'
    os.makedirs(output_dir, exist_ok=True)

    for idx, (s, e) in enumerate(segments):
        start_sample = max(0, s * hop_size - int(sr * keep_head_ms / 1000))
        end_sample = min(total_samples, e * hop_size + int(sr * keep_tail_ms / 1000))
        segment_data = data[start_sample:end_sample]

        filename = f"{os.path.basename(output_prefix)}_{idx+1:03d}.wav"
        filepath = os.path.join(output_dir, filename)

        sf.write(filepath, segment_data, sr)
        dur = len(segment_data) / sr

        if idx == 0:
            start_time = 0.0
        else:
            start_time = timestamps[-1]['end']

        timestamps.append({
            "index": idx + 1,
            "file": filename,
            "start": round(start_time, 3),
            "end": round(start_time + dur, 3),
            "duration": round(dur, 3),
        })
        print(f"  第{idx+1:02d}段: {filename} ({dur:.2f}s)")

    ts_path = f"{output_prefix}_timestamps.json"
    with open(ts_path, 'w', encoding='utf-8') as f:
        json.dump(timestamps, f, ensure_ascii=False, indent=2)
    print(f"时间戳: {ts_path}")

    total_dur = timestamps[-1]['end'] if timestamps else 0
    print(f"总时长: {total_dur:.1f}s ({len(timestamps)} 段)")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python cut_silence.py <项目路径> --input 文件 --output 前缀 [--num-segments N]")
        sys.exit(1)

    project_dir = os.path.abspath(sys.argv[1])
    input_name = '配音_fish.wav'
    output_prefix = None
    threshold = 0.005
    num_segments = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--input' and i + 1 < len(sys.argv):
            input_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_prefix = os.path.join(project_dir, sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--num-segments' and i + 1 < len(sys.argv):
            num_segments = int(sys.argv[i + 1])
            i += 2
        else:
            try:
                threshold = float(sys.argv[i])
            except ValueError:
                pass
            i += 1

    input_wav = os.path.join(project_dir, input_name)
    if output_prefix is None:
        output_prefix = os.path.join(project_dir, input_name.replace('.wav', ''))

    assert os.path.exists(input_wav), f"错误: {input_wav} 不存在"

    cut_silence(input_wav, output_prefix, threshold=threshold, num_segments=num_segments)
