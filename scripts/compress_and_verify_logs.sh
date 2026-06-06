#!/bin/bash

# 日志文件压缩和验证脚本
# 功能：下载 -> 压缩 -> 上传 -> 验证 -> 清理

set -e  # 遇到错误立即退出

# 降低脚本及其子进程的 CPU 优先级
# nice 值范围：-20 (最高) 到 19 (最低)
# 设置为 10 表示较低优先级
renice +10 $$ >/dev/null 2>&1 || true

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
OSS_PREFIX="oss://sg-ads/logs/"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_DIR="${SCRIPT_DIR}/tmp_compress_$(date +%Y%m%d_%H%M%S)"
LIMITED_NUM=1000
ENABLE_VERIFY=false  # 默认不进行校验
START_DAYS_AGO=5      # 处理范围的起始天数（默认前5天）
END_DAYS_AGO=3        # 处理范围的结束天数（默认前3天）

# 显示帮助信息
show_help() {
    cat << EOF
用法: $0 [选项]

选项:
    -v, --verify             启用对比校验功能（默认不校验）
    -s, --start-days N       处理范围的起始天数（默认: 5，表示前5天）
    -e, --end-days N         处理范围的结束天数（默认: 3，表示前3天）
    -h, --help               显示此帮助信息

说明:
    - 日期范围：从 START_DAYS_AGO 天前 到 END_DAYS_AGO 天前
    - 例如：-s 5 -e 3 表示处理前5天到前3天的日志
    - 默认处理范围：前5天到前3天（共3天）

示例:
    $0                        # 默认模式：处理前5-3天的日志，不校验
    $0 --verify               # 处理前5-3天的日志，启用校验
    $0 -s 7 -e 5              # 处理前7-5天的日志
    $0 -s 10 -e 5 --verify    # 处理前10-5天的日志，启用校验
EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verify)
                ENABLE_VERIFY=true
                shift
                ;;
            -s|--start-days)
                if [[ -z "$2" ]] || [[ "$2" =~ ^- ]]; then
                    log_error "选项 -s/--start-days 需要指定天数"
                    show_help
                    exit 1
                fi
                START_DAYS_AGO="$2"
                shift 2
                ;;
            -e|--end-days)
                if [[ -z "$2" ]] || [[ "$2" =~ ^- ]]; then
                    log_error "选项 -e/--end-days 需要指定天数"
                    show_help
                    exit 1
                fi
                END_DAYS_AGO="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 验证日期范围参数
    if ! [[ "$START_DAYS_AGO" =~ ^[0-9]+$ ]] || ! [[ "$END_DAYS_AGO" =~ ^[0-9]+$ ]]; then
        log_error "日期范围参数必须是数字"
        exit 1
    fi
    
    if [ "$START_DAYS_AGO" -lt "$END_DAYS_AGO" ]; then
        log_error "起始天数必须大于或等于结束天数"
        exit 1
    fi
}

# 清理函数
cleanup() {
    echo -e "${YELLOW}清理临时文件...${NC}"
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 计算日期范围
get_date_range() {
    local start_offset=$1  # 过去多少天开始
    local end_offset=$2    # 过去多少天结束
    
    local dates=()
    for i in $(seq $end_offset $start_offset); do
        local date_str
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            date_str=$(date -v-${i}d +"%Y-%m-%d")
        else
            # Linux
            date_str=$(date -d "$i days ago" +"%Y-%m-%d")
        fi
        dates+=("$date_str")
    done
    
    echo "${dates[@]}"
}

# 获取文件列表
get_oss_files() {
    local date_str=$1
    ossutil ls -d --limited-num $LIMITED_NUM "$OSS_PREFIX" --include "info*${date_str}*.log" 2>/dev/null | grep "\.log$" | awk '{print $NF}' || echo ""
}

# 计算MD5
get_md5() {
    local file_path=$1
    local md5
    if command -v md5 &> /dev/null; then
        md5=$(md5 -q "$file_path")
    else
        md5=$(md5sum "$file_path" | awk '{print $1}')
    fi
    echo "$md5"
}

# 处理单个文件
process_file() {
    local oss_file=$1
    local filename=$(basename "$oss_file")
    local zip_filename="${filename}.zip"
    local local_file="$TEMP_DIR/$filename"
    local local_zip="$TEMP_DIR/$zip_filename"
    local local_extracted="$TEMP_DIR/${filename}.extracted"
    
    log_info "处理文件: $oss_file"
    
    # 1. 下载文件
    log_info "  下载文件..."
    if ! ossutil cp "$oss_file" "$local_file"; then
        log_error "  下载失败: $oss_file"
        return 1
    fi
    
    # 2. 压缩并上传
    log_info "  压缩文件..."
    cd "$TEMP_DIR"
    zip -q "$zip_filename" "$filename"
    
    # 上传压缩文件
    log_info "  上传压缩文件..."
    local oss_zip="${oss_file}.zip"
    if ! ossutil cp "$zip_filename" "$oss_zip"; then
        log_error "  上传失败: $oss_zip"
        rm -f "$local_file" "$zip_filename"
        return 1
    fi
    
    # 删除本地zip
    rm -f "$zip_filename"
    log_info "  已删除本地zip文件"
    
    # 3. 验证数据（仅在启用时执行）
    if [ "$ENABLE_VERIFY" = true ]; then
        log_info "  开始验证..."
        
        # 下载zip文件
        local downloaded_zip="$TEMP_DIR/${filename}.downloaded.zip"
        if ! ossutil cp "$oss_zip" "$downloaded_zip"; then
            log_error "  下载zip失败: $oss_zip"
            rm -f "$local_file"
            return 1
        fi
        
        # 解压文件
        log_info "  解压文件..."
        cd "$TEMP_DIR"
        unzip -q -o "$downloaded_zip" -d "$TEMP_DIR"
        
        # 检查解压后的文件是否存在
        if [ ! -f "$local_file" ]; then
            log_error "  解压后文件不存在"
            rm -f "$local_file" "$downloaded_zip"
            return 1
        fi
        mv "$local_file" "$local_extracted"
        
        # 计算MD5
        original_md5=$(get_md5 "$local_extracted")
        
        # 重新下载原始文件对比
        log_info "  对比MD5..."
        local original_local="$TEMP_DIR/${filename}.original"
        if ! ossutil cp "$oss_file" "$original_local"; then
            log_error "  重新下载原始文件失败"
            rm -f "$local_extracted" "$downloaded_zip"
            return 1
        fi
        
        original_reference_md5=$(get_md5 "$original_local")
        
        # 验证MD5
        if [ "$original_md5" != "$original_reference_md5" ]; then
            log_error "  MD5不匹配!"
            log_error "  解压文件MD5: $original_md5"
            log_error "  原始文件MD5: $original_reference_md5"
            rm -f "$local_extracted" "$downloaded_zip" "$original_local"
            return 1
        fi
        
        log_info "  MD5验证通过: $original_md5"
        
        # 清理本地临时文件
        rm -f "$downloaded_zip" "$original_local" "$local_extracted" "$local_file"
    else
        log_info "  跳过校验（未启用 --verify 选项）"
        rm -f $local_file $local_zip $local_extracted
    fi
    
    # 4. 删除OSS上的原始文件
    log_info "  删除OSS原始文件..."
    ossutil rm "$oss_file"
    
    log_info "  文件处理完成: $oss_file ✓"
    return 0
}

# 主函数
main() {
    # 解析命令行参数
    parse_args "$@"
    
    # 清理旧的临时目录（避免磁盘空间问题）
    log_info "清理旧的临时目录..."
    find "$SCRIPT_DIR" -maxdepth 1 -type d -name "tmp_compress_*" -mtime +1 -exec rm -rf {} + 2>/dev/null || true
    
    # 创建临时目录
    
    log_info "开始处理日志文件压缩..."
    log_info "临时目录: $TEMP_DIR"
    log_info "校验功能: $([ "$ENABLE_VERIFY" = true ] && echo "启用" || echo "禁用")"
    log_info "日期范围: 前 $START_DAYS_AGO 天到前 $END_DAYS_AGO 天"
    
    # 获取日期范围
    read -ra dates <<< "$(get_date_range $START_DAYS_AGO $END_DAYS_AGO)"
    
    log_info "具体日期范围: ${dates[0]} 到 ${dates[-1]}"
    
    local total_files=0
    local success_files=0
    local failed_files=0
    
    # 遍历每个日期
    for date_str in "${dates[@]}"; do
        mkdir -p "$TEMP_DIR"
        log_info ""
        log_info "处理日期: $date_str"
        log_info "$(printf '=%.0s' {1..50})"
        
        # 获取该日期的文件列表
        local file_list
        file_list=$(get_oss_files "$date_str")
        
        if [ -z "$file_list" ]; then
            log_info "  该日期没有找到文件"
            continue
        fi
        
        # 处理每个文件
        while IFS= read -r oss_file; do
            if [ -z "$oss_file" ]; then
                continue
            fi
            
            total_files=$((total_files + 1))
            
            if process_file "$oss_file"; then
                success_files=$((success_files + 1))
            else
                failed_files=$((failed_files + 1))
            fi
            
        done <<< "$file_list"
        rm -rf "$TEMP_DIR"
    done

    # 输出统计
    log_info ""
    log_info "$(printf '=%.0s' {1..50})"
    log_info "处理完成!"
    log_info "总文件数: $total_files"
    log_info "成功: ${GREEN}$success_files${NC}"
    log_info "失败: ${RED}$failed_files${NC}"
}

# 首先解析命令行参数（用于处理 --help）
for arg in "$@"; do
    case $arg in
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            ;;
    esac
done

# 检查ossutil是否安装
if ! command -v ossutil &> /dev/null; then
    log_error "ossutil 未安装，请先安装"
    exit 1
fi

# 检查zip命令
if ! command -v zip &> /dev/null; then
    log_error "zip 未安装，请先安装"
    exit 1
fi

# 运行主函数
main "$@"

