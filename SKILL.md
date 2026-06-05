---
name: ai-video-editor
description: "AI 智剪 — 短视频自动剪辑工具。规则固化不可违反。"
---

# $ai-video-editor

## 项目结构要求

```
项目名/
├── 开头/          # .mov 横屏素材（按文件名排序，每组取第 N 个）
├── 结尾/          # .mov 横屏素材（按文件名排序，每组取第 N 个，先排非`_副本`，不够再补`_副本`）
├── 车的素材/       # .mp4 竖屏素材（所有素材，智能选取）
└── 文案_N.txt       # 每组独立配音文案
```

## 固化规则（不可违反）

| # | 规则 | 说明 |
|---|------|------|
| 1 | 开头选材 | `开头/` 按文件名排序，第 N 组取第 N 个 `.mov` |
| 2 | 结尾选材 | `结尾/` 按文件名排序，第 N 组取第 N 个 `.mov`（先排非`_副本`，不够补`_副本`） |
| 3 | 中间选材 | 按文案段落分配素材 → 总时长 **严格**= 配音时长（最后一个裁剪填满） |
| 4 | 配音模型 | GPT-SoVITS 零样本音色克隆 |
| 5 | 裁剪静音 | 剪掉 AI 配音中句间的静音空隙 → 每句话独立保存为一个 WAV 文件 |
| 6 | 配音对齐 | 配音在开头画面结束后开始 |
| 7 | 分辨率 | 竖屏 9:16（2160 × 3840） |
| 8 | 每组独立文案 + 独立参考音频 | 文案_N.txt + 该组开头素材+结尾素材合并的音频 |

## 字幕参数（固定）

金陵体 | 字号11 | 白色 | 居中 | X=0 Y=-500 | 不透明度100% | 阴影#3b3b3b | 去标点用空格 | 每行最多9字 | 简体中文

## 完整流程

```bash
ENV_PY="/Users/nj/Documents/短视频创作/env/bin/python"
SCRIPTS="/Users/nj/.codex/skills/ai-video-editor/scripts"
GPT_ENV="conda run -n GPTSoVits"
PROJ="项目路径"

# 1. 写文案 → 文案_N.txt

# 2. 提取参考音频（合并第N组开头+结尾，给GPT-SoVITS更多学习样本）
N=1
ffmpeg -y -i "$PROJ/开头/$(ls $PROJ/开头/*.mov | sed -n "${N}p")" -vn "$PROJ/开头音频_N.wav"
ffmpeg -y -i "$PROJ/结尾/$(ls $PROJ/结尾/*.mov | sed -n "${N}p")" -vn "$PROJ/结尾音频_N.wav"
ffmpeg -y -i "concat:$PROJ/开头音频_N.wav|$PROJ/结尾音频_N.wav" -acodec copy "$PROJ/参考音频_N.wav"
rm "$PROJ/开头音频_N.wav" "$PROJ/结尾音频_N.wav"

# 3. GPT-SoVITS 配音
$GPT_ENV python "$SCRIPTS/run_gpt_sovits_tts.py" "$PROJ" \
  --ref-wav "$PROJ/参考音频_N.wav" \
  --output "配音_gpt_N.wav"

# 4. 裁剪静音 → 每句独立音频 + 时间戳JSON
# 先读文案句数，传入 --num-segments 确保段数精准对齐文案
文案句数=$(python3 -c "import re; f=open('$PROJ/文案_N.txt').read(); print(len([s for s in re.split(r'(?<=[，,。！？])',f) if s.strip()]))")
$ENV_PY "$SCRIPTS/cut_silence.py" "$PROJ" \
  --input "配音_gpt_N.wav" \
  --output "配音_gpt_cut_N" \
  --num-segments $文案句数

# 5. 智能选材（优先读缓存素材时长.json，避免 ffprobe 卡死）
$ENV_PY "$SCRIPTS/select_materials.py" "$PROJ" \
  --配音 "配音_gpt_cut_N.wav" --index N

# 6. 生成 SRT（从时间戳JSON直接匹配文案，100%对齐）
$ENV_PY "$SCRIPTS/generate_srt.py" "$PROJ" \
  --配音 "配音_gpt_cut_N.wav" \
  --文案 "文案_N.txt" \
  --max-chars 9

# 7. 识别开头结尾音频 → 繁体转简体 → 合并字幕
$ENV_PY "$SCRIPTS/transcribe.py" "$PROJ" --index N

# 8. 生成草稿（多段配音独立拼接 + 字幕）
$ENV_PY "$SCRIPTS/create_draft.py" "$PROJ" "草稿名-N" --index N
```
