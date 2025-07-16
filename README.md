# Audio Test 自动化测试

本项目通过 Python 脚本实现批量音频测试：将人声样本与噪音样本按用户指定音量混合，播放并录制，调用可配置的 ASR 模型进行转写，计算错误率，并保存所有结果及汇总报告。

---

## 功能

* **批量处理**：对所有人声 × 噪音组合执行测试
* **多轮音量测试**：支持多组音量比例
* **自动混合**：按比例调整音量，循环或截断噪音以匹配人声长度
* **同步播放与录制**：使用 `sounddevice.playrec` 完成同步
* **多模型 ASR 集成**：可注册并调用多种 ASR 模型
* **错误率计算**：计算并记录 CER（字符错误率）
* **输出结果**：导出混合音频、录制音频、转写文本和 `summary.txt`

---

## 目录结构

```plaintext
project-root/
├── 人声样本/        # 存放人声音频 (.wav .mp3 .flac .m4a) 及同名 .txt 文本
│   ├── 1.wav
│   ├── 1.txt
│   └── ...
├── 噪音样本/        # 存放噪音音频
│   ├── x.wav
│   └── ...
├── audio_test.py    # 主脚本
├── README.md        # 项目说明（此文件）
└── requirements.txt # 依赖列表
```

---

## 环境与依赖

* Python 3.8 及以上
* 建议使用虚拟环境
* 系统需安装 [FFmpeg](https://ffmpeg.org)（用于 `pydub`）

安装方式：

```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
# .\venv\Scripts\activate  # Windows PowerShell

pip install -r requirements.txt
```

---

## 配置

1. 确保本地 ASR 服务已启动并可访问，默认接口地址：
   `http://10.10.185.9:7861/asr_large`
2. 可以继续新增 ("model_name", model_call_fn)到ASR_MODELS

---

## 使用说明

在激活虚拟环境后运行：

```bash
python audio_test.py
```

1. 输入结果保存目录名称，会在项目根创建该文件夹
2. 输入音量测试次数，例如 `2`
3. 按顺序输入每次的人声音量 % 和噪声音量 %

脚本将对每个人声 × 噪音组合及每组参数执行测试，生成以下文件：

* `mixed_<人声>_<噪音>_<音量人声>_<音量噪音>_<模型名称>.wav`
* `rec_<人声>_<噪音>_<音量人声>_<音量噪音>_<模型名称>.wav`
* `result_<人声>_<噪音>_<音量人声>_<音量噪音>_<模型名称>.txt`
* `summary.txt` （汇总所有测试的 CER）

---

