# njAIcut

AI 短视频自动剪辑工具。基于 GPT-SoVITS 音色克隆 + 剪映草稿自动化。

## 安装

```bash
# Python 环境
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## 快速开始

设置环境变量：
```bash
ENV_PY="/path/to/env/bin/python"
SCRIPTS="/path/to/scripts"
GPT_ENV="conda run -n GPTSoVits"
PROJ="你的项目路径"
N=组编号
```

执行8步流程（详见 SKILL.md）：
1. 写文案 → 文案_N.txt
2. 提取参考音频（合并开头+结尾）
3. GPT-SoVITS 配音
4. 裁剪静音 → 每句独立WAV
5. 智能选材
6. 生成字幕SRT
7. 识别开头结尾 + 合并字幕
8. 生成剪映草稿

## 依赖

- Python 3.10+
- GPT-SoVITS
- pyJianYingDraft
- numpy, soundfile, whisper
- ffmpeg
