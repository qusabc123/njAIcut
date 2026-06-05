"""
智能素材选取器
读取文案，按段落匹配素材，选取总时长 = AI 配音时长（严格等于）
最后一个素材裁剪到刚好填满剩余时长

用法: python select_materials.py <项目路径> --配音 配音文件 [--index N]
"""
import sys, os, json, re, subprocess
import soundfile as sf


def get_duration(path, cache_file=None):
    """获取素材时长，优先使用缓存文件"""
    if cache_file and os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        basename = os.path.basename(path)
        if basename in cache:
            return cache[basename]
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except:
        return 5.0


def read_文案(project_dir, group_index=1):
    candidates = [
        os.path.join(project_dir, f'文案_{group_index}.txt'),
        os.path.join(project_dir, '文案.txt'),
    ]
    text_path = None
    for p in candidates:
        if os.path.exists(p):
            text_path = p
            break
    if not text_path:
        return []

    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read().strip()

    segments = re.split(r'[。！？\n]+', text)
    segments = [s.strip() for s in segments if s.strip()]
    print(f'[select] 文案分段: {len(segments)} 段')
    for i, s in enumerate(segments):
        short = s[:30] + '...' if len(s) > 30 else s
        print(f'  [{i+1}] {short}')
    return segments


def select_materials(project_dir, audio_duration, group_index=1):
    车素材_dir = os.path.join(project_dir, '车的素材')
    if not os.path.isdir(车素材_dir):
        print(f'[select] 错误: 缺少 {车素材_dir}')
        return [], []

    segments = read_文案(project_dir, group_index)
    all_files = sorted([f for f in os.listdir(车素材_dir) if f.lower().endswith('.mp4')])
    
    if not all_files:
        return [], []

    # 获取所有素材时长（预加载缓存，避免ffprobe调用卡死）
    缓存文件 = os.path.join(project_dir, '素材时长.json')
    _cache_data = {}
    if os.path.exists(缓存文件):
        with open(缓存文件, 'r') as _cf:
            _cache_data = json.load(_cf)
    print(f'[select] 从缓存读取 {len(_cache_data)} 个素材时长...')
    for f in all_files:
        if f in _cache_data:
            file_durations[f] = _cache_data[f]
        else:
            file_durations[f] = get_duration(os.path.join(车素材_dir, f), 缓存文件)
    selected = []
    cut_info = None
    accumulated = 0.0

    if segments:
        每段素材数 = max(1, len(all_files) // len(segments))
    else:
        每段素材数 = len(all_files)

    file_idx = 0
    total_segments = len(segments) if segments else 1

    for si in range(total_segments):
        if file_idx >= len(all_files):
            break
        n_files = 每段素材数 if si < total_segments - 1 else len(all_files) - file_idx
        for _ in range(n_files):
            if file_idx >= len(all_files):
                break
            f = all_files[file_idx]
            d = file_durations[f]
            if accumulated + d > audio_duration:
                cut_duration = audio_duration - accumulated
                if cut_duration > 0.3:
                    selected.append(f)
                    cut_info = (f, cut_duration)
                    accumulated = audio_duration
                file_idx += 1
                break
            else:
                selected.append(f)
                accumulated += d
                file_idx += 1
        if accumulated >= audio_duration:
            break

    # 不够就继续加
    while accumulated < audio_duration and file_idx < len(all_files):
        f = all_files[file_idx]
        d = file_durations[f]
        if accumulated + d > audio_duration:
            cut_duration = audio_duration - accumulated
            if cut_duration > 0.3:
                selected.append(f)
                cut_info = (f, cut_duration)
                accumulated = audio_duration
        else:
            selected.append(f)
            accumulated += d
        file_idx += 1

    # 全部用完还不够就循环补
    loop_idx = 0
    while accumulated < audio_duration and selected:
        f = selected[loop_idx % len(selected)]
        d = file_durations[f]
        if accumulated + d > audio_duration:
            cut_duration = audio_duration - accumulated
            if cut_duration > 0.3:
                selected.append(f'__repeat__{f}')
                cut_info = (f, cut_duration)
                accumulated = audio_duration
        else:
            selected.append(f'__repeat__{f}')
            accumulated += d
        loop_idx += 1

    print(f'[select] 选取: {len(selected)} 个素材, 总时长: {accumulated:.3f}s')
    if cut_info:
        print(f'[select] 裁剪素材: {cut_info[0]} → {cut_info[1]:.1f}s')

    result = {
        'files': selected,
        'total_duration': round(accumulated, 3),
        'audio_duration': round(audio_duration, 3),
        'cut_last': {
            'file': cut_info[0],
            'duration': round(cut_info[1], 3)
        } if cut_info else None
    }
    return selected, result


def main():
    if len(sys.argv) < 2:
        print("用法: python select_materials.py <项目路径> --配音 配音文件 [--index N]")
        sys.exit(1)

    project_dir = os.path.abspath(sys.argv[1])
    audio_file = None
    group_index = 1

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--配音' and i + 1 < len(sys.argv):
            audio_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--index' and i + 1 < len(sys.argv):
            group_index = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    audio_duration = None
    # 优先读时间戳JSON（多段文件模式）
    ts_path = os.path.join(project_dir, f'配音_gpt_cut_{group_index}_timestamps.json')
    if os.path.exists(ts_path):
        with open(ts_path, 'r') as _f:
            ts_data = json.load(_f)
        if ts_data:
            audio_duration = ts_data[-1]['end']
            audio_file = f'配音_cut_{group_index} (多段)'
            print(f'[select] 配音: {audio_file} (总时长: {audio_duration:.3f}s)')

    if audio_duration is None:
        if audio_file is None:
            for p in [f'配音_gpt_cut_{group_index}.wav', f'配音_fish_cut_{group_index}.wav']:
                fp = os.path.join(project_dir, p)
                if os.path.exists(fp):
                    audio_file = p
                    break

        if audio_file is None:
            print("[select] 错误: 未找到配音文件")
            sys.exit(1)

        audio_path = os.path.join(project_dir, audio_file)
        data, sr = sf.read(audio_path)
        audio_duration = len(data) / sr
        print(f'[select] 配音: {audio_file} ({audio_duration:.3f}s)')

    selected, result = select_materials(project_dir, audio_duration, group_index)

    output_file = os.path.join(project_dir, f'素材列表_{group_index}.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'[select] 素材列表已保存: {output_file}')


if __name__ == '__main__':
    main()
