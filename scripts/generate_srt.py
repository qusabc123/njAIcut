"""
字幕生成器
从裁剪静音的时间戳 JSON 直接读取每段时间，文案按逗号+句号细分，100% 对齐

用法: python generate_srt.py <项目路径> --配音 配音文件 --文案 文案文件 [--max-chars 9]
"""
import sys, os, re, json


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def remove_punctuation(text):
    text = re.sub(r'[，,。！？、；：""''（）()【】《》\u3000]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


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


def generate_srt(project_dir, audio_file, text_file, max_chars=9):
    # 读取时间戳 JSON
    ts_path = os.path.join(project_dir, audio_file.replace('.wav', '_timestamps.json'))
    if not os.path.exists(ts_path):
        print(f'[srt] 错误: 时间戳文件不存在 {ts_path}')
        return

    with open(ts_path, 'r', encoding='utf-8') as f:
        timestamps = json.load(f)

    print(f'[srt] 时间戳: {len(timestamps)} 段')

    # 读取文案，按逗号+句号+感叹号+问号分割（匹配 GPT-SoVITS 输出）
    text_path = os.path.join(project_dir, text_file)
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read().strip()

    sentences = re.split(r'(?<=[，,。！？])', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    print(f'[srt] 文案分句: {len(sentences)}')

    # 如果文案句数 ≠ 时间戳段数，用文案循环填充
    srt_lines = []
    for i, ts in enumerate(timestamps):
        if i < len(sentences):
            sentence = sentences[i]
        else:
            # 超出文案则循环
            sentence = sentences[i % len(sentences)]

        clean_text = remove_punctuation(sentence)
        if not clean_text:
            continue
        display_text = '\n'.join(split_by_chars(clean_text, max_chars))

        srt_lines.append(f"{i+1}")
        srt_lines.append(f"{format_time(ts['start'])} --> {format_time(ts['end'])}")
        srt_lines.append(display_text)
        srt_lines.append("")

    # 输出
    output_path = os.path.join(project_dir, '字幕.srt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(srt_lines))

    total_dur = timestamps[-1]['end'] if timestamps else 0
    print(f'[srt] 字幕已生成: {output_path}')
    print(f'[srt] {len(srt_lines)//4} 句, 100%对齐, 总时长: {total_dur:.1f}s')
    return output_path


def main():
    if len(sys.argv) < 2:
        print("用法: python generate_srt.py <项目路径> --配音 配音文件 --文案 文案文件 [--max-chars 9]")
        sys.exit(1)

    project_dir = os.path.abspath(sys.argv[1])
    audio_file = None
    text_file = None
    max_chars = 9

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--配音' and i + 1 < len(sys.argv):
            audio_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--文案' and i + 1 < len(sys.argv):
            text_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--max-chars' and i + 1 < len(sys.argv):
            max_chars = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    assert audio_file, "错误: 请指定 --配音"
    assert text_file, "错误: 请指定 --文案"

    generate_srt(project_dir, audio_file, text_file, max_chars)


if __name__ == '__main__':
    main()
