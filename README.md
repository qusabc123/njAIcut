# njAIcut

> AI 短视频自动剪辑工具 — 音色克隆 + 智能配画面 + 自动字幕 → 剪映草稿

## 它能做什么

拍好素材、写好文案，剩下的交给 njAIcut：

```
1. 克隆你的声音
2. 生成配音
3. 智能匹配画面
4. 加专业字幕
5. 生成剪映草稿
6. 导出即可发布
```

**适合场景（开头口播 + 中间混剪 + 结尾口播 模板）：**

| 场景 | 开头素材 | 中间素材 | 结尾素材 | 文案方向 |
|------|---------|---------|---------|---------|
| 🚗 二手车 | 车评人口播 | 车辆外观/内饰/细节 | CTA收尾 | 车况参数+卖点 |
| 🛒 电商带货 | 主播口播 | 产品多角度/使用场景 | CTA引导下单 | 产品卖点+促销 |
| 🏠 房产实拍 | 中介口播 | 户型/小区/周边 | CTA约看 | 房源参数+优势 |
| 🍜 探店美食 | 博主口播 | 菜品特写/环境 | CTA定位 | 菜品介绍+推荐 |
| 📚 知识口播 | 讲者口播 | 图文/演示 | CTA关注 | 知识点+总结 |
| 🎮 游戏解说 | 主播口播 | 游戏画面/高光 | CTA点赞 | 玩法+攻略 |
| 🏋️ 健身教学 | 教练口播 | 动作演示 | CTA跟练 | 动作要领+计划 |
| 💄 美妆测评 | 博主口播 | 产品实测/对比 | CTA购买 | 成分+效果+对比 |
| 🏭 工厂实拍 | 老板口播 | 生产线/质检/仓库 | CTA询价 | 产能+品质+优势 |
| 🎯 直播切片 | 主播高光 | 商品讲解片段 | 限时优惠引导 | 精彩片段提炼 |
| 🎬 短剧解说 | 博主口播 | 剧情片段 | CTA追剧 | 剧情+看点 |
| 📦 开箱测评 | 博主口播 | 开箱过程+产品特写 | CTA购买 | 开箱体验+评价 |
| ✈️ 旅游Vlog | 博主口播 | 景点/美食/人文 | CTA关注 | 攻略+推荐 |
| 🐱 宠物日常 | 博主口播 | 宠物萌趣片段 | CTA点赞 | 宠物故事+知识 |
| 🍳 美食教程 | 博主口播 | 烹饪过程 | CTA跟做 | 步骤+技巧 |

## 效果演示

以法拉利 Roma 为例：

| 输入 | 输出 |
|------|------|
| 4个开头素材 (.mov) | 4条独立短视频 |
| 4个结尾素材 (.mov) | 每条 20~30 秒 |
| 25个车素材 (.mp4) | 竖屏 2160×3840 |
| 1条文案（6句话） | 金陵体字幕 + 阴影 |
| 参考音频（3~6秒） | GPT-SoVITS 音色克隆配音 |

## 安装

### 环境要求

- macOS / Linux
- Python 3.10+
- Conda（用于 GPT-SoVITS）
- ffmpeg
- 剪映专业版（用于预览和导出）

### 步骤

```bash
# 1. 克隆仓库
git clone https://github.com/qusabc123/njAIcut.git
cd njAIcut

# 2. 创建 Python 环境
python3 -m venv env
source env/bin/activate
pip install numpy soundfile whisper openai-whisper

# 3. 安装 GPT-SoVITS（音色克隆）
git clone https://github.com/RVC-Boss/GPT-SoVITS.git /tmp/GPT-SoVITS
cd /tmp/GPT-SoVITS
conda create -n GPTSoVits python=3.10
conda activate GPTSoVits
pip install -r requirements.txt
# Mac MPS 用户需额外配置

# 4. 安装 pyJianYingDraft（剪映草稿生成）
# 从 capcut-mate 项目获取
```

## 快速使用

### 项目结构

创建一个素材文件夹：

```
我的项目/
├── 开头/              # .mov 横屏素材
│   ├── 开头1.mov
│   ├── 开头2.mov
│   └── ...
├── 结尾/              # .mov 横屏素材
│   ├── 结尾1.mov
│   └── ...
├── 车的素材/           # .mp4 竖屏素材
│   ├── 素材1.mp4
│   └── ...
└── 文案_1.txt          # 第1组文案
```

### 执行

```bash
ENV_PY="/path/to/env/bin/python"
SCRIPTS="/path/to/njAIcut/scripts"
GPT_ENV="conda run -n GPTSoVits"
PROJ="/path/to/我的项目"
N=1

# 写文案 → 文案_1.txt

# 一键执行
文案句数=$(python3 -c "import re; f=open('$PROJ/文案_${N}.txt').read(); print(len([s for s in re.split(r'(?<=[，,。！？])',f) if s.strip()]))")
ffmpeg -y -i "$PROJ/开头/$(ls $PROJ/开头/*.mov | sed -n "${N}p")" -vn "$PROJ/开头音频_${N}.wav" &&
ffmpeg -y -i "$PROJ/结尾/$(ls $PROJ/结尾/*.mov | sed -n "${N}p")" -vn "$PROJ/结尾音频_${N}.wav" &&
ffmpeg -y -i "concat:$PROJ/开头音频_${N}.wav|$PROJ/结尾音频_${N}.wav" -acodec copy "$PROJ/参考音频_${N}.wav" &&
rm "$PROJ/开头音频_${N}.wav" "$PROJ/结尾音频_${N}.wav" &&
$GPT_ENV python "$SCRIPTS/run_gpt_sovits_tts.py" "$PROJ" --ref-wav "$PROJ/参考音频_${N}.wav" --output "配音_gpt_${N}.wav" &&
$ENV_PY "$SCRIPTS/cut_silence.py" "$PROJ" --input "配音_gpt_${N}.wav" --output "配音_gpt_cut_${N}" --num-segments $文案句数 &&
$ENV_PY "$SCRIPTS/select_materials.py" "$PROJ" --配音 "配音_gpt_cut_${N}.wav" --index $N &&
$ENV_PY "$SCRIPTS/generate_srt.py" "$PROJ" --配音 "配音_gpt_cut_${N}.wav" --文案 "文案_${N}.txt" --max-chars 9 &&
$ENV_PY "$SCRIPTS/transcribe.py" "$PROJ" --index $N &&
$ENV_PY "$SCRIPTS/create_draft.py" "$PROJ" "草稿名-${N}" --index $N
```

打开剪映 → 本地草稿 → 找到"草稿名-1" → 预览导出。

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `run_gpt_sovits_tts.py` | GPT-SoVITS 音色克隆配音 |
| `run_fish_tts.py` | Fish Speech TTS（备用） |
| `cut_silence.py` | 裁剪静音，每句独立WAV |
| `select_materials.py` | 智能选材，总时长=配音时长 |
| `generate_srt.py` | 生成字幕SRT |
| `transcribe.py` | Whisper识别开头结尾+合并字幕 |
| `create_draft.py` | 生成剪映草稿 |

## 字幕样式

金陵体 | 字号11 | 白色 | 居中 | Y=-500 | 阴影#3b3b3b | 去标点 | 9字换行 | 简体中文

## 技术栈

- **音色克隆**: GPT-SoVITS
- **语音识别**: OpenAI Whisper (small)
- **草稿生成**: pyJianYingDraft (capcut-mate)
- **音频处理**: numpy, soundfile, ffmpeg
- **输出**: 剪映专业版草稿

## 规则（锁定，不可违反）

1. 开头按文件名排序，第N组取第N个
2. 结尾先排非`_副本`，不够再补
3. 素材总时长严格=配音时长
4. GPT-SoVITS 零样本音色克隆
5. +10dB增益裁剪 + 文案句数约束
6. 配音在开头结束后开始
7. 竖屏 2160×3840
8. 每组独立文案+独立参考音频

## 许可证

MIT
