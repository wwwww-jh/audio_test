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
    return re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", text)

def asr_large_api(audio_file_path: str, timeout: int = 300) -> str:
    url = "http://10.10.185.9:7861/asr_large"
    try:
        with open(audio_file_path, 'rb') as f:
            files = {'file': ('audio.wav', f, 'audio/wav')}
            resp = requests.post(url, headers={'accept':'application/json'}, files=files, timeout=timeout)
            resp.raise_for_status()
            return resp.json().get('result', "")
    except Exception as e:
        print(f"[ASR 接口错误] {e}")
        return ""
    


# 把所有模型接口注册到一个列表里
ASR_MODELS = [
    ("large", asr_large_api),
    # 以后可以继续新增 ("model_name", model_call_fn)
]

# 调整音量和混合
def adjust_volume(seg: AudioSegment, percent: float) -> AudioSegment:
    ratio = percent/100.0
    gain_db = 20*math.log10(ratio) if ratio>0 else -120
    return seg.apply_gain(gain_db)

# 混音，返回(人声音频, 噪声音频, 混合后音频)
def mix_tracks(vocal_path, noise_path, vol_v, vol_n):
    v = AudioSegment.from_file(vocal_path)
    n = AudioSegment.from_file(noise_path)
    v2 = adjust_volume(v, vol_v)
    n2 = adjust_volume(n, vol_n)
    # 长度对齐
    lv, ln = len(v2), len(n2)
    if lv > ln:
        n2 = (n2 * math.ceil(lv / ln))[:lv]
    else:
        n2 = n2[:lv]
    mix = v2.overlay(n2)
    return v2, n2, mix

# 播放并录音
def play_and_record(audio: AudioSegment) -> np.ndarray:
    fs = audio.frame_rate
    data = np.array(audio.get_array_of_samples()).reshape((-1, audio.channels))
    data = data.astype(np.float32)/float(2**(8*audio.sample_width-1))
    rec = sd.playrec(data, samplerate=fs, channels=1, dtype='float32')
    sd.wait()
    return rec

# 主流程
def main():
    base = os.getcwd()
    vocal_dir = os.path.join(base, '人声样本')
    noise_dir = os.path.join(base, '噪音样本')
    # 列出文件
    vocals = sorted([f for f in os.listdir(vocal_dir) if f.lower().endswith(('wav','mp3','flac','m4a'))])
    noises = sorted([f for f in os.listdir(noise_dir) if f.lower().endswith(('wav','mp3','flac','m4a'))])
    if not vocals or not noises:
        print('人声样本或噪音样本目录为空，退出。')
        return
    # 读取参考文本
    ref_texts = {}
    for v in vocals:
        txt = os.path.join(vocal_dir, os.path.splitext(v)[0]+'.txt')
        if os.path.isfile(txt):
            ref_texts[v] = open(txt, encoding='utf-8').read().strip()
        else:
            print(f'缺少参考文本: {txt}，该文件将被忽略')

    # 询问距离 —— #
    distance = float(input('请输入音源与麦克风的距离（米）：').strip())
    # 询问收音设备 —— #
    device_name = input('请输入收音设备名称：').strip()
    # 自动生成输出目录
    out_dir = f"{device_name}-{distance:.2f}m"
    os.makedirs(out_dir, exist_ok=True)
    print(f"结果将保存在目录：{out_dir}")

    # 测试参数采集
    n = int(input('请输入音量测试次数：').strip())
    params = []
    for i in range(1,n+1):
        vv = float(input(f'第{i}次：人声音量%:').strip())
        vn = float(input(f'第{i}次：噪声音量%:').strip())
        params.append((vv,vn))
    # 运行测试
    summary = []
    for v in vocals:
        if v not in ref_texts: continue
        vp = os.path.join(vocal_dir, v)
        for noise in noises:
            np_ = os.path.join(noise_dir, noise)
            for idx, (vv,vn) in enumerate(params,1):
                # 1. 混音并导出
                v2, n2, mix = mix_tracks(vp, np_, vv, vn)
                base_name = f"{os.path.splitext(v)[0]}_{os.path.splitext(noise)[0]}_{vv}_{vn}"
                mix_path = os.path.join(out_dir,f"mixed_{base_name}.wav")
                mix.export(mix_path, format='wav')

                # 计算 dB 差值
                db_diff = v2.dBFS - n2.dBFS


                # 2. 播放并录音
                rec = play_and_record(mix)
                rec16 = (np.clip(rec,-1,1)*32767).astype(np.int16)
                rec_path = os.path.join(out_dir,f"rec_{base_name}.wav")
                write(rec_path,mix.frame_rate,rec16)
                # 3. 分别调用 ASR
                for model_name, model_fn in ASR_MODELS:
                    hyp = model_fn(rec_path)
                    # 保存识别结果
                    res_path = os.path.join(out_dir, f"result_{model_name}_{base_name}.txt")
                    with open(res_path, 'w', encoding='utf-8') as f:
                        f.write(hyp)

                    # 计算 CER 并记录
                    c = cer(
                        clean_chinese_text(ref_texts[v]),
                        clean_chinese_text(hyp)
                    )
                    summary.append((v, noise, vv, vn, distance, device_name, db_diff, model_name, c))
                    print(f"{base_name} [{model_name}] 距离: {distance:.2f}m, 设备: {device_name}, dB差: {db_diff:.2f}dB, CER: {c*100:.2f}%")
    # 写 summary
    sum_file = os.path.join(out_dir, 'summary.txt')
    with open(sum_file, 'w', encoding='utf-8') as sf:
        sf.write('vocal\tnoise\tvol_v\tvol_n\tdistance_m\tdevice\tdB_diff\tmodel\tCER\n')
        for v, noise, vv, vn, dist, dev, db_diff, model_name, c in summary:
            sf.write(f'{v}\t{noise}\t{vv}\t{vn}\t{dist:.2f}\t{dev}\t{db_diff:.2f} dB\t{model_name}\t{c*100:.2f}%\n')
    print('全部完成，结果在', out_dir)

if __name__=='__main__':
    main()
