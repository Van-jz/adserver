#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一编排脚本 - 整合日志处理、频率控制和URL请求"""

import json
import sys
import os
import argparse
import logging
import urllib.parse
import random
import re
import hashlib
import time
import subprocess
import shlex
import glob
from datetime import datetime
from typing import Dict, Any, Optional, List, Set, Tuple, Iterator
from collections import defaultdict

BLOCKED_DOMAINS = ('ad.ap4r.com', 's16.kwai.net', 'adx.opera.com', 'liftoff-creatives.io')
VALUE_PROBS = [(5, 5), (45, 10), (60, 20), (74, 30), (83, 40), (90, 50), (95, 60), (98, 80), (100, 100)]

# token=null 时的 POST 请求配置
NULL_TOKEN_API_URL = 'https://ads.mythad.com/log/common'
NULL_TOKEN_HEADERS = {
    'accept': '*/*',
    'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'cache-control': 'no-cache',
    'content-type': 'application/json',
    'dnt': '1',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Chromium";v="{chrome_ver}", "Google Chrome";v="{chrome_ver}", "Not.A/Brand";v="24"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'sec-fetch-storage-access': 'none',
}

# Android 设备型号池（型号, Build ID 前缀）
ANDROID_DEVICES = [
    ('SM-A546E', 'UP1A.231005.007'), ('SM-G998B', 'UP1A.231005.007'),
    ('SM-G996B', 'UP1A.231005.007'), ('SM-G991B', 'UP1A.231005.007'),
    ('SM-S918B', 'UP1A.231005.007'), ('SM-S916B', 'UP1A.231005.007'),
    ('SM-S911B', 'UP1A.231005.007'), ('SM-F936B', 'UP1A.231005.007'),
    ('SM-F721B', 'UP1A.231005.007'), ('SM-A536E', 'UP1A.231005.007'),
    ('Pixel 7 Pro', 'UP1A.231005.007'), ('Pixel 7', 'UP1A.231005.007'),
    ('Pixel 6 Pro', 'SD1A.808817.019'), ('Pixel 6', 'SD1A.808817.019'),
    ('Pixel 8 Pro', 'UD1A.231005.007'), ('Pixel 8', 'UD1A.231005.007'),
    ('SM-X710', 'UP1A.231005.007'), ('RMX3830', 'UP1A.231005.007'),
    ('CPH2513', 'UP1A.231005.007'), ('V2238', 'UP1A.231005.007'),
]

# Chrome 版本池（版本号, WebKit 版本）
CHROME_VERSIONS = [
    ('125', '537.36'), ('126', '537.36'), ('127', '537.36'),
    ('128', '537.36'), ('124', '537.36'), ('123', '537.36'),
    ('122', '537.36'), ('121', '537.36'), ('120', '537.36'),
]

# Android 系统版本池
ANDROID_VERSIONS = ['12', '13', '14', '15']


def _generate_random_android_ua() -> Tuple[str, str, str]:
    """生成随机 Android User-Agent，返回 (ua_string, sec_ch_ua, platform_version)"""
    device, build_prefix = random.choice(ANDROID_DEVICES)
    chrome_ver, webkit_ver = random.choice(CHROME_VERSIONS)
    android_ver = random.choice(ANDROID_VERSIONS)
    build_id = build_prefix
    ua = f'Mozilla/5.0 (Linux; Android {android_ver}; {device} Build/{build_id}) AppleWebKit/{webkit_ver} (KHTML, like Gecko) Chrome/{chrome_ver}.0.0.0 Mobile Safari/{webkit_ver}'
    sec_ch_ua = f'"Chromium";v="{chrome_ver}", "Google Chrome";v="{chrome_ver}", "Not.A/Brand";v="24"'
    return ua, sec_ch_ua, android_ver


def _iter_pixelid_token_rows(file_path: str) -> Iterator[Tuple[str, str, Optional[str]]]:
    """解析 pixelid_token_cnt.txt，yield (pixelid, token, cnt_opt)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or 'pixel_id' in line.lower() or '→' in line:
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                pixelid, token = parts[0], parts[1]
                if token != 'null' and not (35 <= len(token) <= 50):
                    continue
                yield (pixelid, token, parts[2] if len(parts) >= 3 else None)
    except FileNotFoundError:
        print(f"警告: 文件 '{file_path}' 不存在", file=sys.stderr)
    except Exception as e:
        print(f"警告: 读取文件失败: {e}", file=sys.stderr)


def load_pixelid_set(file_path: str) -> Set[str]:
    """从 pixelid_token_cnt.txt 构建 pixelid 集合"""
    s = set(r[0] for r in _iter_pixelid_token_rows(file_path))
    if s:
        print(f"从 {file_path} 加载了 {len(s)} 个有效 pixel_id")
    return s


def extract_request_body(log_line: str) -> Optional[str]:
    """从日志行中提取 requestBody"""
    marker = '收到 kwaiadsinfo postshow 请求数据: '
    pos = log_line.find(marker)
    return log_line[pos + len(marker):].strip() if pos >= 0 else None


def parse_json_data(request_body_str: str) -> Optional[Dict[str, Any]]:
    """解析 requestBody，支持直接 JSON 或 data= 开头的 URL 编码格式"""
    try:
        s = urllib.parse.unquote(request_body_str[5:]) if request_body_str.startswith('data=') else request_body_str
        return json.loads(s)
    except (json.JSONDecodeError, Exception) as e:
        print(f"警告: 解析失败: {e}", file=sys.stderr)
        return None


def extract_referrer_package(json_data: Dict[str, Any]) -> Optional[str]:
    """从 JSON 提取 referrer_package（bundle），支持 data 为 dict 或 JSON 字符串"""
    try:
        data = json_data.get('data')
        if data is None:
            return None
        if isinstance(data, dict):
            return data.get('referrer_package')
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    return parsed.get('referrer_package')
            except (json.JSONDecodeError, Exception):
                pass
        return None
    except Exception:
        return None


def extract_urls_from_data(json_data: Dict[str, Any]) -> list:
    """从 JSON 提取 URLs：data 为 dict 取 urls 数组，为 str 则正则提取"""
    try:
        data = json_data.get('data')
        if data is None:
            return []
        if isinstance(data, dict):
            urls = data.get('urls', [])
            return urls if isinstance(urls, list) else []
        if isinstance(data, str):
            return re.findall(r'https?://[^\s]+', data)
        return []
    except Exception as e:
        print(f"警告: 提取URLs失败: {e}", file=sys.stderr)
        return []


def _bundle_map_warn(logger: Optional[logging.Logger], message: str) -> None:
    """输出 bundle map 兼容处理警告。"""
    if logger:
        logger.warning(message)
    else:
        print(f"警告: {message}", file=sys.stderr)


def _parse_bundle_timestamp(value: Any) -> Optional[int]:
    """解析 Unix 秒级时间戳，非法时返回 None。"""
    if isinstance(value, bool) or value is None:
        return None
    try:
        timestamp = int(value)
        return timestamp if timestamp >= 0 else None
    except (TypeError, ValueError):
        return None


def load_bundle_map(
    bundle_map_file: str,
    logger: Optional[logging.Logger] = None
) -> Tuple[Dict[str, Dict[str, Any]], bool, Dict[str, int]]:
    """
    加载 click_id -> bundle 映射，并统一迁移为:
    click_id -> {'bundle': bundle, 'timestamp': unix_seconds}

    Returns:
        (normalized_map, changed, stats)
    """
    stats = {
        'total': 0,
        'migrated': 0,
        'timestamp_fixed': 0,
        'skipped_invalid': 0
    }
    if not bundle_map_file:
        return {}, False, stats

    try:
        with open(bundle_map_file, 'r', encoding='utf-8') as f:
            raw_map = json.load(f)
    except FileNotFoundError:
        return {}, False, stats
    except json.JSONDecodeError as e:
        _bundle_map_warn(logger, f"bundle 映射文件格式错误，忽略本次加载: {e}")
        return {}, False, stats

    if not isinstance(raw_map, dict):
        _bundle_map_warn(logger, "bundle 映射文件根节点不是对象，忽略本次加载")
        return {}, False, stats

    now_ts = int(time.time())
    normalized = {}
    changed = False
    stats['total'] = len(raw_map)

    for click_id, entry in raw_map.items():
        if not isinstance(click_id, str) or not click_id:
            stats['skipped_invalid'] += 1
            changed = True
            _bundle_map_warn(logger, f"跳过无效 click_id: {click_id}")
            continue

        if isinstance(entry, str):
            if not entry:
                stats['skipped_invalid'] += 1
                changed = True
                _bundle_map_warn(logger, f"跳过空 bundle 记录: {click_id}")
                continue
            normalized[click_id] = {'bundle': entry, 'timestamp': now_ts}
            stats['migrated'] += 1
            changed = True
            continue

        if isinstance(entry, dict):
            bundle = entry.get('bundle')
            if not isinstance(bundle, str) or not bundle:
                stats['skipped_invalid'] += 1
                changed = True
                _bundle_map_warn(logger, f"跳过缺少有效 bundle 的记录: {click_id}")
                continue

            timestamp = _parse_bundle_timestamp(entry.get('timestamp'))
            if timestamp is None:
                timestamp = now_ts
                stats['timestamp_fixed'] += 1
                changed = True

            normalized_entry = {'bundle': bundle, 'timestamp': timestamp}
            normalized[click_id] = normalized_entry
            if entry != normalized_entry:
                changed = True
            continue

        stats['skipped_invalid'] += 1
        changed = True
        _bundle_map_warn(logger, f"跳过无效 bundle map 记录: {click_id}")

    return normalized, changed, stats


def save_bundle_map(bundle_map_file: str, bundle_map: Dict[str, Dict[str, Any]], logger: Optional[logging.Logger] = None) -> bool:
    """保存标准格式的 bundle map。"""
    if not bundle_map_file:
        return False
    try:
        with open(bundle_map_file, 'w', encoding='utf-8') as f:
            json.dump(bundle_map, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        _bundle_map_warn(logger, f"保存 bundle 映射失败: {e}")
        return False


def get_bundle_from_map_entry(entry: Any) -> Optional[str]:
    """兼容旧/新格式，提取 bundle 字符串。"""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        bundle = entry.get('bundle')
        return bundle if isinstance(bundle, str) else None
    return None


def update_bundle_map_entry(
    bundle_map: Dict[str, Dict[str, Any]],
    click_id: str,
    referrer_package: str,
    logger: Optional[logging.Logger] = None
) -> Tuple[bool, bool]:
    """
    新增或刷新 click_id 的 timestamp。

    Returns:
        (changed, is_new)
    """
    now_ts = int(time.time())
    entry = bundle_map.get(click_id)
    if entry is None:
        bundle_map[click_id] = {'bundle': referrer_package, 'timestamp': now_ts}
        return True, True

    existing_bundle = get_bundle_from_map_entry(entry)
    if existing_bundle and existing_bundle != referrer_package:
        _bundle_map_warn(logger, f"click_id {click_id} 的 bundle 不一致，保留旧值: {existing_bundle}, 本次: {referrer_package}")

    bundle = existing_bundle or referrer_package
    old_entry = entry.copy() if isinstance(entry, dict) else entry
    bundle_map[click_id] = {'bundle': bundle, 'timestamp': now_ts}
    return bundle_map[click_id] != old_entry, False


def cleanup_loaded_bundle_map(
    bundle_map: Dict[str, Dict[str, Any]],
    retention_days: int,
    load_stats: Dict[str, int]
) -> Dict[str, int]:
    """对已加载到内存的 bundle map 执行可选清理。"""
    deleted_count = 0

    if retention_days >= 0:
        cutoff_ts = int(time.time()) - retention_days * 86400
        expired_click_ids = [
            click_id
            for click_id, entry in bundle_map.items()
            if _parse_bundle_timestamp(entry.get('timestamp')) is not None
            and int(entry['timestamp']) < cutoff_ts
        ]
        for click_id in expired_click_ids:
            del bundle_map[click_id]
        deleted_count = len(expired_click_ids)

    return {
        'loaded': load_stats['total'],
        'migrated': load_stats['migrated'],
        'timestamp_fixed': load_stats['timestamp_fixed'],
        'skipped_invalid': load_stats['skipped_invalid'],
        'deleted': deleted_count,
        'remaining': len(bundle_map),
        'retention_days': retention_days,
        'cleanup_enabled': 1 if retention_days >= 0 else 0,
        'changed': 1 if deleted_count > 0 else 0
    }


def process_log_file_incremental(
    file_path: str,
    output_file: str,
    pixelid_token_cnt_file: Optional[str] = None,
    start_position: int = 0,
    bundle_map_file: str = None,
    click_id_bundle_map: Optional[Dict[str, Dict[str, Any]]] = None,
    bundle_map_changed: bool = False,
    bundle_map_load_stats: Optional[Dict[str, int]] = None,
    save_bundle_map_on_change: bool = True
) -> Dict[str, Any]:
    """
    增量处理日志文件，从指定位置开始

    Args:
        file_path: 日志文件路径
        output_file: 输出文件路径
        pixelid_token_cnt_file: pixelid_token_cnt.txt 文件路径
        start_position: 开始处理的文件字节位置
        bundle_map_file: click_id -> bundle 映射文件路径
        click_id_bundle_map: 已加载到内存的 click_id -> bundle 映射
        bundle_map_changed: 传入映射在调用前是否已有变更
        bundle_map_load_stats: 传入映射对应的加载统计
        save_bundle_map_on_change: 映射变更后是否由本函数写回文件

    Returns:
        处理结果字典，包含统计信息和新的文件位置
    """
    pixelid_set = set()
    if pixelid_token_cnt_file:
        pixelid_set = load_pixelid_set(pixelid_token_cnt_file)

    # 用于 click_id 去重
    click_id_set = set()

    # 加载已有的 click_id -> bundle 映射，并兼容迁移旧格式
    if click_id_bundle_map is None:
        click_id_bundle_map, bundle_map_changed, bundle_map_load_stats = load_bundle_map(bundle_map_file)
    if bundle_map_load_stats is None:
        bundle_map_load_stats = {'migrated': 0, 'timestamp_fixed': 0, 'skipped_invalid': 0}

    stats = {
        'total_log_count': 0,
        'filtered_count': 0,
        'format_new_count': 0,  # 新格式（直接JSON）
        'format_old_count': 0,  # 旧格式（URL编码）
        'url_count': 0,
        'duplicate_click_id_count': 0,
        'url_after_dedup': 0,
        'matched_url_count': 0,
        'bundle_found_count': 0,  # 找到 bundle 的数量
        'bundle_timestamp_updated_count': 0,
        'bundle_map_migrated_count': bundle_map_load_stats['migrated'],
        'bundle_map_timestamp_fixed_count': bundle_map_load_stats['timestamp_fixed'],
        'bundle_map_invalid_count': bundle_map_load_stats['skipped_invalid'],
        'end_position': start_position,
        'processed_bytes': 0
    }

    urls_written = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # 移动到起始位置
            f.seek(start_position)

            with open(output_file, 'a', encoding='utf-8') as out_f:
                # referrer_package 和 URLs 通常在不同日志条目中：
                # type 3/4 有 referrer_package 但无 URLs，type 2/新格式有 URLs 但无 referrer_package
                # 通过跨条目记忆 last_referrer_package 来关联
                last_referrer_package = None
                lines_since_referrer = 0

                for line in f:
                    request_body_str = extract_request_body(line)

                    if request_body_str is None:
                        continue

                    stats['total_log_count'] += 1

                    # 解析 JSON 数据（支持两种格式）
                    json_data = parse_json_data(request_body_str)
                    if json_data is None:
                        continue

                    stats['filtered_count'] += 1

                    # 统计格式类型
                    if 'data' in json_data:
                        if isinstance(json_data['data'], dict):
                            stats['format_new_count'] += 1  # 新格式
                        elif isinstance(json_data['data'], str):
                            stats['format_old_count'] += 1  # 旧格式

                    # 提取 referrer_package（bundle）
                    referrer_package = extract_referrer_package(json_data)

                    # 跨日志条目关联 referrer_package
                    if referrer_package:
                        last_referrer_package = referrer_package
                        lines_since_referrer = 0
                    else:
                        lines_since_referrer += 1
                        # 10条 postshow 日志内复用最近的 referrer_package
                        if last_referrer_package and lines_since_referrer <= 10:
                            referrer_package = last_referrer_package

                    # 提取 URLs（支持两种格式）
                    urls = extract_urls_from_data(json_data)
                    if not urls:
                        continue

                    for url in urls:
                        if not isinstance(url, str):
                            continue
                        if any(d in url for d in BLOCKED_DOMAINS):
                            continue
                        url = url.strip().rstrip('"')
                        if "click_id" not in url or "pixel_id" not in url:
                            continue
                        stats['url_count'] += 1
                        try:
                            pixel_id, click_id = parse_url_pixel_id(url)
                            if click_id and click_id in click_id_set:
                                stats['duplicate_click_id_count'] += 1
                                continue
                            if click_id:
                                click_id_set.add(click_id)
                                # 保存 click_id -> bundle 映射，并刷新命中记录的 timestamp
                                if referrer_package:
                                    changed, is_new = update_bundle_map_entry(click_id_bundle_map, click_id, referrer_package)
                                    bundle_map_changed = bundle_map_changed or changed
                                    if is_new:
                                        stats['bundle_found_count'] += 1
                                    elif changed:
                                        stats['bundle_timestamp_updated_count'] += 1
                            stats['url_after_dedup'] += 1
                            should_write = not pixelid_set or (pixel_id and pixel_id in pixelid_set)
                            if should_write:
                                out_f.write(url + '\n')
                                out_f.flush()
                                urls_written.append(url)
                                stats['matched_url_count'] += 1
                        except Exception as e:
                            print(f"警告: URL 解析失败: {e}", file=sys.stderr)

                # 记录当前文件位置
                stats['end_position'] = f.tell()
                stats['processed_bytes'] = stats['end_position'] - start_position

        # 保存 click_id -> bundle 映射
        if bundle_map_file and bundle_map_changed and save_bundle_map_on_change:
            save_bundle_map(bundle_map_file, click_id_bundle_map)

        stats['bundle_map_changed'] = 1 if bundle_map_changed else 0
        return stats

    except FileNotFoundError:
        print(f"错误: 文件 '{file_path}' 不存在", file=sys.stderr)
        raise
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        raise



def _load_json_state(state_file: str, default: dict) -> dict:
    """加载 JSON 状态文件"""
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def load_daily_counts(state_file: str, target_date: str = None) -> Dict[str, int]:
    """加载当天 pixel_id 计数，日期不匹配则返回空"""
    today = target_date or datetime.now().strftime('%Y-%m-%d')
    state = _load_json_state(state_file, {'date': '', 'pixel_id_counts': {}})
    saved_date, counts = state.get('date', ''), state.get('pixel_id_counts', {})
    if saved_date == today:
        print(f"加载状态: 日期匹配 ({saved_date})，已有 {len(counts)} 个pixel_id")
        return counts
    print(f"加载状态: 日期不匹配 (状态:{saved_date}, 当前:{today})，重置")
    return {}


def save_daily_counts(state_file: str, counts: Dict[str, int], target_date: str = None) -> None:
    """保存 pixel_id 计数"""
    today = target_date or datetime.now().strftime('%Y-%m-%d')
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump({'date': today, 'pixel_id_counts': counts}, f, indent=2, ensure_ascii=False)
        print(f"保存状态: 日期={today}, {len(counts)}个pixel_id")
    except Exception as e:
        raise RuntimeError(f"保存状态失败: {e}")


def should_process_url(url: str, ratio: float) -> bool:
    """
    基于URL的哈希值确定性地判断是否应该处理这个URL

    Args:
        url: URL字符串
        ratio: 处理比例（0-1）

    Returns:
        True 表示应该处理，False 表示跳过
    """
    # 使用 MD5 哈希URL，获得一个 0-1 之间的值
    hash_val = int(hashlib.md5(url.encode()).hexdigest(), 16)
    threshold = hash_val / (2**128)  # 归一化到 0-1

    return threshold < ratio


def load_pixel_id_max_counts(pixelid_token_cnt_file: str, cnt_rate: float, default_max: int) -> Dict[str, int]:
    """从 pixelid_token_cnt.txt 加载每个 pixel_id 的最大转化数"""
    result = {}
    for pixelid, _, cnt_opt in _iter_pixelid_token_rows(pixelid_token_cnt_file):
        if cnt_opt:
            try:
                result[pixelid] = int(int(cnt_opt.replace(',', '')) * cnt_rate)
            except ValueError:
                pass
    if result:
        print(f"从 {pixelid_token_cnt_file} 加载了 {len(result)} 个 pixel_id 最大值")
    return result


def parse_url_pixel_id(url: str) -> Tuple[str, str]:
    """
    解析URL，提取pixel_id和click_id
    注意：pixel_id只保留数字部分，自动截断非数字字符

    Args:
        url: URL字符串

    Returns:
        (pixel_id, click_id) 元组，如果解析失败返回 (None, None)
    """
    try:
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        pixel_id = None
        if 'pixel_id' in query_params:
            pixel_id_list = query_params['pixel_id']
            if pixel_id_list:
                raw_pixel_id = pixel_id_list[0]
                # 只提取开头的数字部分，截断后续的非数字字符
                match = re.match(r'^(\d+)', raw_pixel_id)
                if match:
                    pixel_id = match.group(1)

        click_id = None
        if 'click_id' in query_params:
            click_id_list = query_params['click_id']
            if click_id_list:
                click_id = click_id_list[0]

        return (pixel_id, click_id)
    except Exception:
        return (None, None)


def apply_frequency_control(
    input_file: str,
    output_file: str,
    state_file: str,
    max_per_pixel_id: int = 10,
    total_ratio: float = 1.0,
    target_date: str = None,
    pixelid_token_cnt_file: str = None,
    cnt_rate: float = 1.0,
    bundle_ratio: Dict[str, float] = None,
    bundle_map_file: str = None,
    click_id_bundle_map: Optional[Dict[str, Dict[str, Any]]] = None,
    save_bundle_map_on_change: bool = True
) -> Dict[str, any]:
    """
    应用频率控制规则：每个pixel_id每天最多处理指定数量的URL，然后应用总体比例限制

    注意：本函数会预先计数，实际成功转化后convert_enhanced.py会自动纠正计数

    Args:
        input_file: 输入文件路径（包含所有候选URL）
        output_file: 输出文件路径（过滤后的URL）
        state_file: 状态文件路径（保存每日pixel_id计数）
        max_per_pixel_id: 每个pixel_id每天最大处理数（默认10）
        total_ratio: 总体处理比例（0-1，默认1.0即100%）
        target_date: 目标日期（格式：YYYY-MM-DD），如果为None则使用当前日期
        pixelid_token_cnt_file: pixelid_token_cnt.txt 文件路径
        cnt_rate: 转化率系数（默认1.0）
        bundle_ratio: bundle -> ratio 映射字典
        bundle_map_file: click_id -> bundle 映射文件路径
        click_id_bundle_map: 已加载到内存的 click_id -> bundle 映射
        save_bundle_map_on_change: 映射格式迁移后是否由本函数写回文件

    Returns:
        统计信息字典
    """
    # 加载每个pixel_id的自定义最大值
    pixel_id_max_counts = {}
    if pixelid_token_cnt_file:
        pixel_id_max_counts = load_pixel_id_max_counts(
            pixelid_token_cnt_file,
            cnt_rate,
            max_per_pixel_id
        )

    # 加载 click_id -> bundle 映射，并兼容迁移旧格式
    if click_id_bundle_map is None:
        click_id_bundle_map, bundle_map_changed, _ = load_bundle_map(bundle_map_file)
        if bundle_map_changed and save_bundle_map_on_change:
            save_bundle_map(bundle_map_file, click_id_bundle_map)

    # 加载当天的pixel_id计数
    pixel_id_counts = load_daily_counts(state_file, target_date)

    # 读取所有URL
    urls = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    urls.append(line)
    except FileNotFoundError:
        print(f"错误: 输入文件 '{input_file}' 不存在", file=sys.stderr)
        return {
            'total_input': 0,
            'total_output': 0,
            'skipped_by_limit': 0
        }

    total_input = len(urls)

    print(f"输入URL总数: {total_input}")
    print(f"总体比例限制: {total_ratio*100:.2f}%")
    print(f"每个pixel_id每天限制: {max_per_pixel_id} 个")
    if bundle_ratio:
        print(f"Bundle 差异化比例: {bundle_ratio}")

    # 步骤1: 先应用频率限制（过滤掉已达上限的 pixel_id），确保比例筛选的池子可转化
    print(f"\n步骤1: 应用频率限制...")
    pixel_id_groups = defaultdict(list)
    urls_without_pixel_id = []
    skipped_by_limit = 0

    for url in urls:
        pixel_id, click_id = parse_url_pixel_id(url)
        if pixel_id:
            pixel_id_groups[pixel_id].append((url, click_id))
        else:
            urls_without_pixel_id.append((url, None))

    eligible_urls = []  # 通过频率限制的 URL
    for pixel_id, url_list in pixel_id_groups.items():
        current_count = pixel_id_counts.get(pixel_id, 0)
        pixel_max = pixel_id_max_counts.get(pixel_id, max_per_pixel_id)
        remaining = pixel_max - current_count

        if remaining <= 0:
            skipped_by_limit += len(url_list)
            print(f"pixel_id {pixel_id}: 今日已达上限({current_count}/{pixel_max})，跳过 {len(url_list)} 个URL")
            continue

        if len(url_list) > remaining:
            url_list_sorted = sorted(url_list, key=lambda x: hashlib.md5(x[0].encode()).hexdigest())
            selected = url_list_sorted[:remaining]
            skipped_by_limit += len(url_list) - remaining
            print(f"pixel_id {pixel_id}: 已处理{current_count}个(最大{pixel_max})，从{len(url_list)}个中选{remaining}个，跳过{len(url_list) - remaining}个")
        else:
            selected = url_list
            print(f"pixel_id {pixel_id}: 已处理{current_count}个(最大{pixel_max})，{len(url_list)}个全部通过")
        eligible_urls.extend(selected)

    eligible_urls.extend(urls_without_pixel_id)
    if urls_without_pixel_id:
        print(f"没有pixel_id的URL: {len(urls_without_pixel_id)} 个（全部保留）")
    print(f"频率过滤后可选URL数: {len(eligible_urls)}")

    # 步骤2: 按 bundle 分组，应用不同的比例限制
    print(f"\n步骤2: 应用 bundle 差异化比例限制...")
    bundle_groups = defaultdict(list)
    for url, click_id in eligible_urls:
        bundle = get_bundle_from_map_entry(click_id_bundle_map.get(click_id)) if click_id else None
        bundle_groups[bundle].append((url, click_id))

    final_urls = []
    skipped_by_ratio = 0
    bundle_stats = {}
    # 跨 bundle 累加小数部分，避免小分组全部 round 到 0
    fractional_acc = 0.0

    for bundle, url_list in bundle_groups.items():
        # 确定该 bundle 的比例
        if bundle and bundle_ratio and bundle in bundle_ratio:
            ratio = bundle_ratio[bundle]
            print(f"Bundle '{bundle}': 使用专属比例 {ratio*100:.2f}%，共 {len(url_list)} 个可用URL")
        else:
            ratio = total_ratio
            bundle_name = bundle if bundle else '(无bundle)'
            print(f"Bundle '{bundle_name}': 使用默认比例 {ratio*100:.2f}%，共 {len(url_list)} 个可用URL")

        # 累加精确目标值，取整数部分作为本组目标，小数部分留给下一组
        fractional_acc += len(url_list) * ratio
        target_count = int(fractional_acc)
        fractional_acc -= target_count

        # 实际可选的只有 url_list 中的 URL
        if target_count > 0 and len(url_list) > 0:
            # 按 URL 哈希排序，确定性选取
            url_list_sorted = sorted(url_list, key=lambda x: hashlib.md5(x[0].encode()).hexdigest())
            selected_count = min(target_count, len(url_list))
            selected = url_list_sorted[:selected_count]
            skipped = len(url_list) - selected_count
            final_urls.extend(selected)
            skipped_by_ratio += skipped

            bundle_stats[bundle if bundle else '(无bundle)'] = {
                'available': len(url_list),
                'target': target_count,
                'selected': selected_count,
                'skipped': skipped,
                'ratio': ratio
            }
            print(f"  可用 {len(url_list)} 个，目标 {target_count} 个（{len(url_list)}×{ratio*100:.0f}%），实际选取 {selected_count} 个，跳过 {skipped} 个")
        else:
            skipped_by_ratio += len(url_list)
            bundle_stats[bundle if bundle else '(无bundle)'] = {
                'available': len(url_list),
                'target': 0,
                'selected': 0,
                'skipped': len(url_list),
                'ratio': ratio
            }
            print(f"  可用 {len(url_list)} 个，目标 0 个，全部跳过")

    print(f"\n最终输出URL数: {len(final_urls)}")
    print(f"最终转化率: {len(final_urls)/total_input*100:.2f}%\" if total_input > 0 else \"最终转化率: 0.00%")
    print(f"因频率限制跳过: {skipped_by_limit}")
    print(f"因比例限制跳过: {skipped_by_ratio}")

    # 根据实际写入的URL数量增加计数（按pixel_id分组统计）
    final_pixel_id_counts = defaultdict(int)
    for url, click_id in final_urls:
        pixel_id, _ = parse_url_pixel_id(url)
        if pixel_id:
            final_pixel_id_counts[pixel_id] += 1

    # 更新pixel_id_counts
    for pixel_id, count in final_pixel_id_counts.items():
        current_count = pixel_id_counts.get(pixel_id, 0)
        pixel_id_counts[pixel_id] = current_count + count
        print(f"pixel_id {pixel_id}: 实际增加计数 {count}，总计数 {pixel_id_counts[pixel_id]}")

    # 写入输出文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for url, _ in final_urls:
                f.write(url + '\n')
    except Exception as e:
        print(f"错误: 写入输出文件失败: {e}", file=sys.stderr)
        return {
            'total_input': total_input,
            'urls_after_frequency': 0,
            'total_output': 0,
            'skipped_by_limit': 0,
            'skipped_by_ratio': 0
        }

    # 保存更新后的计数
    save_daily_counts(state_file, pixel_id_counts, target_date)

    stats = {
        'total_input': total_input,
        'urls_after_ratio': len(final_urls),
        'total_output': len(final_urls),
        'skipped_by_limit': skipped_by_limit,
        'skipped_by_ratio': skipped_by_ratio,
        'bundle_stats': bundle_stats
    }

    return stats



def load_frequency_state(state_file: str) -> Dict[str, any]:
    """加载 frequency_state.json"""
    return _load_json_state(state_file, {'date': datetime.now().strftime('%Y-%m-%d'), 'pixel_id_counts': {}})


def save_frequency_state(state_file: str, state: Dict[str, any]) -> None:
    """保存 frequency_state.json"""
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"警告: 保存状态失败: {e}", file=sys.stderr)


def decrement_pixel_count(state_file: str, pixelid: str, count: int, logger: logging.Logger) -> None:
    state = load_frequency_state(state_file)
    pixel_id_counts = state.get('pixel_id_counts', {})

    if pixelid in pixel_id_counts:
        old_count = pixel_id_counts[pixelid]
        new_count = max(0, old_count - count)
        pixel_id_counts[pixelid] = new_count
        state['pixel_id_counts'] = pixel_id_counts
        save_frequency_state(state_file, state)
        logger.info(f"已从frequency_state扣除 pixelid '{pixelid}' 的计数: {old_count} -> {new_count} (扣除{count})")
    else:
        logger.debug(f"pixel_id '{pixelid}' 在frequency_state中不存在，无需扣除")


def _setup_logger(name: str, log_file: str) -> logging.Logger:
    """配置 logger：文件+控制台"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    for h in (logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()):
        h.setLevel(logging.INFO)
        h.setFormatter(fmt)
        logger.addHandler(h)
    return logger


def load_pixelid_token_mapping(file_path: str, logger: logging.Logger) -> Dict[str, str]:
    """从 pixelid_token_cnt.txt 构建 pixelid->token 映射"""
    m = {r[0]: r[1] for r in _iter_pixelid_token_rows(file_path)}
    if not m:
        logger.error(f"文件 '{file_path}' 不存在或为空")
        sys.exit(1)
    logger.info(f"加载 {len(m)} 条 pixelid-token 映射")
    return m


def save_pixelid_token_mapping(file_path: str, pixelid_token_map: Dict[str, str], logger: logging.Logger) -> bool:
    """记录映射变更（仅日志，不修改源文件）"""
    logger.info(f"当前 {len(pixelid_token_map)} 条映射，不修改源文件 {file_path}")
    return True


def _extract_origin_from_url(url: str) -> Tuple[str, str]:
    """从完整 URL 提取 origin 和 referer（基于域名）"""
    try:
        parsed = urllib.parse.urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return (base, base + '/')
    except Exception:
        return ('https://wuuou88.com', 'https://wuuou88.com/')


def parse_clicks_file(file_path: str, logger: logging.Logger) -> list:
    """解析 clicks.txt，返回 [(pixelid, click_id, current_href), ...]，current_href 为完整 URL"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
    except (FileNotFoundError, Exception) as e:
        logger.error(f"读取 '{file_path}' 失败: {e}")
        sys.exit(1)
    result = []
    for line_num, line in enumerate(lines, 1):
        pixelid, click_id = parse_url_pixel_id(line)
        if pixelid and click_id:
            # 清理 +deepLink: 后缀及之后的内容
            current_href = line.split('+deepLink:')[0] if '+deepLink:' in line else line
            result.append((pixelid, urllib.parse.unquote(click_id), current_href))
        else:
            logger.warning(f"第 {line_num} 行缺少参数，跳过")
    logger.info(f"解析 {len(result)} 条 clicks")
    return result


def get_value_by_probability() -> int:
    """按概率返回 value：20%→5, 30%→10, 20%→20, 10%→30, 10%→40, 5%→50, 5%→100"""
    r = random.random() * 100
    for threshold, val in VALUE_PROBS:
        if r < threshold:
            return val
    return 100


def build_url(pixelid: str, click_id: str, token: str, current_href: str = None) -> List[Any]:
    """拼接 URL：第一个必为 REGISTRATION，50% 概率追加 PURCHASE。
    token 为 'null' 时返回 POST 请求 spec（需 current_href）。"""
    if token == 'null':
        if not current_href:
            return []
        origin, referer = _extract_origin_from_url(current_href)
        parsed = urllib.parse.urlparse(current_href)
        host = parsed.netloc or 'example.com'
        event_id = f"eventId-{int(time.time()*1000)}-{random.randint(1000000000000, 9999999999999)}-{pixelid}"
        session_id = f"sessionId-{int(time.time()*1000)}-{random.randint(1000000000000, 9999999999999)}-{pixelid}"
        uuid_hex = hashlib.md5(f"{pixelid}{click_id}{time.time()}".encode()).hexdigest()
        # 生成随机 UA（与 curl 请求保持一致）
        ua, sec_ch_ua, android_ver = _generate_random_android_ua()
        kwai_info = {
            "uuid": uuid_hex,
            "currentHref": current_href,
            "accessMode": 0,
            "host": host,
            "navigator": ua,
            "eventId": event_id,
            "tirdParty": "none",
            "kwaiAdInfoSource": "url",
            "referrer": "",
            "inIframe": False,
            "isGtm": False,
            "staticHost": "s1.kwai.net",
            "displayMode": "browser",
            "iosStandalone": False,
        }
        # 基础 spec 字段（共享 UA 和 session）
        base_spec = {
            "type": "null_token",
            "url": NULL_TOKEN_API_URL,
            "origin": origin,
            "referer": referer,
            "ua": ua,
            "sec_ch_ua": sec_ch_ua,
            "android_ver": android_ver,
        }
        # REGISTRATION 请求
        pixel_ext_reg = {
            "kwaiInfo": kwai_info,
            "pixelIds": pixelid,
            "sessionId": session_id,
            "sendMethod": 1,
            "sendWithXhrAsync": False,
        }
        body_reg = {
            "clickid": click_id,
            "event_name": "EVENT_COMPLETE_REGISTRATION",
            "is_attributed": 0,
            "mmpcode": "PL",
            "pixelId": pixelid,
            "pixelSdkVersion": "2.11.1",
            "testFlag": False,
            "trackFlag": False,
            "pixelExtData": json.dumps(pixel_ext_reg, separators=(',', ':')),
        }
        result = [{**base_spec, "body": body_reg}]
        # 50% 概率追加 PURCHASE 请求
        if random.random() < 0.5:
            pixel_ext_pur = {
                "kwaiInfo": kwai_info,
                "pixelIds": pixelid,
                "sessionId": session_id,
                "sendMethod": 1,
                "sendWithXhrAsync": False,
                "currency": "BRL",
                "value": get_value_by_probability(),
            }
            body_pur = {
                "clickid": click_id,
                "event_name": "EVENT_PURCHASE",
                "is_attributed": 0,
                "mmpcode": "PL",
                "pixelId": pixelid,
                "pixelSdkVersion": "2.11.1",
                "testFlag": False,
                "trackFlag": False,
                "pixelExtData": json.dumps(pixel_ext_pur, separators=(',', ':')),
            }
            result.append({**base_spec, "body": body_pur, "is_purchase": True})
        return result
    base = "https://www.adsnebula.com/log/common/gapi?access_token={t}&pixelId={p}&clickid={c}&mmpcode=PL&pixelSdkVersion=9.9.9&is_attributed=1&testFlag=false&trackFlag=false"
    url1 = base.format(t=token, p=pixelid, c=click_id) + "&event_name=EVENT_COMPLETE_REGISTRATION"
    urls = [url1]
    if random.random() < 0.5:
        urls.append(base.format(t=token, p=pixelid, c=click_id) + f"&event_name=EVENT_PURCHASE&currency=BRL&value={get_value_by_probability()}")
    return urls


def _build_curl_cmd(url_or_spec, session_id: str, token_null: bool = False) -> list:
    """构建 curl 命令。token_null 时 url_or_spec 为 dict，否则为 URL 字符串"""
    proxy_user = f'client-liuxiaoyu_area-BR_session-{session_id}:asdfasdaili112'
    proxy_arg = f'{proxy_user}@proxy.iproyal.net:9000'
    base = ['curl', '-x', proxy_arg, '-s', '-w', '\nHTTP_CODE:%{http_code}']

    if token_null and isinstance(url_or_spec, dict):
        spec = url_or_spec
        url = spec['url']
        origin, referer = spec['origin'], spec['referer']
        body_str = json.dumps(spec['body'], separators=(',', ':'))
        # 使用 build_url 生成的 UA（保证 body 和请求头一致）
        headers = dict(NULL_TOKEN_HEADERS)
        headers['origin'] = origin
        headers['referer'] = referer
        headers['user-agent'] = spec['ua']
        headers['sec-ch-ua'] = spec['sec_ch_ua']
        args = base + [url]
        for k, v in headers.items():
            args.extend(['-H', f'{k}: {v}'])
        args.extend(['--data-raw', body_str])
        return args

    return base + [url_or_spec]


def curl_request(url_or_spec, logger: logging.Logger, session_id: str, url_idx: int = None, total_urls: int = None, token_null: bool = False) -> tuple:
    """使用 curl 访问 URL 或执行 POST 请求。token_null 时 url_or_spec 为 dict"""
    try:
        curl_cmd = _build_curl_cmd(url_or_spec, session_id, token_null)
        curl_cmd_str = ' '.join(shlex.quote(arg) for arg in curl_cmd)

        # 打印合并后的日志
        if url_idx is not None and total_urls is not None:
            logger.info(f"发送请求 {url_idx}/{total_urls}: {curl_cmd_str}")
        else:
            logger.info(f"执行curl命令: {curl_cmd_str}")

        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout
        http_code = None

        if 'HTTP_CODE:' in output:
            parts = output.rsplit('HTTP_CODE:', 1)
            if len(parts) == 2:
                output = parts[0].strip()
                try:
                    http_code = int(parts[1].strip())
                except ValueError:
                    pass

        success = result.returncode == 0 and (http_code is None or 200 <= http_code < 300)

        return (success, output, http_code)

    except subprocess.TimeoutExpired:
        logger.warning("请求超时")
        return (False, "请求超时", None)
    except Exception as e:
        logger.error(f"请求失败: {str(e)}")
        return (False, f"请求失败: {str(e)}", None)


def _load_pending_curls(pending_file: str) -> List[Dict[str, str]]:
    """加载待执行的 curl 列表"""
    try:
        with open(pending_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('items', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_pending_curls(pending_file: str, items: List[Dict[str, str]]) -> None:
    """保存待执行的 curl 列表"""
    with open(pending_file, 'w', encoding='utf-8') as f:
        json.dump({'items': items, 'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, f, indent=2)


def execute_pending_curls(pending_file: str, logger: logging.Logger, sleep_seconds: int = 5, purchase_log_file: str = None) -> int:
    """执行上次保存的 50% 概率产生的 curl/spec（session_id 保持），返回成功数。
    每执行完一项立即从文件移除，避免崩溃后重复执行。执行前写入 purchase.log。"""
    items = _load_pending_curls(pending_file)
    if not items:
        return 0
    logger.info(f"执行 {len(items)} 个待处理的 PURCHASE 请求（上次 50% 概率产生）")
    success_count = 0
    for i, item in enumerate(items):
        session_id = item.get('session_id')
        token_null = item.get('token_null', False)
        # 支持 dict spec（null_token）或字符串 URL
        if token_null:
            spec = item.get('spec')
            if not spec or not session_id:
                logger.warning(f"跳过无效 pending 项: {item}")
                _save_pending_curls(pending_file, items[i + 1:])
                continue
            _log_purchase_curl(purchase_log_file, spec, session_id)
            curl_cmd_str = ' '.join(shlex.quote(a) for a in _build_curl_cmd(spec, session_id, token_null=True))
            logger.info(f"执行 pending null_token {i + 1}/{len(items)}: {curl_cmd_str[:200]}...")
            success, response, http_code = curl_request(spec, logger, session_id, token_null=True)
        else:
            url = item.get('url')
            if not url or not session_id:
                logger.warning(f"跳过无效 pending 项: {item}")
                _save_pending_curls(pending_file, items[i + 1:])
                continue
            _log_purchase_curl(purchase_log_file, url, session_id)
            curl_cmd_str = ' '.join(shlex.quote(a) for a in _build_curl_cmd(url, session_id))
            logger.info(f"执行 pending {i + 1}/{len(items)}: {curl_cmd_str}")
            success, response, http_code = curl_request(url, logger, session_id)
        if success:
            success_count += 1
            logger.info(f"pending 请求成功 - HTTP {http_code}")
        else:
            logger.error(f"pending 请求失败 - {response}")
        _save_pending_curls(pending_file, items[i + 1:])  # 已执行项从文件移除，防崩溃重复
        if i + 1 < len(items):
            time.sleep(sleep_seconds)
    return success_count


def _log_purchase_curl(purchase_log_file: str, url_or_spec, session_id: str) -> None:
    """将 PURCHASE curl 命令追加到 purchase.log"""
    if not purchase_log_file:
        return
    try:
        token_null = isinstance(url_or_spec, dict)
        curl_args = _build_curl_cmd(url_or_spec, session_id, token_null=token_null)
        curl_cmd_str = ' '.join(shlex.quote(a) for a in curl_args)
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S') + f',{datetime.now().microsecond//1000:03d}'
        with open(purchase_log_file, 'a', encoding='utf-8') as f:
            f.write(f"{ts} - INFO - PURCHASE: {curl_cmd_str}\n")
    except Exception:
        pass


def save_pending_curl(pending_file: str, url_or_spec, session_id: str, pixelid: str, purchase_log_file: str = None) -> None:
    """将 50% 概率产生的 PURCHASE curl/spec 追加到待执行列表，并写入 purchase.log"""
    items = _load_pending_curls(pending_file)
    # 支持字符串 URL 或 dict spec（null_token 场景）
    if isinstance(url_or_spec, dict):
        item = {'spec': url_or_spec, 'session_id': session_id, 'pixelid': pixelid, 'token_null': True}
    else:
        item = {'url': url_or_spec, 'session_id': session_id, 'pixelid': pixelid, 'token_null': False}
    items.append(item)
    _save_pending_curls(pending_file, items)
    _log_purchase_curl(purchase_log_file, url_or_spec, session_id)


def process_requests(
    pixelid_token_map: Dict[str, str],
    clicks_data: list,
    logger: logging.Logger,
    pixelid_token_cnt_file: str,
    frequency_state_file: str,
    sleep_seconds: int = 5,
    pending_curl_file: str = None,
    purchase_log_file: str = None
) -> Dict[str, int]:
    """处理所有请求"""
    stats = {
        'total': len(clicks_data),
        'success': 0,
        'failed': 0,
        'missing_token': 0,
        'url_count': 0
    }

    for idx, item in enumerate(clicks_data, 1):
        pixelid, click_id = item[0], item[1]
        current_href = item[2] if len(item) >= 3 else None
        session_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(1000, 9999))
        logger.info(f"处理第 {idx}/{len(clicks_data)} 条记录 - pixelid: {pixelid} - session_id: {session_id}")

        token = pixelid_token_map.get(pixelid)
        if token is None:
            logger.warning(f"未找到 pixelid '{pixelid}' 对应的 token，跳过")
            stats['missing_token'] += 1
            if frequency_state_file:
                decrement_pixel_count(frequency_state_file, pixelid, 1, logger)
            continue

        urls = build_url(pixelid, click_id, token, current_href)
        logger.info(f"生成 {len(urls)} 个 URL")
        stats['url_count'] += len(urls)

        for url_idx, url_or_spec in enumerate(urls, 1):
            is_null_token = isinstance(url_or_spec, dict) and url_or_spec.get('type') == 'null_token'
            is_purchase = is_null_token and url_or_spec.get('is_purchase', False)
            # null token 的 PURCHASE 请求或普通 URL 的第二个请求都需要 pending
            if is_purchase or (url_idx == 2 and pending_curl_file and not is_null_token):
                save_pending_curl(pending_curl_file, url_or_spec, session_id, pixelid, purchase_log_file)
                logger.info(f"50% 概率 PURCHASE 已保存，下次 cron 执行（session_id={session_id}）")
                continue
            if is_null_token:
                TEST_MODE = False
                if TEST_MODE:
                    success, response, http_code = True, "test", 200
                else:
                    success, response, http_code = curl_request(url_or_spec, logger, session_id, 1, 1, token_null=True)
            else:
                TEST_MODE = False
                if TEST_MODE:
                    success, response, http_code = True, "test", 200
                    logger.info(f"测试请求成功, url: {url_or_spec} 没有真正发送请求")
                else:
                    success, response, http_code = curl_request(url_or_spec, logger, session_id, url_idx, len(urls))

            if success:
                stats['success'] += 1
                resp_preview = (response or '')[:100]
                logger.info(f"请求成功 - HTTP {http_code} - 响应: {resp_preview}{'...' if len(response or '') > 100 else ''}")

                # 校验响应内容（null_token 接口可能返回不同格式，暂不校验）
                if not is_null_token and response != '{"result":1}':
                    logger.warning(f"响应内容不符合预期 (期望: {{'result':1}}, 实际: {response}), 删除 pixelid '{pixelid}' 的映射关系")
                    if pixelid in pixelid_token_map:
                        del pixelid_token_map[pixelid]
                        save_pixelid_token_mapping(pixelid_token_cnt_file, pixelid_token_map, logger)
                        logger.info(f"已从内存映射中删除 pixelid '{pixelid}'，跳过后续 URL")
                        # 扣除本次click的计数（因为token无效，这个click不应计入限额）
                        # 注意：url_frequency_controller按click条目计数，所以扣除1
                        if frequency_state_file:
                            decrement_pixel_count(frequency_state_file, pixelid, 1, logger)
                        break  # 跳出最里面的循环
            else:
                stats['failed'] += 1
                logger.error(f"请求失败 - {response}")
                # 扣除本次click的计数（因为请求失败，这个click不应计入限额）
                # 注意：url_frequency_controller按click条目计数，所以扣除1
                if frequency_state_file:
                    decrement_pixel_count(frequency_state_file, pixelid, 1, logger)
                break  # 请求失败，跳出URL循环，不再尝试后续URL

            # 如果不是最后一个 URL，休眠
            if url_idx < len(urls):
                time.sleep(sleep_seconds)

        # 如果不是最后一条记录，休眠
        if idx < len(clicks_data):
            time.sleep(sleep_seconds)

    return stats


class Orchestrator:
    """主编排器"""

    def __init__(self, config_file: str = 'orchestrator_config.json', bundle_map_retention_days: Optional[int] = None):
        """初始化"""
        self.config = self.load_config(config_file)
        if bundle_map_retention_days is not None:
            self.config['bundle_map_retention_days'] = bundle_map_retention_days
        self.state_file = self.config.get('state_file', 'orchestrator_state.json')
        self.bundle_map_file = self.config.get('bundle_map_file', 'click_id_bundle_map.json')
        self.logger = self.setup_logging()

    def setup_logging(self) -> logging.Logger:
        """配置日志"""
        return _setup_logger('orchestrator', self.config.get('orchestrator_log', 'orchestrator.log'))

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            'log_dir': '/data/disk0/home/luoxun/logs/springboot-scaffold',
            'log_prefix': 'info.prod0320',
            'enable_increase_info_log': True,
            'increase_log_dir': 'increase_info_log',
            'increase_log_prefix': 'increase_info_log',
            'increase_log_wait_seconds': 5,
            'increase_log_wait_attempts': 3,
            'pixelid_token_cnt_file': 'pixelid_token_cnt.txt',
            'clicks_temp_file': 'clicks_temp.txt',
            'clicks_file': 'clicks.txt',
            'frequency_state_file': 'frequency_state.json',
            'state_file': 'orchestrator_state.json',
            'bundle_map_file': 'click_id_bundle_map.json',
            'orchestrator_log': 'orchestrator.log',
            'convert_log': 'convert_results.log',
            'purchase_log_file': 'purchase.log',
            'pending_curl_file': 'pending_curl.json',
            'total_ratio': 0.04,
            'max_per_pixel_id': 10,
            'cnt_rate': 1.0,
            'sleep_seconds': 5,
            'bundle_ratio': {},
            'bundle_map_retention_days': -1,
            'scripts_dir': os.path.dirname(os.path.abspath(__file__))
        }

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            print(f"警告: 配置文件 '{config_file}' 不存在，使用默认配置", file=sys.stderr)
            return default_config
        except json.JSONDecodeError as e:
            print(f"错误: 配置文件格式错误: {e}，使用默认配置", file=sys.stderr)
            return default_config

    def load_state(self) -> Dict[str, Any]:
        """加载状态"""
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                return state
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'last_log_file': None,
                'last_position': 0,
                'last_run': None
            }

    def get_log_start_position(self, state: Dict[str, Any], log_file: str) -> int:
        """按旧版状态格式读取指定日志文件的起始位置。"""
        log_file_abs = os.path.abspath(log_file)
        last_log_file = state.get('last_log_file')
        if last_log_file:
            last_log_file_abs = os.path.abspath(last_log_file)
            if last_log_file in (log_file, log_file_abs) or last_log_file_abs == log_file_abs:
                try:
                    return int(state.get('last_position', 0))
                except (TypeError, ValueError):
                    return 0
        return 0

    def save_state(self, state: Dict[str, Any]) -> None:
        """保存状态"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"保存状态失败: {e}")

    def resolve_increase_log_dir(self) -> str:
        """解析 increase_info_log 目录；相对路径按 log_dir 下的子目录处理。"""
        increase_log_dir = self.config.get('increase_log_dir', 'increase_info_log')
        if os.path.isabs(increase_log_dir):
            return increase_log_dir
        return os.path.join(self.config['log_dir'], increase_log_dir)

    def parse_log_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """解析日志文件名，兼容 info.prod0320_日期.part_N.log 和 info.prod0320.IP_日期.part_N.log。"""
        log_prefix = re.escape(self.config['log_prefix'])
        pattern = re.compile(
            rf'^{log_prefix}(?:\.(?P<ip>[^_]+))?_(?P<date>\d{{4}}-\d{{2}}-\d{{2}})\.part_(?P<part>\d+)\.log$'
        )
        match = pattern.match(filename)
        if not match:
            return None
        return {
            'date': match.group('date'),
            'part': int(match.group('part')),
            'ip': match.group('ip') or ''
        }

    def parse_increase_log_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """解析 increase_info_log.<ip>.YYYYMMDD.HHMM[.seq] 增量日志文件名。"""
        log_prefix = re.escape(self.config.get('increase_log_prefix', 'increase_info_log'))
        pattern = re.compile(
            rf'^{log_prefix}\.(?P<ip>.+)\.(?P<date>\d{{8}})\.(?P<hour_minute>\d{{4}})(?:\.(?P<seq>\d+))?$'
        )
        match = pattern.match(filename)
        if not match:
            return None
        raw_date = match.group('date')
        return {
            'date': f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}",
            'part': 0,
            'ip': match.group('ip') or '',
            'hour_minute': match.group('hour_minute'),
            'seq': int(match.group('seq') or 0)
        }

    def current_increase_log_stamp(self) -> str:
        """返回当前 5 分钟时间片的 YYYYMMDD.HHMM，例如 15:41 -> 20260615.1540。"""
        now = datetime.now()
        bucket_minute = (now.minute // 5) * 5
        return now.replace(minute=bucket_minute, second=0, microsecond=0).strftime('%Y%m%d.%H%M')

    def find_increase_logs_for_stamp(self, stamp: str) -> List[str]:
        """查找指定 YYYYMMDD.HHMM 时间片的 increase_info_log 文件。"""
        increase_log_dir = self.resolve_increase_log_dir()
        if not os.path.isdir(increase_log_dir):
            return []

        increase_prefix = re.escape(self.config.get('increase_log_prefix', 'increase_info_log'))
        pattern = re.compile(rf'^{increase_prefix}\..*\.{re.escape(stamp)}(?:\.\d+)?$')
        glob_pattern = os.path.join(
            increase_log_dir,
            f"{self.config.get('increase_log_prefix', 'increase_info_log')}.*.{stamp}*"
        )
        return sorted(
            path
            for path in glob.glob(glob_pattern)
            if os.path.isfile(path) and pattern.match(os.path.basename(path))
        )

    def wait_for_current_increase_log(self) -> None:
        """运行前等待当前 5 分钟时间片的 increase_info_log 文件落盘；缺失只记日志不阻断流程。"""
        if not self.config.get('enable_increase_info_log', True):
            return

        stamp = self.current_increase_log_stamp()
        increase_log_dir = self.resolve_increase_log_dir()
        wait_seconds = int(self.config.get('increase_log_wait_seconds', 5))
        wait_attempts = int(self.config.get('increase_log_wait_attempts', 3))

        for attempt in range(wait_attempts + 1):
            matched = self.find_increase_logs_for_stamp(stamp)
            if matched:
                self.logger.info(
                    f"当前 5 分钟时间片 increase_info_log 已存在: stamp={stamp}, "
                    f"files={len(matched)}, first={matched[0]}"
                )
                return

            if attempt < wait_attempts:
                self.logger.warning(
                    f"当前 5 分钟时间片 increase_info_log 尚未生成，等待 {wait_seconds}s 后重试 "
                    f"({attempt + 1}/{wait_attempts}): dir={increase_log_dir}, stamp={stamp}"
                )
                time.sleep(wait_seconds)

        self.logger.warning(
            f"当前 5 分钟时间片 increase_info_log 缺失，已等待 {wait_seconds * wait_attempts}s，"
            f"继续执行后续流程: dir={increase_log_dir}, stamp={stamp}"
        )

    def find_log_files_for_latest_date(self) -> List[Dict[str, Any]]:
        """查找本轮处理文件：最新主日志文件 + 当前 5 分钟时间片增量日志。"""
        log_dir = self.config['log_dir']
        log_prefix = self.config['log_prefix']

        try:
            files = os.listdir(log_dir)
            log_files = []
            main_log_files = []
            for filename in files:
                if not (filename.startswith(log_prefix) and filename.endswith('.log')):
                    continue
                parsed = self.parse_log_filename(filename)
                log_file = os.path.join(log_dir, filename)
                if not os.path.isfile(log_file):
                    continue
                main_log_files.append({
                    'path': log_file,
                    'name': filename,
                    'date': parsed['date'] if parsed else '',
                    'part': parsed['part'] if parsed else 0,
                    'ip': parsed['ip'] if parsed else '',
                    'source': 'info_log',
                    'hour_minute': '',
                    'seq': 0,
                    'mtime': os.path.getmtime(log_file)
                })

            if main_log_files:
                log_files.append(max(main_log_files, key=lambda item: item['mtime']))

            if self.config.get('enable_increase_info_log', True):
                increase_log_dir = self.resolve_increase_log_dir()
                if os.path.isdir(increase_log_dir):
                    increase_stamp = self.current_increase_log_stamp()
                    increase_unmatched_log_files = []
                    for log_file in self.find_increase_logs_for_stamp(increase_stamp):
                        filename = os.path.basename(log_file)
                        parsed = self.parse_increase_log_filename(filename)
                        if not parsed:
                            increase_unmatched_log_files.append(filename)
                            continue
                        log_files.append({
                            'path': log_file,
                            'name': filename,
                            'date': parsed['date'],
                            'part': parsed['part'],
                            'ip': parsed['ip'],
                            'source': 'increase_info_log',
                            'hour_minute': parsed['hour_minute'],
                            'seq': parsed['seq'],
                            'mtime': os.path.getmtime(log_file)
                        })
                    if increase_unmatched_log_files:
                        self.logger.warning(
                            f"跳过 {len(increase_unmatched_log_files)} 个不符合 increase_info_log 格式的日志文件: "
                            + ', '.join(sorted(increase_unmatched_log_files)[:5])
                        )
                else:
                    self.logger.info(f"increase_info_log 目录不存在，跳过: {increase_log_dir}")

            if not log_files:
                raise Exception(f"在目录 {log_dir} 中未找到可解析的日志文件")

            log_files.sort(
                key=lambda item: (
                    0 if item['source'] == 'info_log' else 1,
                    item['hour_minute'],
                    item['ip'],
                    item['seq'],
                    item['name']
                )
            )

            return log_files

        except Exception as e:
            self.logger.error(f"查找日志文件失败: {e}")
            raise

    def run_extract_log(
        self,
        log_file: str,
        start_position: int,
        click_id_bundle_map: Optional[Dict[str, Dict[str, Any]]] = None,
        bundle_map_changed: bool = False,
        bundle_map_load_stats: Optional[Dict[str, int]] = None,
        clear_output: bool = True
    ) -> tuple:
        """运行日志提取，返回 (end_position, extracted_url_count, bundle_map_changed)"""
        self.logger.info("步骤 1: 提取日志数据")

        clicks_temp_file = self.config['clicks_temp_file']
        pixelid_token_cnt_file = self.config['pixelid_token_cnt_file']

        # 清空临时文件
        if clear_output:
            try:
                open(clicks_temp_file, 'w').close()
            except Exception as e:
                self.logger.warning(f"清空临时文件失败: {e}")

        self.logger.info(f"开始处理日志文件: {log_file}")
        self.logger.info(f"开始从位置 {start_position} 处理日志文件...")

        # 直接调用内部函数
        stats = process_log_file_incremental(
            log_file,
            clicks_temp_file,
            pixelid_token_cnt_file,
            start_position,
            self.bundle_map_file,
            click_id_bundle_map,
            bundle_map_changed,
            bundle_map_load_stats,
            False
        )

        end_position, extracted_count = stats['end_position'], stats['matched_url_count']
        for k, v in stats.items():
            self.logger.info(f"  {k}: {v}")
        if stats['url_count'] > 0:
            self.logger.info(f"  去重率: {stats['duplicate_click_id_count']/stats['url_count']*100:.2f}%")
        if stats['url_after_dedup'] > 0:
            self.logger.info(f"  pixel_id覆盖率: {stats['matched_url_count']/stats['url_after_dedup']*100:.2f}%")
        return (end_position, extracted_count, bool(stats.get('bundle_map_changed')))

    def run_frequency_control(
        self,
        click_id_bundle_map: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> int:
        """运行频率控制（应用pixel_id每天x个的限制和总体比例限制），返回过滤后的URL数量"""
        self.logger.info("步骤 2: 应用频率控制和总体比例限制")

        clicks_temp_file = self.config['clicks_temp_file']
        clicks_file = self.config['clicks_file']
        frequency_state_file = self.config['frequency_state_file']
        max_per_pixel_id = self.config.get('max_per_pixel_id', 10)
        total_ratio = self.config.get('total_ratio', 0.04)
        pixelid_token_cnt_file = self.config.get('pixelid_token_cnt_file')
        cnt_rate = self.config.get('cnt_rate', 1.0)
        bundle_ratio = self.config.get('bundle_ratio', {})

        self.logger.info(f"应用频率控制...")
        self.logger.info(f"使用当前日期: {datetime.now().strftime('%Y-%m-%d')}")

        # 直接调用内部函数
        stats = apply_frequency_control(
            clicks_temp_file,
            clicks_file,
            frequency_state_file,
            max_per_pixel_id,
            total_ratio,
            None,  # target_date
            pixelid_token_cnt_file,
            cnt_rate,
            bundle_ratio,
            self.bundle_map_file,
            click_id_bundle_map,
            False
        )

        for k, v in stats.items():
            if k != 'bundle_stats':
                self.logger.info(f"  {k}: {v}")

        # 输出 bundle 统计
        if 'bundle_stats' in stats:
            self.logger.info("  Bundle 统计:")
            for bundle, bundle_stat in stats['bundle_stats'].items():
                self.logger.info(f"    {bundle}: 可选={bundle_stat['available']}, 目标={bundle_stat['target']}, 选取={bundle_stat['selected']}, 跳过={bundle_stat['skipped']}, 比例={bundle_stat['ratio']*100:.2f}%")

        return stats['total_output']

    def run_convert(self) -> int:
        """运行URL转换和请求，返回成功转化的数量"""
        self.logger.info("步骤 3: 执行 curl 请求")

        clicks_file = self.config['clicks_file']
        pixelid_token_cnt_file = self.config['pixelid_token_cnt_file']
        convert_log = self.config['convert_log']
        frequency_state_file = self.config['frequency_state_file']
        sleep_seconds = self.config['sleep_seconds']

        # 检查 clicks.txt 是否为空
        try:
            with open(clicks_file, 'r') as f:
                if not f.read().strip():
                    self.logger.info("clicks.txt 为空，跳过 curl 请求")
                    return 0
        except FileNotFoundError:
            self.logger.info("clicks.txt 不存在，跳过 curl 请求")
            return 0

        logger = _setup_logger('convert', convert_log)

        logger.info("="*80)
        logger.info(f"开始处理 - 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)

        # 加载 pixelid-token 映射
        logger.info("正在加载 pixelid-token 映射...")
        pixelid_token_map = load_pixelid_token_mapping(pixelid_token_cnt_file, logger)

        # 解析 clicks 文件
        logger.info("正在解析 clicks 文件...")
        clicks_data = parse_clicks_file(clicks_file, logger)

        if not clicks_data:
            logger.error("没有找到任何有效的 clicks 数据")
            return 0

        # 处理请求
        logger.info(f"开始处理 {len(clicks_data)} 条记录...")
        stats = process_requests(
            pixelid_token_map,
            clicks_data,
            logger,
            pixelid_token_cnt_file,
            frequency_state_file,
            sleep_seconds,
            self.config.get('pending_curl_file'),
            self.config.get('purchase_log_file')
        )

        for k, v in stats.items():
            logger.info(f"  {k}: {v}")
        if stats['url_count'] > 0:
            logger.info(f"  成功率: {stats['success']/stats['url_count']*100:.2f}%")
        success_count = stats['success']
        self.logger.info(f"成功转化数量: {success_count}")
        return success_count

    def run(self) -> None:
        """执行完整流程"""
        self.logger.info("="*80)
        self.logger.info(f"开始执行编排流程 - 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("="*80)

        try:
            # 迁移 bundle map 格式；retention_days >= 0 时额外清理过期记录
            retention_days = int(self.config.get('bundle_map_retention_days', -1))
            click_id_bundle_map, bundle_map_dirty, bundle_map_load_stats = load_bundle_map(self.bundle_map_file, self.logger)
            cleanup_stats = cleanup_loaded_bundle_map(click_id_bundle_map, retention_days, bundle_map_load_stats)
            bundle_map_dirty = bundle_map_dirty or bool(cleanup_stats['changed'])
            if cleanup_stats['cleanup_enabled']:
                self.logger.info(
                    "bundle map 清理完成: "
                    f"加载={cleanup_stats['loaded']}, 迁移={cleanup_stats['migrated']}, "
                    f"修复时间戳={cleanup_stats['timestamp_fixed']}, 删除={cleanup_stats['deleted']}, "
                    f"保留={cleanup_stats['remaining']}, 保留天数={cleanup_stats['retention_days']}"
                )
            else:
                self.logger.info(
                    "bundle map 清理已跳过: "
                    f"加载={cleanup_stats['loaded']}, 迁移={cleanup_stats['migrated']}, "
                    f"修复时间戳={cleanup_stats['timestamp_fixed']}, 保留={cleanup_stats['remaining']}, "
                    "retention_days=-1"
                )
            if bundle_map_dirty:
                save_bundle_map(self.bundle_map_file, click_id_bundle_map, self.logger)
                bundle_map_dirty = False

            # 步骤 0: 先执行上次 50% 概率产生的 PURCHASE curl（session_id 保持）
            pending_file = self.config.get('pending_curl_file', 'pending_curl.json')
            sleep_seconds = self.config.get('sleep_seconds', 5)
            purchase_log_file = self.config.get('purchase_log_file')
            pending_success = execute_pending_curls(pending_file, self.logger, sleep_seconds, purchase_log_file)
            if pending_success > 0:
                self.logger.info(f"待处理 PURCHASE 执行完成: {pending_success} 个")

            # 加载状态
            state = self.load_state()
            self.logger.info(f"加载状态: {state}")

            # 等待当前时间点的增量日志落盘；缺失时只记录日志，不阻断后续处理。
            self.wait_for_current_increase_log()

            # 查找本轮处理文件
            log_files = self.find_log_files_for_latest_date()
            self.logger.info(
                f"使用日志文件数: {len(log_files)}"
            )
            for log_item in log_files:
                display_ip = log_item['ip'] or '(no ip)'
                self.logger.info(
                    f"  日志文件: {log_item['path']} "
                    f"(source={log_item['source']}, date={log_item['date']}, "
                    f"part={log_item['part']}, ip={display_ip})"
                )

            # 获取目标比例
            target_ratio = self.config.get('total_ratio', 0.04)

            # 步骤 1: 提取日志
            extracted_count = 0
            last_log_file = None
            last_position = 0

            for index, log_item in enumerate(log_files):
                log_file = log_item['path']
                is_increase_log = log_item['source'] == 'increase_info_log'
                start_position = 0 if is_increase_log else self.get_log_start_position(state, log_file)
                file_size = os.path.getsize(log_file)
                if start_position > file_size:
                    self.logger.warning(
                        f"日志文件大小小于历史位置，重置为从头处理: {log_file}, "
                        f"position={start_position}, size={file_size}"
                    )
                    start_position = 0

                if is_increase_log:
                    self.logger.info(f"增量日志全量读取，不记录文件位置: {log_file}")
                self.logger.info(f"起始位置: {start_position}")
                end_position, file_extracted_count, bundle_map_dirty = self.run_extract_log(
                    log_file,
                    start_position,
                    click_id_bundle_map,
                    bundle_map_dirty,
                    {'migrated': 0, 'timestamp_fixed': 0, 'skipped_invalid': 0},
                    index == 0
                )
                extracted_count += file_extracted_count
                if not is_increase_log:
                    last_log_file = log_file
                    last_position = end_position

            if bundle_map_dirty:
                save_bundle_map(self.bundle_map_file, click_id_bundle_map, self.logger)
                bundle_map_dirty = False

            # 步骤 2: 频率控制
            filtered_count = self.run_frequency_control(click_id_bundle_map)

            # 步骤 3: 执行请求
            success_count = self.run_convert()

            # 更新状态
            new_state = {
                'last_log_file': last_log_file,
                'last_position': last_position,
                'last_run': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            self.save_state(new_state)

            # 输出汇总统计（包含比例信息）
            self.logger.info("="*80)
            self.logger.info("编排流程执行完成 - 汇总统计")
            self.logger.info("="*80)
            self.logger.info(f"步骤0 - 待处理 PURCHASE: {pending_success} 个")
            self.logger.info(f"步骤1 - 提取日志: {extracted_count} 个URL")
            self.logger.info(f"步骤2 - 频率控制: {filtered_count} 个URL（通过频率和比例限制）")
            self.logger.info(f"步骤3 - 成功转化: {success_count} 个URL")
            self.logger.info("-"*80)
            self.logger.info(f"目标转化率: {target_ratio*100:.2f}%")
            if extracted_count > 0:
                actual_ratio = success_count / extracted_count
                self.logger.info(f"实际转化率: {actual_ratio*100:.2f}% ({success_count}/{extracted_count})")
                ratio_diff = actual_ratio - target_ratio
                if abs(ratio_diff) < 0.01:  # 误差小于1%
                    self.logger.info(f"转化率符合预期 ✓")
                else:
                    self.logger.warning(f"转化率偏差: {ratio_diff*100:+.2f}%")
            else:
                self.logger.info(f"实际转化率: N/A (无提取URL)")
            self.logger.info("="*80)

        except Exception as e:
            self.logger.error(f"编排流程执行失败: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='统一编排脚本')
    parser.add_argument('--config', default='orchestrator_config.json', help='配置文件路径')
    parser.add_argument(
        '--bundle-map-retention-days',
        type=int,
        default=None,
        help='click_id_bundle_map.json 保留天数，-1 表示不清理（覆盖配置文件）'
    )
    args = parser.parse_args()
    Orchestrator(args.config, args.bundle_map_retention_days).run()


if __name__ == '__main__':
    main()
