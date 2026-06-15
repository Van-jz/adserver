#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monitor recent click counts by bundle from kwaiadsinfo postshow logs."""

import argparse
import json
import os
import re
import socket
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


BLOCKED_DOMAINS = ("ad.ap4r.com", "s16.kwai.net", "adx.opera.com", "liftoff-creatives.io")
REQUEST_MARKER = "收到 kwaiadsinfo postshow 请求数据: "
UNKNOWN_BUNDLE = "(unknown)"
DEFAULT_OUTPUT_DIR = "/data/disk0/home/luoxun/logs/springboot-scaffold/clk_stat"
DEFAULT_LOG_DIR = "/data/disk0/home/luoxun/logs/springboot-scaffold"
DEFAULT_LOG_PREFIX = "info.prod0320"
DEFAULT_BUNDLE_MAP_FILE = "click_id_bundle_map.json"
LOG_TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:[.,](\d{1,6}))?")
MAIL_ALERT_MINUTES = 30
MAIL_ALERT_TO = "hanjing915@qq.com"
CLICK_DROP_ALERT_THRESHOLD = 0.10


def script_dir() -> str:
    """返回当前脚本所在目录，用来定位相邻的 send_mail 模块。"""
    return os.path.dirname(os.path.abspath(__file__))


def load_json_file(path: str, default: Any) -> Any:
    """读取 JSON 文件；文件不存在或格式错误时返回 default。"""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def find_log_files(log_dir: str, log_prefix: str) -> List[str]:
    """在日志目录中找到匹配前缀且以 .log 结尾的文件，按修改时间从新到旧排序。"""
    try:
        files = os.listdir(log_dir)
    except OSError as exc:
        raise RuntimeError(f"cannot list log dir {log_dir}: {exc}") from exc

    log_files = [
        os.path.join(log_dir, name)
        for name in files
        if name.startswith(log_prefix) and name.endswith(".log")
    ]
    if not log_files:
        raise RuntimeError(f"no log files found in {log_dir} with prefix {log_prefix}")
    return sorted(log_files, key=os.path.getmtime, reverse=True)


def find_latest_log_file(log_dir: str, log_prefix: str) -> str:
    """在日志目录中找到最新修改的、匹配前缀且以 .log 结尾的文件。"""
    return find_log_files(log_dir, log_prefix)[0]


def extract_request_body(log_line: str) -> Optional[str]:
    """从 postshow 日志行中截取请求体；非目标日志行返回 None。"""
    pos = log_line.find(REQUEST_MARKER)
    if pos < 0:
        return None
    return log_line[pos + len(REQUEST_MARKER):].strip()


def parse_log_time(log_line: str) -> Optional[Tuple[float, str]]:
    """解析日志行首时间，返回时间戳和原始展示字符串。"""
    match = LOG_TIME_RE.match(log_line)
    if not match:
        return None

    base, fraction = match.groups()
    try:
        dt = datetime.strptime(base, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    display = base
    if fraction:
        micros = fraction[:6].ljust(6, "0")
        dt = dt.replace(microsecond=int(micros))
        display = f"{base}.{fraction}"
    return dt.timestamp(), display


def format_log_time(ts: float) -> str:
    """把秒级时间戳格式化成日志时间字符串。"""
    dt = datetime.fromtimestamp(ts)
    if dt.microsecond:
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f").rstrip("0")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_replay_time(value: str) -> datetime:
    """解析历史回放时间参数。"""
    for fmt in ("%Y%m%d %H%M", "%Y%m%d%H%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"invalid time '{value}', expected format like '20260615 1500'"
    )


def parse_json_data(request_body_str: str) -> Optional[Dict[str, Any]]:
    """解析 postshow 请求体，兼容直接 JSON 和 data=URL编码JSON 两种格式。"""
    try:
        body = request_body_str[5:] if request_body_str.startswith("data=") else request_body_str
        return json.loads(urllib.parse.unquote(body))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def extract_referrer_package(json_data: Dict[str, Any]) -> Optional[str]:
    """从请求数据中提取 referrer_package，作为本批 URL 的 bundle。"""
    data = json_data.get("data")
    if isinstance(data, dict):
        value = data.get("referrer_package")
        return value if isinstance(value, str) and value else None
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None
        if isinstance(parsed, dict):
            value = parsed.get("referrer_package")
            return value if isinstance(value, str) and value else None
    return None


def extract_urls_from_data(json_data: Dict[str, Any]) -> List[str]:
    """从请求数据中提取 URL 列表，兼容 data 为 dict 或字符串的格式。"""
    data = json_data.get("data")
    if isinstance(data, dict):
        urls = data.get("urls", [])
        return [u for u in urls if isinstance(u, str)] if isinstance(urls, list) else []
    if isinstance(data, str):
        return re.findall(r"https?://[^\s]+", data)
    return []


def parse_url_pixel_id(url: str) -> Tuple[Optional[str], Optional[str]]:
    """从点击 URL 中提取 pixel_id 和 click_id；解析失败返回 (None, None)。"""
    try:
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        pixel_id = None
        if "pixel_id" in query_params and query_params["pixel_id"]:
            match = re.match(r"^(\d+)", query_params["pixel_id"][0])
            if match:
                pixel_id = match.group(1)

        click_id = None
        if "click_id" in query_params and query_params["click_id"]:
            click_id = query_params["click_id"][0]

        return pixel_id, click_id
    except Exception:
        return None, None


def load_bundle_map(bundle_map_file: Optional[str]) -> Dict[str, str]:
    """读取 click_id 到 bundle 的兜底映射文件；兼容值为字符串或对象的新旧格式。"""
    if not bundle_map_file:
        return {}
    data = load_json_file(bundle_map_file, {})
    if not isinstance(data, dict):
        return {}

    bundle_map = {}
    for click_id, value in data.items():
        if not isinstance(click_id, str) or not click_id:
            continue

        bundle = None
        if isinstance(value, str):
            bundle = value
        elif isinstance(value, dict):
            bundle = value.get("bundle")

        if isinstance(bundle, str) and bundle:
            bundle_map[click_id] = bundle

    return bundle_map


def find_last_log_time(log_file: str) -> Optional[Tuple[float, str]]:
    """扫描日志文件，找到最后一条可解析的行首时间。"""
    latest_log_time = None
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed = parse_log_time(line)
            if parsed:
                latest_log_time = parsed
    return latest_log_time


def find_latest_parsed_log_time(log_files: List[str]) -> Optional[Tuple[str, float, str]]:
    """按文件修改时间从新到旧查找最近一条可解析日志时间。"""
    for log_file in log_files:
        latest_log_time = find_last_log_time(log_file)
        if latest_log_time:
            return log_file, latest_log_time[0], latest_log_time[1]
    return None


def find_window_log_files(log_files: List[str], window_start_time: float, latest_log_file: str) -> List[str]:
    """选择可能覆盖统计窗口的日志文件，并按修改时间从旧到新排序。"""
    selected = [
        log_file
        for log_file in log_files
        if log_file == latest_log_file or os.path.getmtime(log_file) >= window_start_time
    ]
    return sorted(selected, key=os.path.getmtime)


def scan_window_clicks(
    log_files: List[str],
    window_start_time: float,
    window_end_time: float,
    bundle_map: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """统计指定日志时间窗口内的有效点击事件，并按 click_id 去重。

    bundle 归因优先级：click_id_bundle_map -> referrer_package -> (unknown)。
    """
    events: List[Dict[str, Any]] = []
    seen_click_ids = set()
    stats = {
        "scanned_lines": 0,
        "scanned_log_time_start": format_log_time(window_start_time),
        "scanned_log_time_end": format_log_time(window_end_time),
        "actual_scanned_log_time_start": None,
        "actual_scanned_log_time_end": None,
        "postshow_lines": 0,
        "candidate_urls": 0,
        "duplicate_click_ids": 0,
        "blocked_urls": 0,
        "valid_clicks": 0,
    }
    earliest_log_time = None
    latest_log_time = None

    last_referrer_package = None
    lines_since_referrer = 0

    for log_file in log_files:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parsed_log_time = parse_log_time(line)
                if not parsed_log_time:
                    continue

                log_time, log_time_display = parsed_log_time
                if log_time > window_end_time:
                    continue

                # 窗口前的 postshow 也要解析，用来延续 referrer_package 上下文；
                # 只有窗口内的 URL 才会进入最终统计。
                in_window = log_time >= window_start_time
                if in_window:
                    stats["scanned_lines"] += 1
                    if earliest_log_time is None or log_time < earliest_log_time[0]:
                        earliest_log_time = (log_time, log_time_display)
                    if latest_log_time is None or log_time > latest_log_time[0]:
                        latest_log_time = (log_time, log_time_display)

                request_body = extract_request_body(line)
                if request_body is None:
                    continue

                stats["postshow_lines"] += 1
                json_data = parse_json_data(request_body)
                if json_data is None:
                    continue

                referrer_package = extract_referrer_package(json_data)
                if referrer_package:
                    last_referrer_package = referrer_package
                    lines_since_referrer = 0
                else:
                    lines_since_referrer += 1
                    if last_referrer_package and lines_since_referrer <= 10:
                        referrer_package = last_referrer_package

                if not in_window:
                    continue

                for raw_url in extract_urls_from_data(json_data):
                    url = raw_url.strip().rstrip('"')
                    if "click_id" not in url or "pixel_id" not in url:
                        continue
                    if any(domain in url for domain in BLOCKED_DOMAINS):
                        stats["blocked_urls"] += 1
                        continue

                    stats["candidate_urls"] += 1
                    _, click_id = parse_url_pixel_id(url)
                    if not click_id:
                        continue
                    # 同一次扫描内，同一个 click_id 只计一次，保持与 orchestrator 的去重口径一致。
                    if click_id in seen_click_ids:
                        stats["duplicate_click_ids"] += 1
                        continue

                    seen_click_ids.add(click_id)
                    bundle = bundle_map.get(click_id) or referrer_package or UNKNOWN_BUNDLE
                    events.append(
                        {
                            "log_time": log_time,
                            "log_time_display": log_time_display,
                            "bundle": bundle,
                            "click_id": click_id,
                        }
                    )
                    stats["valid_clicks"] += 1

    if earliest_log_time:
        stats["actual_scanned_log_time_start"] = earliest_log_time[1]
    if latest_log_time:
        stats["actual_scanned_log_time_end"] = latest_log_time[1]

    return events, stats


def build_rows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把点击事件聚合成按 bundle 展示的表格行。"""
    bundle_clicks = Counter(event.get("bundle", UNKNOWN_BUNDLE) for event in events)

    rows = []
    for bundle in sorted(bundle_clicks.keys()):
        rows.append(
            {
                "bundle": bundle,
                "clicks": bundle_clicks[bundle],
            }
        )
    rows.sort(key=lambda row: (-row["clicks"], row["bundle"]))
    return rows


def render_table(rows: List[Dict[str, Any]], top: Optional[int], show_all: bool) -> str:
    """把聚合行渲染为终端可读的等宽表格。"""
    if not rows:
        return "No clicks in the current window."

    visible_rows = rows if show_all or top is None else rows[:top]
    headers = ["bundle", "clicks"]
    widths = {
        header: max(len(header), *(len(str(row[header])) for row in visible_rows))
        for header in headers
    }

    lines = []
    lines.append("  ".join(header.ljust(widths[header]) for header in headers))
    lines.append("  ".join("-" * widths[header] for header in headers))
    for row in visible_rows:
        lines.append(
            "  ".join(
                [
                    str(row["bundle"]).ljust(widths["bundle"]),
                    str(row["clicks"]).rjust(widths["clicks"]),
                ]
            )
        )

    hidden = len(rows) - len(visible_rows)
    if hidden > 0:
        lines.append(f"... {hidden} more bundle(s); use --all to show all")
    return "\n".join(lines)


def build_output_text(
    latest_log_file: str,
    minutes: int,
    scanned_range: str,
    total_clicks: int,
    table_text: str,
) -> str:
    """组装本次运行的完整输出文本，供终端打印和文件落盘共用。"""
    return "\n".join(
        [
            f"log_file: {latest_log_file}",
            f"min: {minutes}",
            f"scanned_log_time_range: {scanned_range}",
            f"total_clicks: {total_clicks}",
            table_text,
        ]
    )


def write_output_file(output_dir: str, output_text: str, run_dt: datetime) -> str:
    """将本次统计结果写入 clk_stat.YYYYMMDD-hhmm 文件，并返回文件路径。"""
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"clk_stat.{run_dt.strftime('%Y%m%d-%H%M')}")
    append_mode = os.path.exists(output_file)
    with open(output_file, "a", encoding="utf-8") as f:
        if append_mode:
            f.write("\n" + "=" * 80 + "\n")
        f.write(output_text)
        f.write("\n")
    return output_file


def get_clk_stat_file_path(output_dir: str, run_dt: datetime) -> str:
    """按运行时间拼出对应的 clk_stat 文件路径。"""
    return os.path.join(output_dir, f"clk_stat.{run_dt.strftime('%Y%m%d-%H%M')}")


def read_total_clicks_from_clk_stat(path: str) -> Optional[int]:
    """读取 clk_stat 文件里的 total_clicks；追加写入时取最后一次结果。"""
    totals = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = re.match(r"^\s*total_clicks:\s*(\d+)\s*$", line)
                if match:
                    totals.append(int(match.group(1)))
    except FileNotFoundError:
        return None
    except OSError as exc:
        print(f"warning: cannot read yesterday clk_stat {path}: {exc}", file=sys.stderr)
        return None

    if not totals:
        print(f"warning: cannot find total_clicks in yesterday clk_stat: {path}", file=sys.stderr)
        return None
    return totals[-1]


def get_machine_ip() -> str:
    """获取报警邮件里展示的机器 IP，可用 CLK_MONITOR_MACHINE_IP 覆盖。"""
    env_ip = os.environ.get("CLK_MONITOR_MACHINE_IP")
    if env_ip:
        return env_ip

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    finally:
        sock.close()

    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "unknown"


def maybe_send_zero_clicks_alert(
    minutes: int,
    total_clicks: int,
    latest_log_file: str,
    scanned_range: str,
    output_file: str,
) -> Optional[str]:
    """满足 30 分钟以上且零点击时，通过 send_mail.py 发送报警邮件。"""
    if minutes < MAIL_ALERT_MINUTES or total_clicks != 0:
        return None

    send_mail_dir = os.path.abspath(os.path.join(script_dir(), "..", "send_mail"))
    if send_mail_dir not in sys.path:
        sys.path.insert(0, send_mail_dir)

    try:
        from send_mail import send_mail
    except Exception as exc:
        print(f"warning: cannot import send_mail.py: {exc}", file=sys.stderr)
        return "failed"

    machine_ip = get_machine_ip()
    subject = f"[clk_monitor] {machine_ip} {minutes} minutes zero clicks alert"
    content = "\n".join(
        [
            f"！机器{machine_ip}已经{minutes}分钟没有点击了！",
            f"机器IP machine_ip: {machine_ip}",
            f"统计时间窗 minutes: {minutes}",
            f"总点击 total_clicks: {total_clicks}",
            f"日志文件 log_file: {latest_log_file}",
            f"扫描时间窗 scanned_log_time_range: {scanned_range}",
            f"输出文件 output_file: {output_file}",
        ]
    )
    result = send_mail(subject, content, MAIL_ALERT_TO)
    if result != "sent":
        print(f"warning: zero clicks alert mail result: {result}", file=sys.stderr)
    return result


def maybe_send_click_drop_alert(
    output_dir: str,
    run_dt: datetime,
    total_clicks: int,
    latest_log_file: str,
    scanned_range: str,
    output_file: str,
) -> Optional[str]:
    """对比昨天同时间总点击，下降超过阈值时发送报警邮件。"""
    yesterday_dt = run_dt - timedelta(days=1)
    yesterday_file = get_clk_stat_file_path(output_dir, yesterday_dt)
    yesterday_total_clicks = read_total_clicks_from_clk_stat(yesterday_file)
    if yesterday_total_clicks is None:
        print(f"info: no yesterday clk_stat data for same time: {yesterday_file}; skip click drop alert")
        return None
    if yesterday_total_clicks <= 0:
        print(
            f"info: yesterday total_clicks is {yesterday_total_clicks} for {yesterday_file}; skip click drop alert"
        )
        return None

    drop_ratio = (yesterday_total_clicks - total_clicks) / yesterday_total_clicks
    if drop_ratio <= CLICK_DROP_ALERT_THRESHOLD:
        return None

    send_mail_dir = os.path.abspath(os.path.join(script_dir(), "..", "send_mail"))
    if send_mail_dir not in sys.path:
        sys.path.insert(0, send_mail_dir)

    try:
        from send_mail import send_mail
    except Exception as exc:
        print(f"warning: cannot import send_mail.py: {exc}", file=sys.stderr)
        return "failed"

    machine_ip = get_machine_ip()
    drop_percent = drop_ratio * 100
    subject = f"[clk_monitor] {machine_ip} clicks dropped {drop_percent:.1f}% alert"
    content = "\n".join(
        [
            f"！机器{machine_ip}当轮点击较昨天同时间下降超过{CLICK_DROP_ALERT_THRESHOLD:.0%}！",
            f"机器IP machine_ip: {machine_ip}",
            f"当前时间 current_time: {run_dt.strftime('%Y-%m-%d %H:%M')}",
            f"昨日同期 yesterday_same_time: {yesterday_dt.strftime('%Y-%m-%d %H:%M')}",
            f"本轮总点击 current_total_clicks: {total_clicks}",
            f"昨日同期总点击 yesterday_total_clicks: {yesterday_total_clicks}",
            f"下跌比例 drop_percent: {drop_percent:.2f}%",
            f"日志文件 log_file: {latest_log_file}",
            f"扫描时间段 scanned_log_time_range: {scanned_range}",
            f"输出文件 output_file: {output_file}",
            f"昨日文件 yesterday_output_file: {yesterday_file}",
        ]
    )
    result = send_mail(subject, content, MAIL_ALERT_TO)
    if result != "sent":
        print(f"warning: click drop alert mail result: {result}", file=sys.stderr)
    return result


def cleanup_old_clk_stat_outputs(output_dir: str, retention_days: int, now_dt: datetime) -> int:
    """清理 output_dir 中超过保留天数的 clk_stat.* 产物，返回删除数量。"""
    cutoff_ts = (now_dt - timedelta(days=retention_days)).timestamp()
    deleted = 0
    try:
        names = os.listdir(output_dir)
    except OSError as exc:
        print(f"warning: cannot list output dir for cleanup: {output_dir}: {exc}", file=sys.stderr)
        return deleted

    for name in names:
        if not name.startswith("clk_stat."):
            continue
        path = os.path.join(output_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            if os.path.getmtime(path) >= cutoff_ts:
                continue
            os.remove(path)
            deleted += 1
        except OSError as exc:
            print(f"warning: cannot remove old clk_stat output {path}: {exc}", file=sys.stderr)
    return deleted


def build_scanned_range(stats: Dict[str, Any]) -> str:
    """从扫描统计中生成展示用时间范围。"""
    if stats.get("scanned_log_time_start") and stats.get("scanned_log_time_end"):
        return f"{stats['scanned_log_time_start']} -> {stats['scanned_log_time_end']}"
    return "N/A"


def run_window(
    args: argparse.Namespace,
    log_files: List[str],
    bundle_map: Dict[str, str],
    window_start_time: float,
    window_end_time: float,
    output_dt: datetime,
    send_alerts: bool,
) -> int:
    """扫描一个时间窗口，输出统计结果并按需发送报警。"""
    window_log_files = find_window_log_files(log_files, window_start_time, log_files[0])
    latest_log_file = window_log_files[-1] if window_log_files else log_files[0]

    window_events, stats = scan_window_clicks(
        window_log_files,
        window_start_time,
        window_end_time,
        bundle_map,
    )
    rows = build_rows(window_events)
    scanned_range = build_scanned_range(stats)
    output_text = build_output_text(
        latest_log_file,
        int(round((window_end_time - window_start_time) / 60)),
        scanned_range,
        len(window_events),
        render_table(rows, args.top, args.all),
    )
    print(output_text)
    output_file = write_output_file(args.output_dir, output_text, output_dt)
    print(f"output_file: {output_file}")

    if send_alerts:
        drop_alert_result = maybe_send_click_drop_alert(
            args.output_dir,
            output_dt,
            len(window_events),
            latest_log_file,
            scanned_range,
            output_file,
        )
        if drop_alert_result:
            print(f"click_drop_alert_mail: {drop_alert_result}")
        alert_result = maybe_send_zero_clicks_alert(
            int(round((window_end_time - window_start_time) / 60)),
            len(window_events),
            latest_log_file,
            scanned_range,
            output_file,
        )
        if alert_result:
            print(f"alert_mail: {alert_result}")

    return 0


def parse_args() -> argparse.Namespace:
    """定义并解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Monitor recent click counts by bundle.")
    parser.add_argument("--min", type=int, default=30, help="minutes before the latest log timestamp to scan")
    parser.add_argument("--from", dest="replay_from", type=parse_replay_time, help="replay start time, e.g. '20260615 1500'")
    parser.add_argument("--to", dest="replay_to", type=parse_replay_time, help="replay end time, e.g. '20260615 1800'")
    parser.add_argument("--top", type=int, default=20, help="number of bundles to display")
    parser.add_argument("--all", action="store_true", help="show all bundles")
    parser.add_argument("--no-alert", action="store_true", help="do not send alert mail")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="directory to write clk_stat.YYYYMMDD-hhmm")
    parser.add_argument("--retention-days", type=int, default=3, help="days to keep clk_stat.* outputs")
    return parser.parse_args()


def main() -> int:
    """脚本入口：确定窗口、扫描日志并输出统计表。"""
    args = parse_args()
    run_dt = datetime.now()
    if args.min <= 0:
        print("error: --min must be positive", file=sys.stderr)
        return 2
    if args.top is not None and args.top <= 0:
        print("error: --top must be positive", file=sys.stderr)
        return 2
    if args.retention_days <= 0:
        print("error: --retention-days must be positive", file=sys.stderr)
        return 2
    if (args.replay_from is None) != (args.replay_to is None):
        print("error: --from and --to must be used together", file=sys.stderr)
        return 2
    if args.replay_from and args.replay_to and args.replay_to <= args.replay_from:
        print("error: --to must be later than --from", file=sys.stderr)
        return 2

    log_dir = DEFAULT_LOG_DIR
    log_prefix = DEFAULT_LOG_PREFIX
    bundle_map_file = DEFAULT_BUNDLE_MAP_FILE
    log_files = find_log_files(log_dir, log_prefix)
    latest_log_file = log_files[0]
    window_seconds = args.min * 60
    send_alerts = not args.no_alert

    bundle_map = load_bundle_map(bundle_map_file)
    if args.replay_from and args.replay_to:
        replay_start_time = args.replay_from.timestamp()
        replay_end_time = args.replay_to.timestamp()
        window_start_time = replay_start_time
        while window_start_time < replay_end_time:
            window_end_time = min(window_start_time + window_seconds, replay_end_time)
            output_dt = datetime.fromtimestamp(window_end_time)
            print(f"replay_window: {format_log_time(window_start_time)} -> {format_log_time(window_end_time)}")
            run_window(
                args,
                log_files,
                bundle_map,
                window_start_time,
                window_end_time,
                output_dt,
                send_alerts=False,
            )
            window_start_time = window_end_time
        return 0

    latest_log_time = find_latest_parsed_log_time(log_files)
    if not latest_log_time:
        output_text = build_output_text(
            latest_log_file,
            args.min,
            "N/A",
            0,
            "No clicks in the current window.",
        )
        print(output_text)
        output_file = write_output_file(args.output_dir, output_text, run_dt)
        print(f"output_file: {output_file}")
        if send_alerts:
            drop_alert_result = maybe_send_click_drop_alert(
                args.output_dir,
                run_dt,
                0,
                latest_log_file,
                "N/A",
                output_file,
            )
            if drop_alert_result:
                print(f"click_drop_alert_mail: {drop_alert_result}")
        deleted = cleanup_old_clk_stat_outputs(args.output_dir, args.retention_days, run_dt)
        print(f"cleanup_deleted: {deleted}")
        if send_alerts:
            alert_result = maybe_send_zero_clicks_alert(
                args.min,
                0,
                latest_log_file,
                "N/A",
                output_file,
            )
            if alert_result:
                print(f"alert_mail: {alert_result}")
        return 0

    latest_log_file, window_end_time, _ = latest_log_time
    window_start_time = window_end_time - window_seconds
    run_window(
        args,
        log_files,
        bundle_map,
        window_start_time,
        window_end_time,
        run_dt,
        send_alerts=send_alerts,
    )
    deleted = cleanup_old_clk_stat_outputs(args.output_dir, args.retention_days, run_dt)
    print(f"cleanup_deleted: {deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
