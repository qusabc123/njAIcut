---
name: ai-video-editor
description: "AI 智剪 — 短视频自动剪辑工具。GPT-SoVITS 音色克隆 + 剪映草稿自动化。"
---

# $ai-video-editor (njAIcut)

## 概述

AI 智剪是一个全自动短视频剪辑流水线：

```
写文案 → 克隆声音 → 配音 → 智能配画面 → 加字幕 → 生成剪映草稿
```

**核心能力：**
- **音色克隆**：GPT-SoVITS 零样本克隆，上传参考音频即可复刻任何声音
- **智能选材**：按文案段落匹配素材时长，总时长严格=配音时长
- **自动字幕**：去标点用空格、9字换行、金陵体、阴影美化的专业字幕
- **一键草稿**：输出到剪映，可直接预览和导出

---


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


## 快速开始

```bash
# 1. 设置环境变量
PROJ="/path/to/你的项目"
N=1   # 组编号

ENV_PY="/Users/nj/Documents/短视频创作/env/bin/python"
SCRIPTS="$(pwd)/scripts"
GPT_ENV="conda run -n GPTSoVits"

# 2. 一键执行（第N组）
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

---

## 项目结构

```
项目文件夹/
├── 开头/              # .mov 横屏素材（按文件名排序）
│   ├── IMG_0736.mov   # → 第1组用
│   ├── IMG_0737.mov   # → 第2组用
│   └── ...
├── 结尾/              # .mov 横屏素材（先排非`_副本`，不够再补`_副本`）
│   ├── IMG_0738.mov   # → 第1组用
│   └── ...
├── 车的素材/           # .mp4 竖屏素材（所有素材，智能选材）
│   ├── 素材01.mp4
│   └── ...
├── 文案_1.txt          # 第1组文案（用逗号、句号分割句子）
├── 文案_2.txt          # 第2组文案
└── ...
```

### 文案格式要求

文案用逗号句号分割句子，每个逗号/句号都会生成一条字幕：

```
身在罗马，开法拉利，这才是人生赢家。     ← 3条字幕
21年底的法拉利 Roma，仅行驶一万多公里。   ← 2条字幕
白外红内，经典配色，极品车况。            ← 3条字幕
```

---

## 固化规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | 开头选材 | `开头/` 按文件名排序，第 N 组取第 N 个 `.mov` |
| 2 | 结尾选材 | `结尾/` 按文件名排序，第 N 组取第 N 个 `.mov`（先排非`_副本`） |
| 3 | 中间选材 | 按文案段落分配素材 → 总时长 **严格**= 配音时长 |
| 4 | 配音模型 | GPT-SoVITS 零样本音色克隆 |
| 5 | 裁剪静音 | 裁剪 +10dB 增益检测 → 文案句数约束 → 每句独立 WAV |
| 6 | 配音对齐 | 配音在开头画面结束后开始 |
| 7 | 分辨率 | 竖屏 9:16（2160 × 3840） |
| 8 | 独立文案 | 每组独立文案_N.txt + 独立参考音频 |

---

## 字幕参数

| 参数 | 值 |
|------|-----|
| 字体 | 金陵体 |
| 字号 | 11 |
| 颜色 | 白色 |
| 位置 | 居中，X=0，Y=-500 |
| 不透明度 | 100% |
| 阴影 | #3b3b3b（15px扩散，5px距离，-45°角度） |
| 标点 | 去标点，用空格替换 |
| 换行 | 每行最多9字 |
| 语言 | 简体中文 |

---

## 完整8步流程详解

### 第1步：写文案

手动创建 `文案_N.txt`，用逗号句号感叹号问号分割句子。

**示例文案_1.txt：**
```
身在罗马，开法拉利，这才是人生赢家。
21年底的法拉利 Roma，仅行驶一万多公里。
白外红内，经典配色，全车原版原漆，极品车况。
3.9T V8，620匹马力，3.4秒破百。
前置后驱，2加2座椅，优雅与激情并存。
这台 Roma，让你的品味与众不同。
```

---

### 第2步：提取参考音频

从第N组开头和结尾素材中提取音频，合并后作为GPT-SoVITS的参考音色。

```bash
N=1

# 提取开头音频
ffmpeg -y -i "$PROJ/开头/$(ls $PROJ/开头/*.mov | sed -n "${N}p")" -vn "$PROJ/开头音频_N.wav"

# 提取结尾音频
ffmpeg -y -i "$PROJ/结尾/$(ls $PROJ/结尾/*.mov | sed -n "${N}p")" -vn "$PROJ/结尾音频_N.wav"

# 合并
ffmpeg -y -i "concat:$PROJ/开头音频_N.wav|$PROJ/结尾音频_N.wav" -acodec copy "$PROJ/参考音频_N.wav"

# 清理临时文件
rm "$PROJ/开头音频_N.wav" "$PROJ/结尾音频_N.wav"
```

**为什么合并？** 开头素材只有2.5~6秒，模型学习样本不足导致克隆音色不像。合并后6~10秒，克隆效果明显提升。

---

### 第3步：GPT-SoVITS 配音

零样本音色克隆，生成完整配音（含句间静音）。

```bash
$GPT_ENV python "$SCRIPTS/run_gpt_sovits_tts.py" "$PROJ" \
  --ref-wav "$PROJ/参考音频_N.wav" \
  --output "配音_gpt_N.wav"
```

**输入：** `参考音频_N.wav`（参考音色）+ `文案_N.txt`（配音内容）
**输出：** `配音_gpt_N.wav`（完整配音，35秒左右）

**环境要求：**
- Conda 环境 `GPTSoVits`
- GPT-SoVITS 安装在 `/tmp/GPT-SoVITS`
- 参考音频需3~10秒范围内
- 支持 MPS（Mac）和 CUDA（NVIDIA）

---

### 第4步：裁剪静音

将完整配音中的静音空隙剪掉，每句话独立保存为一个WAV文件。

```bash
# 先读文案句数，传入 --num-segments 确保段数精准对齐
文案句数=$(python3 -c "import re; f=open('$PROJ/文案_N.txt').read(); print(len([s for s in re.split(r'(?<=[，,。！？])',f) if s.strip()]))")

$ENV_PY "$SCRIPTS/cut_silence.py" "$PROJ" \
  --input "配音_gpt_N.wav" \
  --output "配音_gpt_cut_N" \
  --num-segments $文案句数
```

**内部流程：**
1. **+10dB 增益** → 仅用于检测，使语音和静音边界更清晰
2. **帧级能量检测** → 20ms帧、5ms步长，RMS阈值0.005
3. **500ms静音切分** → 检测"原子"说话区间
4. **文案句数约束** → 多了合并（最短静音处），少了拆分（最长静音处）
5. **保存原始音频** → 不受增益影响，保留原音质

**输出文件：**
```
配音_gpt_cut_N_001.wav     ← 第1句话
配音_gpt_cut_N_002.wav     ← 第2句话
...
配音_gpt_cut_N_NNN.wav     ← 第N句话
配音_gpt_cut_N_timestamps.json  ← 时间戳（字幕100%对齐用）
```

---

### 第5步：智能选材

按文案段落匹配素材，总时长严格等于配音时长。

```bash
$ENV_PY "$SCRIPTS/select_materials.py" "$PROJ" \
  --配音 "配音_gpt_cut_N.wav" --index N
```

**选材策略：**
1. 预加载 `素材时长.json` 缓存（避免 ffprobe 逐个扫描卡死）
2. 按文案段落数分配素材
3. 素材总时长 **严格=** 配音时长（最后一个素材裁剪填满）
4. 素材不够时重复最短素材（加 `__repeat__` 前缀标记）

**输出：** `素材列表_N.json`

```json
{
  "files": ["素材A.mp4", "素材B.mp4", ...],
  "audio_duration": 21.305,
  "total_duration": 21.305,
  "cut_last": {
    "file": "素材C.mp4",
    "duration": 0.646
  }
}
```

---

### 第6步：生成字幕SRT

从裁剪静音的时间戳直接匹配文案，100%对齐。

```bash
$ENV_PY "$SCRIPTS/generate_srt.py" "$PROJ" \
  --配音 "配音_gpt_cut_N.wav" \
  --文案 "文案_N.txt" \
  --max-chars 9
```

**功能：**
1. 读取时间戳JSON → 获取每段起止时间
2. 文案按逗号句号分割 → 与时间戳一一对应
3. 去标点用空格 → 字幕干净（"身在罗马，" → "身在罗马"）
4. 每行最多9字换行 → 适配竖屏手机观看
5. 简体中文

**输出：** `字幕.srt`

---

### 第7步：识别开头结尾 + 合并字幕

使用Whisper识别开头和结尾素材的说话内容，繁体转简体，合并到完整字幕。

```bash
$ENV_PY "$SCRIPTS/transcribe.py" "$PROJ" --index N
```

**功能：**
1. Whisper small模型 + zh语言 → 识别开头素材音频
2. 识别结尾素材音频
3. 繁体中文转简体中文（映射表）
4. 与第6步的配音字幕合并
5. 自动计算时间偏移（配音在开头画面结束后开始）

**输出：** `字幕_N.srt`

```
1
00:00:00,000 --> 00:00:02,500
欢迎收看本期视频    ← 开头内容（Whisper识别）

2
00:00:03,500 --> 00:00:04,330
身在罗马
开法拉利              ← 配音内容（17句）
...

19
00:00:24,700 --> 00:00:27,400
记得点赞关注        ← 结尾内容（Whisper识别）
```

---

### 第8步：生成剪映草稿

所有素材和字幕组装成剪映草稿，可直接打开预览。

```bash
$ENV_PY "$SCRIPTS/create_draft.py" "$PROJ" "草稿名-N" --index N
```

**组装逻辑（视频轨道）：**
```
| 开头(3.5s) | 素材1 | 素材2 | ... | 素材N | 结尾(3.4s) |
| ← 配音从开头结束后开始 → |
```

**配音轨道：** 多段独立WAV按顺序拼接，每段独立控制

**字幕轨道：** 金陵体 | 字号11 | 白色 | 居中 X=0 Y=-500 | 阴影#3b3b3b

**输出位置：**
```
/Users/nj/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/草稿名-N/
```

打开剪映 → 本地草稿 → 找到草稿名 → 预览和导出

---

## 多组并行

项目可以同时有4组（4个开头对应4个结尾对应4个文案）：

```bash
# 第1组
N=1 文案句数=17 执行流程

# 第2组
N=2 文案句数=15 执行流程

# 第3组
N=3 文案句数=12 执行流程

# 第4组
N=4 文案句数=10 执行流程
```

每组独立的文件：
```
文案_N.txt           ← 每组文案不同
参考音频_N.wav       ← 每组开头+结尾不同，音色不同
配音_gpt_N.wav       ← 每组配音内容不同
配音_gpt_cut_N_*.wav ← 每组裁剪分段不同
素材列表_N.json      ← 每组选材不同
字幕_N.srt           ← 每组字幕不同
草稿名-N             ← 每组草稿不同
```

---

## 常见问题

### Q: 配音质量不好，音色不像原声？
- 检查参考音频是否3~10秒
- 第2步已合并开头+结尾，仍不满意可以手动提供更长参考音频
- GPT-SoVITS 的 MPS 版本效果略低于 CUDA

### Q: select_materials.py 卡死？
- 已修复：预加载 `素材时长.json` 缓存
- 如果缓存不存在，首次会 ffprobe 扫描所有素材（25个文件约30秒）
- 之后运行从缓存读取，瞬间完成

### Q: 字幕位置不对？
- 默认 Y=-500（画面偏上位置，给底部留空间）
- 修改 `create_draft.py` 中的 `transform_y` 参数

### Q: 运行报错提示找不到模块？
- Python环境：`/Users/nj/Documents/短视频创作/env/bin/python`
- 确认安装了 numpy、soundfile、whisper
- pyJianYingDraft 需要从 capcut-mate 项目导入

---

## 相关链接

- [GitHub 仓库](https://github.com/qusabc123/njAIcut)
- GPT-SoVITS: [RVC-Boss/GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
- pyJianYingDraft: [capcut-mate](https://github.com/your-capcut-mate)
