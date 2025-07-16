import os
import re
import argparse
import csv

def find_summary_dirs(root_dir):
    """返回所有包含 summary.txt 的子目录名字列表"""
    dirs = []
    for name in os.listdir(root_dir):
        full = os.path.join(root_dir, name)
        if os.path.isdir(full) and os.path.isfile(os.path.join(full, 'summary.txt')):
            dirs.append(name)
    return sorted(dirs)


def select_dirs(dirs):
    """交互式选择目录，返回选中的目录名字列表"""
    print("发现以下可选目录：")
    for idx, d in enumerate(dirs, 1):
        print(f"{idx}. {d}")
    sel = input("请输入要合并的目录编号（逗号分隔，例如 1,3）：").strip()
    nums = [int(x) for x in re.split(r'[,\s]+', sel) if x.isdigit()]
    chosen = [dirs[i-1] for i in nums if 1 <= i <= len(dirs)]
    return chosen


def parse_summary(path):
    """
    解析单个 summary.txt，返回 header 列表和记录列表
    将 vol_v, vol_n, distance_m, dB_diff, CER 转为 float
    """
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        header = f.readline().strip().split('\t')
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) != len(header):
                continue
            rec = dict(zip(header, parts))
            # 转数值字段
            rec['distance_m'] = float(rec['distance_m'])
            rec['dB_diff']    = float(rec['dB_diff'].replace(' dB',''))
            rec['CER']        = float(rec['CER'].replace('%',''))
            rows.append(rec)
    return header, rows


def main():
    parser = argparse.ArgumentParser(
        description="合并多个实验文件夹下 summary.txt 中的数据，输出 result.txt"
    )
    parser.add_argument(
        '--root', '-r',
        default=os.getcwd(),
        help='存放各实验子目录的根目录（默认当前目录）'
    )
    args = parser.parse_args()

    # 1. 找到所有包含 summary.txt 的子目录
    dirs = find_summary_dirs(args.root)
    if not dirs:
        print("在根目录未发现任何包含 summary.txt 的子目录，退出。")
        return

    # 2. 交互式选择
    chosen = select_dirs(dirs)
    if not chosen:
        print("未选择任何目录，退出。")
        return

    # 3. 解析并合并
    all_rows = []
    raw_header = None
    for d in chosen:
        path = os.path.join(args.root, d, 'summary.txt')
        h, rows = parse_summary(path)
        if raw_header is None:
            raw_header = h
        all_rows.extend(rows)

    # 4. 构造输出表头 (去除 vol_v, vol_n)
    out_header = [col for col in raw_header if col not in ('vol_v','vol_n')]

    # 5. 输出 result.txt
    out_path = os.path.join(args.root, 'result.txt')
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=out_header, delimiter='\t')
        writer.writeheader()
        for r in all_rows:
            # 仅写入需要的字段
            filtered = {col: r[col] for col in out_header}
            writer.writerow(filtered)

    print(f"已将合并数据保存到：{out_path}")

if __name__ == '__main__':
    main()
