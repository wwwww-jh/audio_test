# Audio Test & Visualize 自动化音频测试与可视化

本仓库包含两个独立脚本：

* **`audio_test.py`**：对人声样本与噪音样本进行多参数、多模型的批量自动化测试，支持混音、播放、录制、ASR 转写与 CER 计算。
* **`visualize.py`**：批量扫描多个测试结果目录，合并 `summary.txt` 数据，并按 ASR 模型绘制交互式子图气泡图。

---

## 目录结构

```plaintext
project-root/
├── 人声样本/            # 存放人声音频 (.wav/.mp3/.flac/.m4a) 及同名参考文本 .txt
├── 噪音样本/            # 存放噪声音频
├── audio_test.py       # 自动化音频测试脚本
├── visualize.py        # 可视化与气泡图绘制脚本
├── requirements.txt    # Python 包依赖列表
└── README.md           # 本说明文档
```

---

## 环境与依赖

1. **系统组件**（请预先安装）：

   * **PortAudio**（为 `sounddevice` 提供播放/录音支持）

     * macOS：`brew install portaudio`
     * Ubuntu/Debian：`sudo apt install portaudio19-dev libportaudio2`
   * **FFmpeg**（为 `pydub` 处理各种音频格式）

     * macOS：`brew install ffmpeg`
     * Ubuntu/Debian：`sudo apt install ffmpeg`

2. **Python 依赖**（`requirements.txt`）：

   ```text
   pydub
   sounddevice
   numpy
   scipy
   requests
   jiwer
   pandas
   matplotlib
   ```

   > 若后续添加 Whisper 或 OpenAI API，请额外安装相应 SDK（如 `openai`、`whisper` 等）。

3. **快速安装**（使用 Conda 推荐）：

   ```bash
   git clone https://github.com/wwwww-jh/audio_test.git
   cd audio_test

   conda create -n audio_test_env python=3.10
   conda activate audio_test_env
   conda install -c conda-forge portaudio ffmpeg
   pip install -r requirements.txt
   ```

---

## 脚本一：`audio_test.py`

### 功能概览

* 批量混合：对所有人声 × 噪音 × 多模型组合执行测试。
* 参数化：按用户输入的“距离（m）”、“收音设备名称”与多组音量百分比自动生成测试目录。
* 同步播录：使用 `sounddevice.playrec` 完成音频播放与录制。
* 多模型 ASR：在脚本开头的 `ASR_MODELS` 注册任意多种 ASR 接口。
* 性能评估：计算并记录字符错误率（CER）。
* 输出结果：生成混合音频、录制音频、转写文本、以及带字段 `vocal, noise, vol_v, vol_n, distance_m, device, dB_diff, model, CER` 的 `summary.txt`。

### 使用步骤

```bash
python audio_test.py
```

1. **输入距离**：音源与麦克风的距离（米），例如 `1.20`。
2. **输入设备名称**：用于自动生成目录名，例如 `USB_MIC`。
3. **输入测试轮数**：例如 `2`，然后依次输入每轮的人声%与噪音%。

执行后在项目根会创建：

```
USB_MIC-1.20m/
├── mixed_<vocal>_<noise>_<vol_v>_<vol_n>.wav
├── rec_<vocal>_<noise>_<vol_v>_<vol_n>.wav
├── result_<model>_<vocal>_<noise>_<vol_v>_<vol_n>.txt
└── summary.txt
```

* **summary.txt** 示例表头：

  ```tsv
  vocal	noise	vol_v	vol_n	distance_m	device	dB_diff	model	CER
  ```

---

## 脚本二：`visualize.py`

### 功能概览

* 扫描指定根目录下所有包含 `summary.txt` 的子目录。
* 交互式选择要合并分析的目录（输入编号列表）。
* 提取核心字段：`vocal, noise, distance_m, device, dB_diff, model, CER`。
* 构建 `result.txt`（合并所有记录，制表符分隔）。
* 按 ASR 模型拆分子图，绘制气泡图：

  * **X 轴**：`distance_m`
  * **Y 轴**：`dB_diff`
  * **气泡尺寸**：`CER`（CER 越小，气泡越大）
  * **气泡颜色**：`device`
* 图表输出：`bubble_by_model.png`

### 使用步骤

```bash
python visualize.py 
```

1. 程序列出所有子目录，按提示输入要分析的目录编号（如 `1,3`）。
2. 会生成：

   * **`result.txt`**：合并后的原始记录表
   * **`bubble_by_model.png`**：按模型拆分的气泡图

---

## 示例

```bash
# 1. 运行多参数测试
python audio_test.py
# 输入：1.50 → USB_MIC → 2 → 80 & 20 → 60 & 40
# 生成目录：USB_MIC-1.50m/

# 2. 可视化分析
python visualize.py -r ./
# 选择目录编号：1  # 比如只有 USB_MIC-1.50m
# 输出 result.txt 和 bubble_by_model.png
```

---

> 📌 **提示**：此脚本运用本地ASR服务，默认接口地址：
>  http://10.10.185.9:7861/asr_large
> 如需自定义 ASR 模型，在 `audio_test.py` 中：
> ```python
> def asr_your_model(audio_path): ...
> ASR_MODELS.append(("your_model", asr_your_model))
> ```
> 处添加所需ASR模型

