#!/bin/bash
# njAIcut — 环境检查
# 检查所有依赖是否就绪

echo "🔍 njAIcut 环境检查"
echo "===================="

ERRORS=0

# Python
echo -n "🐍 Python 3.10+: "
PY_VER=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
if [ "$(echo "$PY_VER >= 3.10" | bc -l 2>/dev/null)" = "1" ] || [ "$PY_VER" = "3.10" ]; then
    echo "✅ $PY_VER"
else
    echo "❌ 当前 $PY_VER，需要 3.10+"
    ERRORS=$((ERRORS+1))
fi

# 虚拟环境
echo -n "📦 项目虚拟环境: "
ENV_PY="/Users/nj/Documents/短视频创作/env/bin/python"
if [ -f "$ENV_PY" ]; then
    echo "✅"
else
    echo "❌ 未找到 $ENV_PY"
    ERRORS=$((ERRORS+1))
fi

# Python 依赖
echo -n "  numpy: "; python3 -c "import numpy" 2>/dev/null && echo "✅" || { echo "❌"; ERRORS=$((ERRORS+1)); }
echo -n "  soundfile: "; python3 -c "import soundfile" 2>/dev/null && echo "✅" || { echo "❌"; ERRORS=$((ERRORS+1)); }
echo -n "  whisper: "; python3 -c "import whisper" 2>/dev/null && echo "✅" || { echo "❌"; ERRORS=$((ERRORS+1)); }

# pyJianYingDraft
echo -n "📁 pyJianYingDraft: "
if [ -f "/Users/nj/Desktop/工作1/德州/poker_ai/capcut-mate/src/pyJianYingDraft/__init__.py" ]; then
    echo "✅"
else
    echo "❌ 未找到"
    ERRORS=$((ERRORS+1))
fi

# Conda / GPT-SoVITS
echo -n "🔊 Conda环境(GPTSoVits): "
conda run -n GPTSoVits python --version 2>/dev/null && echo "✅" || { echo "❌"; ERRORS=$((ERRORS+1)); }

echo -n "  GPT-SoVITS 路径: "
if [ -d "/tmp/GPT-SoVITS" ]; then
    echo "✅"
else
    echo "❌ 未找到 /tmp/GPT-SoVITS"
    ERRORS=$((ERRORS+1))
fi

# ffmpeg
echo -n "🎬 ffmpeg: "
ffmpeg -version 2>/dev/null | head -1 && echo "" || { echo "❌"; ERRORS=$((ERRORS+1)); }

# 剪映草稿目录
echo -n "✂️  剪映草稿目录: "
if [ -d "/Users/nj/Movies/JianyingPro/User Data/Projects/com.lveditor.draft" ]; then
    echo "✅"
else
    echo "❌ 未找到"
    ERRORS=$((ERRORS+1))
fi

echo ""
echo "===================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ 所有环境检查通过！"
else
    echo "❌ $ERRORS 个问题需要修复"
fi
