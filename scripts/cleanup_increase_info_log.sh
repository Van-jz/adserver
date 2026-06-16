#!/bin/bash
set -euo pipefail

# 删除 increase_info_log 目录中基准日期前 N 天的增量日志。
# 默认基准日期为今天、N=1，即删除昨天；按文件名中的 YYYYMMDD 匹配，不比较 HHMM 时刻。

LOG_DIR="/data/disk0/home/luoxun/logs/springboot-scaffold/increase_info_log"
DAYS_AGO=1
BASE_DATE=""
DELETE_DATE=""
DRY_RUN=false
PREFIX="increase_info_log"

show_help() {
    cat << EOF
用法: $0 [选项] [increase_info_log目录]

选项:
    -d, --dir DIR             指定 increase_info_log 目录，等同于位置参数
    --date [YYYYMMDD]         指定基准日期；为空时默认今天
    -a, --days-ago N          删除基准日期 N 天前的日志（默认: 1，即昨天）
    -n, --dry-run             只打印将删除的文件，不实际删除
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
                LOG_DIR="$2"
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
                LOG_DIR="$1"
                shift
                ;;
        esac
    done
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

    DELETE_DATE="$(date -d "${BASE_DATE:0:4}-${BASE_DATE:4:2}-${BASE_DATE:6:2} ${DAYS_AGO} days ago" +%Y%m%d)"

    if [[ ! -d "$LOG_DIR" ]]; then
        echo "错误: 目录不存在: $LOG_DIR" >&2
        exit 1
    fi

    local matched=0
    local deleted=0
    local file

    while IFS= read -r -d '' file; do
        matched=$((matched + 1))
        if [[ "$DRY_RUN" == true ]]; then
            echo "[dry-run] 将删除: $file"
        else
            rm -f -- "$file"
            #echo "已删除: $file"
        fi
        deleted=$((deleted + 1))
    done < <(find "$LOG_DIR" -maxdepth 1 -type f -name "${PREFIX}.*.${DELETE_DATE}.*" -print0)

    echo "清理完成: 匹配=$matched, 删除=$deleted, 基准日期=$BASE_DATE, 删除日期=$DELETE_DATE, 目录=$LOG_DIR"
}

main "$@"
