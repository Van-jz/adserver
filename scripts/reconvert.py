#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新执行 purchase.log 中指定天数的 curl 请求
支持任意历史天数的数据重放，每个时间段可设置不同的执行比例
每个请求间隔随机 0.2-2 秒

用法示例:
  python3 reconvert.py --rate 0.1 --days "1:0.05,2:0.03"
  python3 reconvert.py --rate 0 --days "3:0.05,7:0.01"
"""

import re
import subprocess
import sys
import argparse
import random
import logging
import os
import time
import shlex
from datetime import datetime, timedelta
from typing import List, Tuple


def setup_logging() -> logging.Logger:
    """配置日志记录"""
    logger = logging.getLogger('reconvert')
    logger.setLevel(logging.INFO)

    # 控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # 格式化
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger


def parse_timestamp(timestamp_str: str) -> datetime:
    """
    解析时间戳字符串
    
    Args:
        timestamp_str: 时间戳字符串，格式如 "2026-02-11 08:05:16,811"
    
    Returns:
        datetime 对象
    """
    try:
        # 移除毫秒部分
        dt_str = timestamp_str.split(',')[0]
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        raise ValueError(f"无法解析时间戳 '{timestamp_str}': {e}")


def get_default_archive_dir(log_file: str) -> str:
    """根据当前日志文件路径推导默认归档目录"""
    log_dir = os.path.dirname(log_file) or '.'
    return os.path.join(log_dir, 'purchase_log')


def get_log_file_for_day(log_file: str, archive_dir: str, days_ago: int) -> str:
    """返回指定天数应读取的 purchase 日志文件"""
    if days_ago == 0:
        return log_file

    target_date = datetime.now() - timedelta(days=days_ago)
    archive_name = f"purchase_log.{target_date.strftime('%Y%m%d')}"
    return os.path.join(archive_dir, archive_name)


def extract_curl_commands(log_file: str, logger: logging.Logger, days_ago: int = 0, missing_ok: bool = False) -> List[Tuple[datetime, str]]:
    """
    从日志文件中提取指定天数前的过去一小时内的 curl 命令

    支持两种格式：
    1. purchase.log: 时间戳 + " - INFO - PURCHASE: curl ..."（含 token_null POST）
    2. 旧 convert_results.log: 时间戳 + " - INFO - 发送请求 2/2: curl ..."

    Args:
        log_file: 日志文件路径
        logger: 日志对象
        days_ago: 几天前（0=今天，1=昨天，2=前天，3=大前天）
        missing_ok: 文件不存在时是否跳过

    Returns:
        List of (timestamp, curl_command) tuples
    """
    now = datetime.now()
    # 计算目标时间点（几天前的此刻）
    target_time = now - timedelta(days=days_ago)
    # 目标时间点的前一小时
    one_hour_ago = target_time - timedelta(hours=1)

    logger.info(f"  日志文件: {os.path.abspath(log_file)}")
    logger.info(f"  时间窗口: {one_hour_ago.strftime('%Y-%m-%d %H:%M:%S')} ~ {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    curl_commands = []
    
    # 匹配 purchase.log 格式 或 旧 convert_results.log 格式
    pattern_purchase = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - INFO - PURCHASE: (curl .+)$'
    )
    pattern_legacy = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - INFO - 发送请求 2/2: (curl .+)$'
    )
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        i = 0
        while i < len(lines):
            line = lines[i].rstrip('\n')
            
            # 匹配 PURCHASE 或 发送请求 2/2 格式
            match = pattern_purchase.match(line) or pattern_legacy.match(line)
            if match:
                timestamp_str = match.group(1)
                curl_cmd_start = match.group(2)
                
                # curl 命令可能跨多行，需要继续读取
                # 检查是否以单引号结束（URL 通常用单引号包裹）
                curl_cmd = curl_cmd_start
                
                # 如果命令未完整（可能包含换行），继续读取后续行
                # 通常 curl 命令会在同一行，但如果 -w 参数中有换行，可能需要多行
                # 检查是否以单引号结束
                quote_count = curl_cmd.count("'")
                
                # 如果引号数量是奇数，说明命令可能跨行
                # 或者检查命令是否以单引号结尾（未闭合）
                if quote_count % 2 == 1 or curl_cmd.rstrip().endswith("'"):
                    # 继续读取下一行，直到引号闭合或遇到新的日志行（以时间戳开头）
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].rstrip('\n')
                        
                        # 如果下一行是新的日志行（以时间戳开头），停止
                        if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', next_line):
                            break
                        
                        # 合并到 curl 命令中
                        curl_cmd += ' ' + next_line
                        quote_count = curl_cmd.count("'")
                        
                        # 如果引号闭合，停止
                        if quote_count % 2 == 0 and not curl_cmd.rstrip().endswith("'"):
                            break
                        
                        i += 1
                
                try:
                    timestamp = parse_timestamp(timestamp_str)

                    # 只处理指定时间范围内的记录（target_time 的过去一小时）
                    if one_hour_ago <= timestamp <= target_time:
                        curl_commands.append((timestamp, curl_cmd))
                except ValueError as e:
                    logger.warning(f"跳过无效时间戳的行: {e}")
            
            i += 1
    
    except FileNotFoundError:
        if missing_ok:
            logger.warning(f"日志文件不存在，跳过: {log_file}")
            return []
        logger.error(f"日志文件不存在: {log_file}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"读取日志文件失败: {e}")
        sys.exit(1)
    
    return curl_commands


def execute_curl_command(curl_cmd: str, logger: logging.Logger) -> Tuple[bool, str]:
    """
    执行 curl 命令
    
    Args:
        curl_cmd: curl 命令字符串
        logger: 日志对象
    
    Returns:
        (success, response) tuple
    """
    try:
        # 解析 curl 命令
        # curl 命令格式: curl -x proxy -s -w 'HTTP_CODE:%{http_code}' 'url'
        # 需要正确处理引号内的内容
        
        # 使用 shlex 来安全地分割命令
        parts = shlex.split(curl_cmd)
        
        logger.info(f"执行: {curl_cmd}")
        
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout.strip()
        http_code_match = re.search(r'HTTP_CODE:(\d+)', output)
        
        if http_code_match:
            http_code = http_code_match.group(1)
            response_body = output.replace(f'HTTP_CODE:{http_code}', '').strip()
            
            if result.returncode == 0 and http_code.startswith('2'):
                logger.info(f"请求成功 - HTTP {http_code} - 响应: {response_body}")
                return True, response_body
            else:
                logger.error(f"请求失败 - HTTP {http_code} - 返回码: {result.returncode}")
                if result.stderr:
                    logger.error(f"错误信息: {result.stderr}")
                return False, response_body
        else:
            logger.error(f"无法解析 HTTP 状态码 - 输出: {output}")
            if result.stderr:
                logger.error(f"错误信息: {result.stderr}")
            return False, output
    
    except subprocess.TimeoutExpired:
        logger.error("请求超时（60秒）")
        return False, "Timeout"
    except Exception as e:
        logger.error(f"执行 curl 命令失败: {e}")
        return False, str(e)


def parse_days_config(days_str: str) -> List[Tuple[int, float]]:
    """
    解析 --days 参数，格式: "1:0.05,2:0.03,7:0.01"

    Args:
        days_str: 天数:比例 的逗号分隔字符串

    Returns:
        List of (days_ago, rate) tuples，按 days_ago 升序排列
    """
    configs = []
    for item in days_str.split(','):
        item = item.strip()
        if not item:
            continue
        parts = item.split(':')
        if len(parts) != 2:
            raise ValueError(f"格式错误 '{item}'，应为 '天数:比例'，如 '1:0.05'")
        try:
            days_ago = int(parts[0])
            rate = float(parts[1])
        except ValueError:
            raise ValueError(f"格式错误 '{item}'，天数必须为整数，比例必须为数字")
        if days_ago < 1:
            raise ValueError(f"天数必须 >= 1，当前值: {days_ago}")
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"day{days_ago} 的比例必须在 0.0-1.0 之间，当前值: {rate}")
        configs.append((days_ago, rate))
    configs.sort(key=lambda x: x[0])
    return configs


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='重新执行 purchase.log 中指定天数的 PURCHASE curl 请求',
        epilog='示例: %(prog)s --rate 0.1 --days "1:0.05,2:0.03,7:0.01"'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        default='../purchase.log',
        help='日志文件路径（默认: purchase.log，支持 PURCHASE 格式及 token_null POST）'
    )
    parser.add_argument(
        '--archive-dir',
        type=str,
        default=None,
        help='历史 purchase 日志归档目录（默认: --log-file 同级目录下的 purchase_log）'
    )
    parser.add_argument(
        '--rate',
        type=float,
        default=0.1,
        help='今天的执行比例，0.0-1.0 之间（默认: 0.1）'
    )
    parser.add_argument(
        '--days',
        type=str,
        default='',
        help='历史天数重放配置，格式: "天数:比例,..."，如 "1:0.05,2:0.03,7:0.01"'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='只统计匹配数量，不执行 curl 命令（用于调试验证）'
    )

    args = parser.parse_args()

    # 验证 rate 参数
    if not 0.0 <= args.rate <= 1.0:
        print(f"错误: rate 必须在 0.0 到 1.0 之间，当前值: {args.rate}", file=sys.stderr)
        sys.exit(1)

    # 解析 --days 参数
    days_configs = []
    if args.days:
        try:
            days_configs = parse_days_config(args.days)
        except ValueError as e:
            print(f"错误: --days 参数解析失败: {e}", file=sys.stderr)
            sys.exit(1)

    logger = setup_logging()
    archive_dir = args.archive_dir or get_default_archive_dir(args.log_file)

    # 构建完整的配置列表：(days_ago, rate, label)
    day_configs = [(0, args.rate, '今天')]
    for days_ago, rate in days_configs:
        day_configs.append((days_ago, rate, f'{days_ago}天前'))

    logger.info("=" * 80)
    logger.info(f"开始重新执行 curl 请求 - 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"今天日志文件: {os.path.abspath(args.log_file)}")
    logger.info(f"历史归档目录: {os.path.abspath(archive_dir)}")
    for days_ago, rate, label in day_configs:
        logger.info(f"  {label}执行比例: {rate * 100:.1f}%")
    logger.info("=" * 80)

    dry_run = args.dry_run
    if dry_run:
        logger.info("*** DRY RUN 模式：只统计不执行 ***")

    total_success = 0
    total_fail = 0
    total_executed = 0

    # 处理每一天的数据
    for days_ago, rate, day_label in day_configs:
        if rate == 0.0:
            logger.info(f"\n跳过{day_label}（rate=0.0）")
            continue

        logger.info(f"\n{'=' * 80}")
        logger.info(f"处理{day_label}的数据（{days_ago} 天前）")
        logger.info(f"{'=' * 80}")

        # 提取 curl 命令
        log_file = get_log_file_for_day(args.log_file, archive_dir, days_ago)
        logger.info(f"正在提取{day_label}过去一小时内的 curl 命令...")
        curl_commands = extract_curl_commands(log_file, logger, days_ago, missing_ok=(days_ago > 0))

        if not curl_commands:
            logger.info(f"未找到{day_label}过去一小时内的 curl 命令")
            continue

        logger.info(f"找到 {len(curl_commands)} 条 curl 命令")

        # 根据 rate 筛选要执行的命令
        if rate < 1.0:
            selected_commands = [
                (ts, cmd) for ts, cmd in curl_commands
                if random.random() < rate
            ]
            logger.info(f"根据 rate={rate} 筛选后，将执行 {len(selected_commands)} 条命令")
        else:
            selected_commands = curl_commands

        if not selected_commands:
            logger.info(f"{day_label}没有命令需要执行")
            continue

        # 执行 curl 命令
        success_count = 0
        fail_count = 0

        logger.info(f"开始执行{day_label}的 curl 命令...")
        for idx, (timestamp, curl_cmd) in enumerate(selected_commands, 1):
            logger.info(f"执行第 {idx}/{len(selected_commands)} 条命令 - 原始时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            if dry_run:
                logger.info(f"  [DRY RUN] {curl_cmd[:120]}...")
                success_count += 1
                continue

            success, response = execute_curl_command(curl_cmd, logger)

            if success:
                success_count += 1
            else:
                fail_count += 1

            # 每个命令间隔随机 0.2-2 秒（最后一条不需要等待）
            if idx < len(selected_commands):
                sleep_time = random.uniform(0.2, 2.0)
                time.sleep(sleep_time)

        # 输出当天统计信息
        logger.info(f"\n{day_label}执行完成统计:")
        logger.info(f"   总命令数: {len(selected_commands)}")
        logger.info(f"   成功: {success_count}")
        logger.info(f"   失败: {fail_count}")
        if len(selected_commands) > 0:
            success_rate = (success_count / len(selected_commands)) * 100
            logger.info(f"   成功率: {success_rate:.2f}%")

        total_success += success_count
        total_fail += fail_count
        total_executed += len(selected_commands)

    # 输出总体统计信息
    logger.info("\n" + "=" * 80)
    logger.info("总体执行完成统计:")
    logger.info(f"   总命令数: {total_executed}")
    logger.info(f"   成功: {total_success}")
    logger.info(f"   失败: {total_fail}")
    if total_executed > 0:
        overall_success_rate = (total_success / total_executed) * 100
        logger.info(f"   总成功率: {overall_success_rate:.2f}%")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
