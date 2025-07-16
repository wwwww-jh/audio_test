#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
visualize.py

集成数据提取与气泡图绘制：
- 扫描指定根目录下所有包含 summary.txt 的子目录
- 交互式选择要分析的文件夹
- 提取 vocal, noise, distance_m, device, dB_diff, model, CER
- 绘制气泡图：X=distance_m, Y=dB_diff, 气泡大小=CER, 颜色=model
- 保存结果表 result.txt 和图表 bubble.png
"""
import os
import re
import argparse
import csv

import pandas as pd
import matplotlib.pyplot as plt


def find_summary_dirs(root_dir):
    dirs = []
    for name in os.listdir(root_dir):
        full = os.path.join(root_dir, name)
        if os.path.isdir(full) and os.path.isfile(os.path.join(full, 'summary.txt')):
            dirs.append(name)
    return sorted(dirs)


def select_dirs(dirs):
    print("发现以下可选目录：")
    for idx, d in enumerate(dirs, start=1):
        print(f"{idx}. {d}")
    sel = input("请输入要合并的目录编号（逗号分隔，例如 1,3）：").strip()
    nums = [int(x) for x in re.split(r'[,\s]+', sel) if x.isdigit()]
    return [dirs[i-1] for i in nums if 1 <= i <= len(dirs)]


def parse_summary(path):
    """
    解析 summary.txt，返回记录列表
    仅保留 vocal, noise, distance_m, device, dB_diff, model, CER
    """
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        header = f.readline().strip().split('\t')
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) != len(header):
                continue
            rec = dict(zip(header, parts))
            # 转数值
            rec['distance_m'] = float(rec['distance_m'])
            rec['dB_diff']    = float(rec['dB_diff'].replace(' dB', ''))
            # CER 百分号转数
            rec['CER']        = float(rec['CER'].replace('%',''))
            # 取所需字段
            subset = {
                'vocal': rec['vocal'],
                'noise': rec['noise'],
                'distance_m': rec['distance_m'],
                'device': rec['device'],
                'dB_diff': rec['dB_diff'],
                'model': rec['model'],
                'CER': rec['CER'],
            }
            rows.append(subset)
    return rows


def plot_bubble(df, out_file='bubble.png'):
    """
    气泡图：
    X=distance_m, Y=dB_diff, 气泡大小=CER, 颜色=model
    """
    fig, ax = plt.subplots()
    # 根据 CER 调整气泡大小
    sizes = (df['CER'] - df['CER'].min() + 1) * 50
    # 分模型绘制
    for model, group in df.groupby('model'):
        ax.scatter(
            group['distance_m'],
            group['dB_diff'],
            s=sizes[group.index],
            label=model,
            alpha=0.6,
            edgecolors='w',
            linewidth=0.5,
        )
    ax.set_xlabel('Distance (m)')
    ax.set_ylabel('dB Difference')
    ax.set_title('Bubble Chart: Distance vs dB_diff, Bubble=CER, Color=Model')
    ax.legend(title='Model')
    fig.tight_layout()
    fig.savefig(out_file)
    print(f"已保存气泡图: {out_file}")


def main():
    parser = argparse.ArgumentParser(
        description='合并 summary.txt 并绘制气泡图'
    )
    parser.add_argument(
        '--root', '-r',
        default=os.getcwd(),
        help='根目录，包含各实验子目录'
    )
    args = parser.parse_args()

    # 扫描
    dirs = find_summary_dirs(args.root)
    if not dirs:
        print("未找到包含 summary.txt 的子目录，退出。")
        return
    # 选择
    selected = select_dirs(dirs)
    if not selected:
        print("未选择任何目录，退出。")
        return

    # 合并数据
    all_rows = []
    for d in selected:
        path = os.path.join(args.root, d, 'summary.txt')
        rows = parse_summary(path)
        all_rows.extend(rows)

    # 构造 DataFrame
    df = pd.DataFrame(all_rows)

    # 保存合并结果
    result_path = os.path.join(args.root, 'result.txt')
    df.to_csv(result_path, sep='\t', index=False)
    print(f"已将合并数据保存至: {result_path}")

    # 绘制气泡图
    plot_bubble(df)

if __name__ == '__main__':
    main()
