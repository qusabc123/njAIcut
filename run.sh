#!/bin/bash
# njAIcut — 一键执行完整流程
# 用法: ./run.sh <项目路径> <组编号> [草稿名]

set -e

if [ $# -lt 2 ]; then
    echo "用法: ./run.sh <项目路径> <组编号> [草稿名]"
    echo "示例: ./run.sh /path/to/法拉利罗马 1"
    exit 1
fi

PROJ="$1"
N="$2"
DRAFT_NAME="${3:-草稿-$N}"

# 环境变量
ENV_PY="/Users/nj/Documents/短视频创作/env/bin/python"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)/scripts"
GPT_ENV="conda run -n GPTSoVits"

echo "========================================="
echo " njAIcut — 第${N}组 开始"
echo " 项目: $PROJ"
echo " 草稿: $DRAFT_NAME"
echo "========================================="

# 检查项目结构
[ -d "$PROJ/开头" ] || { echo "❌ 缺少开头/"; exit 1; }
[ -d "$PROJ/结尾" ] || { echo "❌ 缺少结尾/"; exit 1; }
[ -d "$PROJ/车的素材" ] || { echo "❌ 缺少车的素材/"; exit 1; }
[ -f "$PROJ/文案_${N}.txt" ] || { echo "❌ 缺少 文案_${N}.txt"; exit 1; }

# 文案句数
echo ""
echo "📝 文案句数..."
文案句数=$(python3 -c "import re; f=open('$PROJ/文案_${N}.txt').read(); print(len([s for s in re.split(r'(?<=[，,。！？])',f) if s.strip()]))")
echo "  文案句数: $文案句数"

# 第2步：提取参考音频
echo ""
echo "🎵 [2/8] 提取参考音频..."
ffmpeg -y -i "$PROJ/开头/$(ls $PROJ/开头/*.mov | sed -n "${N}p")" -vn "$PROJ/开头音频_${N}.wav" 2>/dev/null
ffmpeg -y -i "$PROJ/结尾/$(ls $PROJ/结尾/*.mov | sed -n "${N}p")" -vn "$PROJ/结尾音频_${N}.wav" 2>/dev/null
ffmpeg -y -i "concat:$PROJ/开头音频_${N}.wav|$PROJ/结尾音频_${N}.wav" -acodec copy "$PROJ/参考音频_${N}.wav" 2>/dev/null
rm "$PROJ/开头音频_${N}.wav" "$PROJ/结尾音频_${N}.wav"
echo "  ✅ 参考音频: 参考音频_${N}.wav"

# 第3步：GPT-SoVITS 配音
echo ""
echo "🎤 [3/8] GPT-SoVITS 配音..."
$GPT_ENV python "$SCRIPTS/run_gpt_sovits_tts.py" "$PROJ" \
  --ref-wav "$PROJ/参考音频_${N}.wav" \
  --output "配音_gpt_${N}.wav"
echo "  ✅ 配音: 配音_gpt_${N}.wav"

# 第4步：裁剪静音
echo ""
echo "✂️  [4/8] 裁剪静音..."
$ENV_PY "$SCRIPTS/cut_silence.py" "$PROJ" \
  --input "配音_gpt_${N}.wav" \
  --output "配音_gpt_cut_${N}" \
  --num-segments $文案句数
echo "  ✅ 裁剪完成: $文案句数 段独立音频"

# 第5步：智能选材
echo ""
echo "🎯 [5/8] 智能选材..."
$ENV_PY "$SCRIPTS/select_materials.py" "$PROJ" \
  --配音 "配音_gpt_cut_${N}.wav" --index $N
echo "  ✅ 选材完成"

# 第6步：生成字幕
echo ""
echo "📄 [6/8] 生成字幕..."
$ENV_PY "$SCRIPTS/generate_srt.py" "$PROJ" \
  --配音 "配音_gpt_cut_${N}.wav" \
  --文案 "文案_${N}.txt" \
  --max-chars 9
echo "  ✅ 字幕已生成"

# 第7步：合并字幕
echo ""
echo "🔗 [7/8] 合并开头结尾字幕..."
$ENV_PY "$SCRIPTS/transcribe.py" "$PROJ" --index $N
echo "  ✅ 字幕合并完成"

# 第8步：生成草稿
echo ""
echo "🎬 [8/8] 生成剪映草稿..."
$ENV_PY "$SCRIPTS/create_draft.py" "$PROJ" "$DRAFT_NAME" --index $N

echo ""
echo "========================================="
echo " ✅ 第${N}组完成！"
echo "    草稿名: $DRAFT_NAME"
echo "    打开剪映 → 本地草稿 → 预览导出"
echo "========================================="
