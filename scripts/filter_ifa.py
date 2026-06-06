#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
去除黑名单中的 ifa 设备记录
输入: ifa_device_src.csv, black_ifa.txt
输出: ifa_device.csv
"""

import sys
import os

def load_black_ifa(black_ifa_file):
    """读取黑名单 ifa"""
    black_set = set()
    try:
        with open(black_ifa_file, 'r', encoding='utf-8') as f:
            for line in f:
                ifa = line.strip()
                if ifa:  # 忽略空行
                    black_set.add(ifa)
    except FileNotFoundError:
        print(f"错误: 找不到黑名单文件 {black_ifa_file}", file=sys.stderr)
        sys.exit(1)
    return black_set

def filter_ifa_device(src_file, black_set, output_file):
    """过滤 ifa 设备记录"""
    removed_count = 0
    kept_count = 0

    try:
        with open(src_file, 'r', encoding='utf-8') as infile, \
             open(output_file, 'w', encoding='utf-8') as outfile:

            for line in infile:
                line = line.rstrip('\n')
                if not line:  # 忽略空行
                    continue

                # 获取第一列 (ifa)
                parts = line.split(',')
                if not parts:
                    continue

                ifa = parts[0].strip()

                # 检查是否在黑名单中
                if ifa in black_set:
                    removed_count += 1
                    print(f"移除: {ifa}")
                else:
                    outfile.write(line + '\n')
                    kept_count += 1

    except FileNotFoundError:
        print(f"错误: 找不到源文件 {src_file}", file=sys.stderr)
        sys.exit(1)

    return kept_count, removed_count

def main():
    # 默认文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    black_ifa_file = os.path.join(parent_dir, 'black_ifa.txt')
    src_file = os.path.join(parent_dir, 'ifa_device_src.csv')
    output_file = os.path.join(parent_dir, 'ifa_device.csv')

    # 支持命令行参数覆盖
    if len(sys.argv) > 1:
        src_file = sys.argv[1]
    if len(sys.argv) > 2:
        black_ifa_file = sys.argv[2]
    if len(sys.argv) > 3:
        output_file = sys.argv[3]

    print(f"源文件: {src_file}")
    print(f"黑名单: {black_ifa_file}")
    print(f"输出文件: {output_file}")
    print("-" * 50)

    # 加载黑名单
    black_set = load_black_ifa(black_ifa_file)
    print(f"加载黑名单: {len(black_set)} 个 ifa")

    # 过滤并输出
    kept, removed = filter_ifa_device(src_file, black_set, output_file)

    print("-" * 50)
    print(f"处理完成:")
    print(f"  保留: {kept} 条记录")
    print(f"  移除: {removed} 条记录")
    print(f"  输出: {output_file}")

if __name__ == '__main__':
    main()
