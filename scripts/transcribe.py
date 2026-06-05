"""
用 Whisper 识别开头/结尾素材的音频
与配音字幕合并为一个完整的 SRT 文件（所有时间偏移在脚本中计算）

用法: python transcribe.py <项目路径> --index N
"""
import sys, os, subprocess, tempfile, re, json


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt(srt_text):
    blocks = re.split(r'\n\n+', srt_text.strip())
    segments = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_line = lines[1]
            text = '\n'.join(lines[2:])
            match = re.match(r'(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)', time_line)
            if match:
                def to_sec(t):
                    parts = t.replace(',', '.').split(':')
                    return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
                segments.append((to_sec(match.group(1)), to_sec(match.group(2)), text.strip()))
    return segments


def remove_punctuation(text):
    text = re.sub(r'[，,。！？、；：""''（）()【】《》\u3000]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def to_simplified(text):
    """繁体转简体（简单映射表）"""
    table = {
        '羅': '罗', '馬': '马', '開': '开', '運': '运', '萬': '万', '歲': '岁',
        '國': '国', '關': '关', '體': '体', '臺': '台', '灣': '湾', '學': '学',
        '會': '会', '區': '区', '東': '东', '西': '西', '南': '南', '北': '北',
        '龍': '龙', '鳳': '凤', '龜': '龟', '魚': '鱼', '鳥': '鸟', '馬': '马',
        '車': '车', '門': '门', '鬥': '斗', '愛': '爱', '親': '亲', '眾': '众',
        '與': '与', '為': '为', '勝': '胜', '敗': '败', '質': '质', '況': '况',
        '僅': '仅', '經': '经', '典': '典', '配': '配', '極': '极',
    }
    result = ''
    for ch in text:
        result += table.get(ch, ch)
    return result


def split_by_chars(text, max_chars=9):
    text = text.strip()
    if not text:
        return [""]
    result = []
    while text:
        width = 0
        pos = 0
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff':
                width += 1
            elif ch.isalpha() or ch.isdigit():
                width += 0.5
            else:
                width += 0.2
            pos += 1
            if width > max_chars:
                break
        line = text[:pos]
        rest = text[pos:]
        if line and rest and line[-1].isalpha() and rest[0].isalpha():
            idx = len(line) - 1
            while idx >= 0 and line[idx].isalpha():
                idx -= 1
            word = line[idx+1:]
            line = line[:idx+1]
            rest = word + rest
        result.append(line.strip())
        text = rest.strip()
        if not text and not result[-1]:
            break
    return result if result else [text]


def get_duration(path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def transcribe_file(video_path):
    result = subprocess.run(
        ['whisper', video_path, '--model', 'small', '--language', 'zh',
         '--output_format', 'srt', '--output_dir', tempfile.gettempdir(),
         '--verbose', 'False'],
        capture_output=True, text=True
    )
    base = os.path.basename(video_path)
    for ext in ['.mov', '.mp4']:
        base = base.replace(ext, '')
    srt_path = os.path.join(tempfile.gettempdir(), base + '.srt')
    segments = []
    if os.path.exists(srt_path):
        with open(srt_path, 'r', encoding='utf-8') as f:
            segments = parse_srt(f.read())
        os.remove(srt_path)
    return segments


def read_配音_srt(project_dir, group_index):
    """读取配音字幕 SRT（generate_srt.py 生成，时间为裁剪后的配音时间）"""
    srt_path = os.path.join(project_dir, '字幕.srt')
    if os.path.exists(srt_path):
        with open(srt_path, 'r', encoding='utf-8') as f:
            return parse_srt(f.read())
    # 也尝试无索引版本
    srt_path = os.path.join(project_dir, '字幕.srt')
    if os.path.exists(srt_path):
        with open(srt_path, 'r', encoding='utf-8') as f:
            return parse_srt(f.read())
    return []


def main():
    if len(sys.argv) < 2:
        print("用法: python transcribe.py <项目路径> --index N")
        sys.exit(1)

    project_dir = os.path.abspath(sys.argv[1])
    group_index = 1

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--index' and i + 1 < len(sys.argv):
            group_index = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    开头_dir = os.path.join(project_dir, '开头')
    结尾_dir = os.path.join(project_dir, '结尾')

    开头列表 = sorted([f for f in os.listdir(开头_dir) if f.lower().endswith('.mov')])
    结尾列表 = sorted([f for f in os.listdir(结尾_dir) if f.lower().endswith('.mov')])

    assert len(开头列表) >= group_index
    开_文件 = 开头列表[group_index - 1]

    结尾_clean = sorted([f for f in 结尾列表 if '_副本' not in f])
    if len(结尾_clean) >= group_index:
        尾_文件 = 结尾_clean[group_index - 1]
    else:
        尾_文件 = 结尾列表[group_index - 1]

    开_路径 = os.path.join(开头_dir, 开_文件)
    尾_路径 = os.path.join(结尾_dir, 尾_文件)
    开_时长 = get_duration(开_路径)  # 秒

    # 计算中间素材总时长（从素材列表中读取或全部素材）
    素材列表路径 = os.path.join(project_dir, f'素材列表_{group_index}.json')
    中间_总时长 = 0.0
    车素材_dir = os.path.join(project_dir, '车的素材')
    if os.path.exists(素材列表路径):
        with open(素材列表路径, 'r', encoding='utf-8') as f:
            data = json.load(f)
        files = data.get('files', data if isinstance(data, list) else [])
        for fname in files:
            if fname.startswith('__repeat__'):
                fname = fname.replace('__repeat__', '')
            fpath = os.path.join(车素材_dir, fname)
            if os.path.exists(fpath):
                中间_总时长 += get_duration(fpath)
        # 如果有裁剪，取实际时长
        if data.get('cut_last'):
            中间_总时长 = data['total_duration']

    # 识别开头和结尾
    print(f'[transcribe] 识别开头: {开_文件}')
    开_segs = transcribe_file(开_路径)
    print(f'[transcribe] 识别结尾: {尾_文件}')
    尾_segs = transcribe_file(尾_路径)

    # 读取配音字幕（时间为裁剪后的配音时长）
    配音_segs = read_配音_srt(project_dir, group_index)
    print(f'[transcribe] 配音字幕: {len(配音_segs)} 段')

    # 时间偏移
    # - 开头字幕：0（从视频0秒开始）
    # - 配音字幕：开头时长后开始（配音从开头画面结束后开始）
    配音_偏移 = 开_时长
    # - 结尾字幕：开头时长 + 中间素材总时长后开始
    尾_偏移 = 开_时长 + 中间_总时长

    # 合并所有字幕段
    all_segments = []

    for s, e, t in 开_segs:
        clean = to_simplified(remove_punctuation(t))
        display = '\n'.join(split_by_chars(clean))
        all_segments.append((s, e, display))

    for s, e, t in 配音_segs:
        display = '\n'.join(split_by_chars(t))
        all_segments.append((s + 配音_偏移, e + 配音_偏移, display))

    for s, e, t in 尾_segs:
        display = '\n'.join(split_by_chars(remove_punctuation(t)))

        # 避免与配音最后一段重叠
        min_end = max(seg[1] for seg in all_segments) if all_segments else 0
        start_time = max(s + 尾_偏移, min_end)
        end_time = max(e + 尾_偏移, start_time + 0.1)
        all_segments.append((start_time, end_time, display))

    # 按时间排序
    all_segments.sort(key=lambda x: x[0])

    # 生成 SRT
    srt_lines = []
    for i, (start, end, text) in enumerate(all_segments):
        srt_lines.append(f"{i+1}")
        srt_lines.append(f"{format_time(start)} --> {format_time(end)}")
        srt_lines.append(text)
        srt_lines.append("")

    # 保存
    输出名 = f"字幕_{group_index}.srt"
    输出路径 = os.path.join(project_dir, 输出名)
    with open(输出路径, 'w', encoding='utf-8') as f:
        f.write('\n'.join(srt_lines))

    print(f'[transcribe] 合并字幕: {输出路径}')
    print(f'[transcribe] 总段数: {len(all_segments)} (开头{len(开_segs)} + 配音{len(配音_segs)} + 结尾{len(尾_segs)})')
    print(f'[transcribe] 偏移: 配音+{配音_偏移:.1f}s, 结尾+{尾_偏移:.1f}s')


if __name__ == '__main__':
    main()
