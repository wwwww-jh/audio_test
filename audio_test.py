import os
import math
import re
import requests
import numpy as np
from pydub import AudioSegment
import sounddevice as sd
from scipy.io.wavfile import write
from jiwer import cer

# —— 辅助函数 ——

def clean_chinese_text(text: str) -> str:
    """只保留汉字、数字和英文字母，去除其他字符。"""
    return re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", text)


def asr_large_api(audio_file_path: str, timeout: int = 300) -> str:
    """调用本地 ASR 接口，返回识别文本。"""
    url = "http://10.10.185.9:7861/asr_large"
    headers = {'accept': 'application/json'}
    files = {'file': ('audio.wav', open(audio_file_path, 'rb'), 'audio/wav')}
    try:
        resp = requests.post(url, headers=headers, files=files, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get('result', "")
    except Exception as e:
        print(f"[ASR 接口错误] {e}")
        return ""

# —— 音频处理函数 ——

def adjust_volume(seg: AudioSegment, percent: float) -> AudioSegment:
    if not (0 <= percent <= 100):
        raise ValueError("音量百分比应在 0-100 之间")
    ratio = percent / 100.0
    gain_dB = 20 * math.log10(ratio) if ratio > 0 else -120
    return seg.apply_gain(gain_dB)


def mix_tracks(vocal_path: str, noise_path: str, vol1: float, vol2: float) -> AudioSegment:
    """
    根据百分比调整人声和噪声音量；
    若人声更长则循环噪声至等长；若噪声更长则截断至人声长度；
    最后叠加并返回混合音频。
    """
    v = AudioSegment.from_file(vocal_path)
    n = AudioSegment.from_file(noise_path)
    v2 = adjust_volume(v, vol1)
    n2 = adjust_volume(n, vol2)
    len_v, len_n = len(v2), len(n2)
    if len_v > len_n:
        repeats = math.ceil(len_v / len_n)
        n2 = (n2 * repeats)[:len_v]
    else:
        n2 = n2[:len_v]
    return v2.overlay(n2)


def play_and_record(audio: AudioSegment, fs: int) -> np.ndarray:
    """使用 playrec 同步播放混合音频并录制麦克风输入（单声道）。"""
    data = np.array(audio.get_array_of_samples()).reshape((-1, audio.channels))
    dtype_max = float(2 ** (8 * audio.sample_width - 1))
    data = data.astype(np.float32) / dtype_max
    rec = sd.playrec(data, samplerate=fs, channels=1, dtype='float32')
    sd.wait()
    return rec


def compute_wer(ref: str, hyp: str) -> float:
    r, h = ref.strip().split(), hyp.strip().split()
    d = [[0]*(len(h)+1) for _ in range(len(r)+1)]
    for i in range(len(r)+1): d[i][0] = i
    for j in range(len(h)+1): d[0][j] = j
    for i in range(1, len(r)+1):
        for j in range(1, len(h)+1):
            d[i][j] = d[i-1][j-1] if r[i-1]==h[j-1] else 1+min(d[i-1][j], d[i][j-1], d[i-1][j-1])
    return d[len(r)][len(h)] / max(1, len(r))


def select_file_from_dir(directory: str, extensions=('wav','mp3','flac','m4a')) -> str:
    """
    列出目录下指定扩展名的音频文件，让用户通过输入序号选择。
    支持 wav, mp3, flac, m4a 格式。
    """
    files = [f for f in os.listdir(directory) if f.lower().endswith(extensions)]
    if not files:
        print(f"目录 '{directory}' 中没有音频文件。")
        return ''
    print(f"请选择目录 '{directory}' 中的文件：")
    for idx, fname in enumerate(files, 1):
        print(f"  {idx}. {fname}")
    while True:
        choice = input(f"输入序号 (1-{len(files)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(files):
            return os.path.join(directory, files[int(choice)-1])
        print("无效输入，请重新输入。")


def main():
    base_dir = os.getcwd()
    vocal_dir = os.path.join(base_dir, '人声样本')
    noise_dir = os.path.join(base_dir, '噪音样本')

    vocal_path = select_file_from_dir(vocal_dir)
    noise_path = select_file_from_dir(noise_dir)
    if not vocal_path or not noise_path:
        print("未选择有效的音频文件，退出。")
        return

    output_folder = input("请输入结果保存目录名称：").strip()
    os.makedirs(output_folder, exist_ok=True)

    base = os.path.splitext(os.path.basename(vocal_path))[0]
    ref_file = os.path.join(vocal_dir, base + ".txt")
    if not os.path.isfile(ref_file):
        print(f"找不到参考文本文件：{ref_file}")
        return
    with open(ref_file, encoding="utf-8") as f:
        ref_text = f.read().strip()

    try:
        n_tests = int(input("请输入测试次数：").strip())
    except ValueError:
        print("请输入有效的整数。")
        return
    test_params = []
    for i in range(1, n_tests + 1):
        print(f"\n第 {i} 次测试参数：")
        v1 = float(input("  人声音量百分比 (0-100)：").strip())
        v2 = float(input("  噪声音量百分比 (0-100)：").strip())
        test_params.append((v1, v2))

    summary = []
    for idx, (v1, v2) in enumerate(test_params, start=1):
        print(f"\n--- 执行第 {idx} 次测试 ---")
        mixed = mix_tracks(vocal_path, noise_path, v1, v2)
        mixed_path = os.path.join(output_folder, f"mixed{idx}.wav")
        mixed.export(mixed_path, format="wav")

        rec = play_and_record(mixed, mixed.frame_rate)
        rec_int16 = np.clip(rec, -1, 1)
        rec_int16 = (rec_int16 * 32767).astype(np.int16)
        rec_path = os.path.join(output_folder, f"rec{idx}.wav")
        write(rec_path, mixed.frame_rate, rec_int16)

        hyp = asr_large_api(rec_path)
        res_path = os.path.join(output_folder, f"result{idx}.txt")
        with open(res_path, "w", encoding="utf-8") as f:
            f.write(hyp)

        cer_val = cer(clean_chinese_text(ref_text), clean_chinese_text(hyp))
        summary.append((idx, v1, v2, cer_val))
        print(f"第 {idx} 次测试 CER: {cer_val*100:.2f}%")

    summary_path = os.path.join(output_folder, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        for idx, v1, v2, c in summary:
            f.write(f"测试{idx}: 人声{v1}% 噪音{v2}% CER {c*100:.2f}%\n")
    print(f"\n所有测试完成，结果保存在：{output_folder}")

if __name__ == "__main__":
    main()