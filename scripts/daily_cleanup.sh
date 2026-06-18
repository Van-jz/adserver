#!/bin/bash
set -euo pipefail

# 删除 increase_info_log 目录中基准日期前 N 天的增量日志。
# 默认基准日期为今天、N=1，即删除昨天；按文件名中的 YYYYMMDD 匹配，不比较 HHMM 时刻。
# 同时按基准日前一天分别归档 orchestrator.log/reconvert.log，并按各自保留天数清理归档。

INCREASE_LOG_DIR="/data/disk0/home/luoxun/logs/springboot-scaffold/increase_info_log"
PROCESS_DIR="/data/disk0/home/luoxun/logs/springboot-scaffold"
ORCHESTRATOR_LOG_ARCHIVE_DIR="${PROCESS_DIR}/logs/orchestrator_log"
RECONVERT_LOG_ARCHIVE_DIR="${PROCESS_DIR}/logs/reconvert_log"
ORCHESTRATOR_LOG_NAME="orchestrator.log"
RECONVERT_LOG_NAME="reconvert.log"
ORCHESTRATOR_LOG_RETENTION_DAYS=7
RECONVERT_LOG_RETENTION_DAYS=7
DAYS_AGO=1
BASE_DATE=""
DELETE_DATE=""
LOG_ARCHIVE_DATE=""
DRY_RUN=false
PREFIX="increase_info_log"

show_help() {
    cat << EOF
用法: $0 [选项] [increase_info_log目录]

选项:
    -d, --dir DIR             指定 increase_info_log 目录，等同于位置参数
    --date [YYYYMMDD]         指定基准日期；为空时默认今天
    -a, --days-ago N          删除基准日期 N 天前的日志（默认: 1，即昨天）
    -n, --dry-run             只打印将删除或归档的文件，不实际删除或归档
    -h, --help                显示帮助信息

示例:
    $0                                      # 使用默认目录，删除昨天
    $0 --dry-run                           # 使用默认目录，预览删除昨天
    $0 --date 20260616                     # 使用默认目录，删除 20260615
    $0 /path/to/increase_info_log          # 覆盖默认目录
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --date=*)
                BASE_DATE="${1#--date=}"
                shift
                ;;
            -d|--dir)
                if [[ $# -lt 2 || "$2" == -* ]]; then
                    echo "错误: $1 需要指定目录" >&2
                    exit 1
                fi
                INCREASE_LOG_DIR="$2"
                shift 2
                ;;
            -a|--days-ago)
                if [[ $# -lt 2 || "$2" == -* ]]; then
                    echo "错误: $1 需要指定天数" >&2
                    exit 1
                fi
                DAYS_AGO="$2"
                shift 2
                ;;
            --date)
                if [[ $# -ge 2 && "$2" =~ ^[0-9]{8}$ ]]; then
                    BASE_DATE="$2"
                    shift 2
                else
                    BASE_DATE=""
                    shift
                fi
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                echo "错误: 未知参数 $1" >&2
                show_help
                exit 1
                ;;
            *)
                if [[ -z "$1" ]]; then
                    shift
                    continue
                fi
                INCREASE_LOG_DIR="$1"
                shift
                ;;
        esac
    done
}

date_days_ago() {
    local days="$1"
    date -d "${BASE_DATE:0:4}-${BASE_DATE:4:2}-${BASE_DATE:6:2} ${days} days ago" +%Y%m%d
}

archive_runtime_log() {
    local log_name="$1"
    local archive_dir="$2"
    local active_log="${PROCESS_DIR}/logs/${log_name}"

    if [[ ! -f "$active_log" ]]; then
        return 1
    fi

    local archive_file="${archive_dir}/${log_name}.${LOG_ARCHIVE_DATE}"

    if [[ "$DRY_RUN" == true ]]; then
        echo "[dry-run] 将归档: $active_log -> $archive_file"
        return
    fi

    mkdir -p -- "$archive_dir"
    mv -f -- "$active_log" "$archive_file"
    touch -- "$active_log"
    echo "运行日志处理完成: 日志=$log_name, 归档日期=$LOG_ARCHIVE_DATE, 文件=$archive_file"
}

cleanup_runtime_log_archives() {
    local log_name="$1"
    local delete_date="$2"
    local archive_dir="$3"

    if [[ ! -d "$archive_dir" ]]; then
        echo "跳过运行日志归档清理: 目录不存在: $archive_dir"
        return
    fi

    local files=()
    local file
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(find "$archive_dir" -maxdepth 1 -type f -name "${log_name}.${delete_date}*" -print0)

    if [[ ${#files[@]} -eq 0 ]]; then
        echo "无需清理运行日志归档: 日志=$log_name, 日期=$delete_date"
        return
    fi

    for file in "${files[@]}"; do
        if [[ "$DRY_RUN" == true ]]; then
            echo "[dry-run] 将删除: $file"
        else
            rm -f -- "$file"
        fi
    done

    echo "运行日志归档清理完成: 日志=$log_name, 匹配=${#files[@]}, 删除日期=$delete_date, 目录=$archive_dir"
}

main() {
    parse_args "$@"

    if [[ -z "$BASE_DATE" ]]; then
        BASE_DATE="$(date +%Y%m%d)"
    fi

    if ! [[ "$BASE_DATE" =~ ^[0-9]{8}$ ]]; then
        echo "错误: 基准日期必须是 YYYYMMDD: $BASE_DATE" >&2
        exit 1
    fi

    if ! [[ "$DAYS_AGO" =~ ^[0-9]+$ ]]; then
        echo "错误: 天数必须是非负整数: $DAYS_AGO" >&2
        exit 1
    fi

    DELETE_DATE="$(date_days_ago "$DAYS_AGO")"
    LOG_ARCHIVE_DATE="$(date_days_ago 1)"

    if [[ ! -d "$INCREASE_LOG_DIR" ]]; then
        echo "错误: 目录不存在: $INCREASE_LOG_DIR" >&2
        exit 1
    fi

    local matched=0
    local deleted=0
    local file
    # 清理increase_info_log
    while IFS= read -r -d '' file; do
        matched=$((matched + 1))
        if [[ "$DRY_RUN" == true ]]; then
            echo "[dry-run] 将删除: $file"
        else
            rm -f -- "$file"
            #echo "已删除: $file"
        fi
        deleted=$((deleted + 1))
    done < <(find "$INCREASE_LOG_DIR" -maxdepth 1 -type f -name "${PREFIX}.*.${DELETE_DATE}.*" -print0)

    echo "清理完成: 匹配=$matched, 删除=$deleted, 基准日期=$BASE_DATE, 删除日期=$DELETE_DATE, 目录=$INCREASE_LOG_DIR"

    # 归档并清理orchestrator.log
    if archive_runtime_log "$ORCHESTRATOR_LOG_NAME" "$ORCHESTRATOR_LOG_ARCHIVE_DIR"; then
        cleanup_runtime_log_archives "$ORCHESTRATOR_LOG_NAME" "$(date_days_ago "$ORCHESTRATOR_LOG_RETENTION_DAYS")" "$ORCHESTRATOR_LOG_ARCHIVE_DIR"
    fi
    # 归档并清理reconvert.log
    if archive_runtime_log "$RECONVERT_LOG_NAME" "$RECONVERT_LOG_ARCHIVE_DIR"; then
        cleanup_runtime_log_archives "$RECONVERT_LOG_NAME" "$(date_days_ago "$RECONVERT_LOG_RETENTION_DAYS")" "$RECONVERT_LOG_ARCHIVE_DIR"
    fi
}

main "$@"
