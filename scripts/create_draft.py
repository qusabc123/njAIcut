"""
剪映草稿生成器 (通用版)
规则固化，每个项目按同样流程执行

用法: python create_draft.py <项目路径> [草稿名称] [--index N]
  --index N  使用第 N 组开头+结尾（从1开始，默认1）
"""
import sys, os, shutil, json, subprocess

sys.path.insert(0, '/Users/nj/Desktop/工作1/德州/poker_ai/capcut-mate/src')
from pyJianYingDraft import (
    DraftFolder, VideoSegment, AudioSegment, TextSegment,
    Timerange, TrackType, VideoMaterial, AudioMaterial,
    TextStyle, TextShadow, FontType, ClipSettings,
)


def find_配音(project_dir, group_index=1):
    # 优先找裁剪后的多段文件（配音_gpt_cut_1_001.wav 等）
    import glob as _glob
    多段前缀 = os.path.join(project_dir, f'配音_gpt_cut_{group_index}_')
    多段文件 = _glob.glob(f'{多段前缀}*.wav')
    if 多段文件:
        return f'配音_gpt_cut_{group_index}'
    patterns = [
        f'配音_gpt_cut_{group_index}.wav',
        f'配音_fish_cut_{group_index}.wav',
        '配音_gpt_cut.wav',
        '配音_fish_cut.wav',
    ]
    for p in patterns:
        fp = os.path.join(project_dir, p)
        if os.path.exists(fp):
            return p
    return None


def find_字幕(project_dir, group_index=1):
    patterns = [
        f'字幕_{group_index}.srt',
        '字幕.srt',
    ]
    for p in patterns:
        fp = os.path.join(project_dir, p)
        if os.path.exists(fp):
            return p
    return None


def load_素材列表(project_dir, group_index=1):
    列表文件 = os.path.join(project_dir, f'素材列表_{group_index}.json')
    if os.path.exists(列表文件):
        with open(列表文件, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and 'files' in data:
            return data['files'], data.get('cut_last')
        elif isinstance(data, list):
            return data, None
    return None, None


def cut_video(input_path, output_path, duration):
    result = subprocess.run(
        ['ffmpeg', '-y', '-i', input_path, '-t', str(duration),
         '-c', 'copy', output_path],
        capture_output=True, text=True
    )
    return result.returncode == 0


def main():
    if len(sys.argv) < 2:
        print("用法: python create_draft.py <项目路径> [草稿名称] [--index N]")
        sys.exit(1)

    project_dir = os.path.abspath(sys.argv[1])

    group_index = 1
    args_remain = []
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--index' and i + 1 < len(sys.argv):
            group_index = int(sys.argv[i + 1])
            i += 2
        else:
            args_remain.append(sys.argv[i])
            i += 1

    draft_name = args_remain[0] if args_remain else f"{os.path.basename(project_dir)}-{group_index}"

    # ===== 验证项目结构 =====
    开头_dir = os.path.join(project_dir, '开头')
    结尾_dir = os.path.join(project_dir, '结尾')
    车素材_dir = os.path.join(project_dir, '车的素材')

    assert os.path.isdir(开头_dir), f"错误: 缺少 {开头_dir}"
    assert os.path.isdir(结尾_dir), f"错误: 缺少 {结尾_dir}"
    assert os.path.isdir(车素材_dir), f"错误: 缺少 {车素材_dir}"

    # ===== 规则1: 开头 =====
    开头列表 = sorted([f for f in os.listdir(开头_dir) if f.lower().endswith('.mov')])
    assert len(开头列表) >= group_index
    开_文件 = 开头列表[group_index - 1]
    print(f'[规则1] 开头: {开_文件}')

    # ===== 规则2: 结尾 =====
    结尾列表_clean = sorted([f for f in os.listdir(结尾_dir) if f.lower().endswith('.mov') and '_副本' not in f])
    结尾列表_all = sorted([f for f in os.listdir(结尾_dir) if f.lower().endswith('.mov')])
    if len(结尾列表_clean) >= group_index:
        结尾列表 = 结尾列表_clean
    else:
        结尾列表 = 结尾列表_all
    assert len(结尾列表) >= group_index
    尾_文件 = 结尾列表[group_index - 1]
    print(f'[规则2] 结尾: {尾_文件}')

    # ===== 规则3: 智能素材 =====
    中间列表_raw, cut_info = load_素材列表(project_dir, group_index)
    if 中间列表_raw is not None:
        中间_list = []
        for f in 中间列表_raw:
            if f.startswith('__repeat__'):
                原文件 = f.replace('__repeat__', '')
                if os.path.exists(os.path.join(车素材_dir, 原文件)):
                    中间_list.append(原文件)
            else:
                if os.path.exists(os.path.join(车素材_dir, f)):
                    中间_list.append(f)
        print(f'[规则3] 智能选取: {len(中间_list)} 个素材')
    else:
        中间_list = sorted([f for f in os.listdir(车素材_dir) if f.lower().endswith('.mp4')])
        print(f'[规则3] 全部素材: {len(中间_list)} 个')
    assert len(中间_list) > 0

    # ===== 配音 =====
    配音文件 = find_配音(project_dir, group_index)
    assert 配音文件 is not None, f"错误: 未找到第{group_index}组配音文件"
    print(f'[规则4/5] 配音: {配音文件}')

    # ===== 创建草稿 =====
    draft_dir = '/Users/nj/Movies/JianyingPro/User Data/Projects/com.lveditor.draft'
    draft_path = os.path.join(draft_dir, draft_name)
    if os.path.exists(draft_path):
        shutil.rmtree(draft_path)

    folder = DraftFolder(draft_dir)
    sf = folder.create_draft(draft_name, width=2160, height=3840, fps=30, allow_replace=True)
    print(f'[规则7] 分辨率: 2160×3840')

    # ===== 复制素材 =====
    av = os.path.join(draft_path, 'assets', 'videos')
    aa = os.path.join(draft_path, 'assets', 'audios')
    os.makedirs(av, exist_ok=True)
    os.makedirs(aa, exist_ok=True)

    开_路径 = os.path.join(av, 开_文件)
    shutil.copy2(os.path.join(开头_dir, 开_文件), 开_路径)

    尾_路径 = os.path.join(av, 尾_文件)
    shutil.copy2(os.path.join(结尾_dir, 尾_文件), 尾_路径)

    中_路径列表 = []
    for vf in 中间_list:
        src = os.path.join(车素材_dir, vf)
        dst = os.path.join(av, vf)
        shutil.copy2(src, dst)
        中_路径列表.append(dst)

    if cut_info and 中_路径列表:
        最后一个 = 中_路径列表[-1]
        裁剪文件名 = f'_cut_{os.path.basename(最后一个)}'
        裁剪路径 = os.path.join(av, 裁剪文件名)
        cut_duration = cut_info['duration']
        if cut_video(最后一个, 裁剪路径, cut_duration):
            中_路径列表[-1] = 裁剪路径
            print(f'[裁剪] {os.path.basename(最后一个)} → {cut_duration:.1f}s')

    print('素材复制完成')

    # ===== 主视频轨道 =====
    sf.add_track(track_type=TrackType.video, track_name="主轨道", relative_index=0)
    cur = 0

    mat_开 = VideoMaterial(开_路径)
    sf.add_segment(VideoSegment(开_路径, target_timerange=Timerange(0, mat_开.duration)), "主轨道")
    cur += int(mat_开.duration)

    for vp in 中_路径列表:
        mat = VideoMaterial(vp)
        dur = int(mat.duration)
        sf.add_segment(VideoSegment(vp, target_timerange=Timerange(cur, dur)), "主轨道")
        cur += dur

    mat_尾 = VideoMaterial(尾_路径)
    sf.add_segment(VideoSegment(尾_路径, target_timerange=Timerange(cur, mat_尾.duration)), "主轨道")
    cur += int(mat_尾.duration)

    # ===== 配音轨道（多段独立音频按顺序拼接） =====
    sf.add_track(track_type=TrackType.audio, track_name="配音", relative_index=1)
    audio_track_name = None
    for tid, t in sf.tracks.items():
        if t.track_type == TrackType.audio:
            audio_track_name = tid
            break

    # 查找多段配音文件：配音_gpt_cut_1_NNN.wav
    import glob as _glob
    import json as _json
    配音前缀 = os.path.join(project_dir, f'配音_gpt_cut_{group_index}')
    配音段文件 = sorted(_glob.glob(f'{配音前缀}_*.wav'))
    
    配音开始 = int(mat_开.duration)
    配音总时长 = 0
    
    if 配音段文件:
        print(f'[配音] {len(配音段文件)} 段独立音频')
        配音文件 = 配音段文件[0]  # 用实际文件名
        for seg_file in 配音段文件:
            段名 = os.path.basename(seg_file)
            段_剪映路径 = os.path.join(aa, 段名)
            shutil.copy2(seg_file, 段_剪映路径)
            段_mat = AudioMaterial(段_剪映路径)
            段时长 = int(段_mat.duration)
            sf.add_segment(
                AudioSegment(段_剪映路径, target_timerange=Timerange(配音开始 + 配音总时长, 段时长)),
                audio_track_name
            )
            配音总时长 += 段时长
    else:
        # 没有多段文件，用单个配音文件
        配_mat = AudioMaterial(配音_剪映路径)
        配音总时长 = int(配_mat.duration)
        sf.add_segment(
            AudioSegment(配音_剪映路径, target_timerange=Timerange(配音开始, 配音总时长)),
            audio_track_name
        )

    # ===== BGM 背景音乐轨道 =====
    BGM目录 = os.path.join(project_dir, 'BGM')
    BGM音量 = 0.15  # 配音的15%，避免盖过人声
    BGM淡入 = 1000000  # 1秒淡入（微秒）
    BGM淡出 = 1000000  # 1秒淡出（微秒）
    
    if os.path.isdir(BGM目录):
        # 筛选纯音频文件（排除录屏等带视频轨道的文件）
        _候选 = [f for f in os.listdir(BGM目录) if f.lower().endswith(('.mp3', '.wav', '.m4a', '.aac', '.aiff'))]
        BGM文件列表 = []
        for _f in _候选:
            _路径 = os.path.join(BGM目录, _f)
            _r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1', _路径],
                              capture_output=True, text=True, timeout=5)
            _类型 = _r.stdout.strip().split('\n')
            if 'video' not in _类型:
                BGM文件列表.append(_f)
        BGM文件列表.sort()
        print(f'[BGM] 检测到 {len(BGM文件列表)} 个纯音频文件: {BGM文件列表}')
        if BGM文件列表:
            BGM文件 = BGM文件列表[0]  # 取第一个
            BGM路径 = os.path.join(BGM目录, BGM文件)
            BGM_剪映路径 = os.path.join(aa, BGM文件)
            shutil.copy2(BGM路径, BGM_剪映路径)
            BGM素材 = AudioMaterial(BGM_剪映路径)
            BGM总时长 = int(BGM素材.duration)
            视频总时长 = cur  # 当前视频总长
            
            # 创建BGM轨道
            sf.add_track(track_type=TrackType.audio, track_name="BGM", relative_index=2)
            bgm_track_name = None
            for tid, t in sf.tracks.items():
                if t.track_type == TrackType.audio and t.name == "BGM":
                    bgm_track_name = tid
                    break
            
            if bgm_track_name:
                # BGM从视频开始到结束，音量降低
                if BGM总时长 >= 视频总时长:
                    # BGM够长，直接裁剪
                    bgm_seg = AudioSegment(
                        BGM_剪映路径,
                        target_timerange=Timerange(0, 视频总时长),
                        volume=BGM音量,
                    )
                    bgm_seg.add_fade(BGM淡入, BGM淡出)
                    sf.add_segment(bgm_seg, bgm_track_name)
                    print(f'[BGM] {BGM文件} (音量{BGM音量:.0%}, 淡入1s, 淡出1s)')
                else:
                    # BGM太短，循环播放填满视频时长
                    循环次数 = (视频总时长 // BGM总时长) + 1
                    pos = 0
                    for _ in range(循环次数):
                        if pos >= 视频总时长:
                            break
                        剩余时长 = 视频总时长 - pos
                        本段时长 = min(BGM总时长, 剩余时长)
                        seg = AudioSegment(
                            BGM_剪映路径,
                            target_timerange=Timerange(pos, 本段时长),
                            volume=BGM音量,
                        )
                        # 只在第一段加淡入，最后一段加淡出
                        if pos == 0:
                            seg.add_fade(BGM淡入, 0)
                        elif pos + 本段时长 >= 视频总时长:
                            seg.add_fade(0, BGM淡出)
                        sf.add_segment(seg, bgm_track_name)
                        pos += 本段时长
                    print(f'[BGM] {BGM文件} (循环{循环次数}次, 音量{BGM音量:.0%})')
    else:
        print('[BGM] 未找到BGM目录，跳过')
    
    # ===== 字幕轨道（金陵体、字号11、白色、Y=-500、阴影#3b3b3b） =====
    字幕文件 = find_字幕(project_dir, group_index)
    if 字幕文件:
        字幕路径 = os.path.join(project_dir, 字幕文件)
        print(f'[字幕] 导入: {字幕文件}')

        # 创建样式参考片段（阴影和字体必须通过 style_reference 传递）
        style_ref = TextSegment(
            "样式参考",
            Timerange(0, 1000000),
            style=TextStyle(size=11.0, color=(1.0, 1.0, 1.0), align=1, alpha=1.0, auto_wrapping=False),
            font=FontType.金陵体,
            shadow=TextShadow(alpha=1.0, color=(59/255, 59/255, 59/255), diffuse=15.0, distance=5.0, angle=-45.0),
            clip_settings=ClipSettings(transform_y=-500/1080),
        )

        sf.import_srt(
            字幕路径,
            track_name="字幕",
            style_reference=style_ref,

            clip_settings=None,
        )

        print(f'[字幕] 金陵体 | 字号11 | 白色 | Y=-500 | 阴影#3b3b3b')
    else:
        print(f'[字幕] 未找到字幕文件')

    # ===== 保存 =====
    sf.save()
    print(f'\n=== 完成 第{group_index}组 ===')
    print(f'草稿名: {draft_name}')
    print(f'视频总长: {cur / 1e6:.1f}s')
    print(f'配音总时长: {配音总时长 / 1e6:.1f}s')
    if 字幕文件:
        print(f'[字幕] {字幕文件}')


if __name__ == '__main__':
    main()
