#!/bin/bash
set -euo pipefail

# 将昨天的 purchase.log 归档为 purchase_log/purchase_log.YYYYMMDD。
# 本脚本只负责归档逻辑，定时执行时间由 crontab 配置。

# 第一个参数可指定当前活跃 purchase 日志路径，默认使用当前目录的 purchase.log。
LOG_FILE="${1:-purchase.log}"
LOG_DIR="$(cd "$(dirname "$LOG_FILE")" && pwd)"
LOG_BASENAME="$(basename "$LOG_FILE")"
ACTIVE_LOG="$LOG_DIR/$LOG_BASENAME"

# 第二个参数可指定归档目录，默认使用当前日志同级的 purchase_log 目录。
ARCHIVE_DIR="${2:-$LOG_DIR/purchase_log}"
YESTERDAY="$(date -d "yesterday" +%Y%m%d)"
ARCHIVE_FILE="$ARCHIVE_DIR/purchase_log.$YESTERDAY"

mkdir -p "$ARCHIVE_DIR"

# 如果当前日志不存在，只创建一个空日志文件，避免后续写入失败。
if [ ! -e "$ACTIVE_LOG" ]; then
    touch "$ACTIVE_LOG"
    echo "purchase 日志不存在，已创建空日志: $ACTIVE_LOG"
    exit 0
fi

# 已有同名归档时直接失败，避免覆盖历史数据。
if [ -e "$ARCHIVE_FILE" ]; then
    echo "错误: 归档文件已存在，拒绝覆盖: $ARCHIVE_FILE" >&2
    exit 1
fi

# 移动旧日志后立刻创建新的空 purchase.log，供写入进程继续追加。
mv "$ACTIVE_LOG" "$ARCHIVE_FILE"
touch "$ACTIVE_LOG"

echo "已归档 $ACTIVE_LOG -> $ARCHIVE_FILE"
