#!/usr/bin/env bash
# Git Worktrees 智能冲突预警系统（简化版）
# 兼容 bash 3.2+

set -e

# 颜色定义
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目配置
PROJECT_ROOT="/Users/luoxun/dev/ads/server"
MAIN_WORKTREE="${PROJECT_ROOT}/ads"

# Worktree列表（分支名）
WORKTREE_BRANCHES=(
    "feature/api-layer"
    "feature/service-layer"
    "feature/config-layer"
)

WORKTREE_DIRS=(
    "ads-api"
    "ads-service"
    "ads-config"
)

# 高风险文件模式
HIGH_RISK_PATTERNS=(
    "pom.xml"
    "application.yml"
    "application.properties"
    "application-.*\.yml"
)

# ==================== 辅助函数 ====================

print_header() {
    echo -e "\n${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  Git Worktrees 智能冲突预警系统           ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}\n"
}

print_separator() {
    echo -e "${BLUE}────────────────────────────────────────────${NC}"
}

is_high_risk_file() {
    local file="$1"
    for pattern in "${HIGH_RISK_PATTERNS[@]}"; do
        if echo "$file" | grep -qE "$pattern"; then
            return 0
        fi
    done
    return 1
}

# ==================== 核心功能 ====================

# 1. 快速检查
quick_check() {
    echo -e "${BLUE}⚡ 快速冲突检查${NC}\n"

    local has_issues=0

    for i in "${!WORKTREE_DIRS[@]}"; do
        local dir="${WORKTREE_DIRS[$i]}"
        local path="${PROJECT_ROOT}/${dir}"

        if [ ! -d "$path" ]; then
            echo -e "${RED}  ⚠️  worktree 不存在: $dir${NC}"
            continue
        fi

        cd "$path"

        # 检查是否有未提交的改动
        if ! git diff-index --quiet HEAD 2>/dev/null; then
            echo -e "${YELLOW}  ⚠️  $dir 有未提交的改动${NC}"
            has_issues=1
        fi

        # 检查是否与main有差异
        local diff_count=$(git diff --name-only main 2>/dev/null | wc -l | tr -d ' ')
        if [ "$diff_count" -gt 0 ]; then
            echo -e "${CYAN}  📝 $dir 相对main有 $diff_count 个改动文件${NC}"
        fi
    done

    if [ $has_issues -eq 0 ]; then
        echo -e "${GREEN}  ✓ 所有 worktree 工作区干净${NC}"
    fi

    cd "$MAIN_WORKTREE"
    echo ""
}

# 2. 扫描改动并检测冲突
scan_and_detect() {
    echo -e "${BLUE}📊 扫描所有 worktree 的文件改动...${NC}\n"

    local tmpfile="/tmp/worktree_changes_$$"
    : > "$tmpfile"

    # 收集所有改动文件
    for i in "${!WORKTREE_DIRS[@]}"; do
        local dir="${WORKTREE_DIRS[$i]}"
        local branch="${WORKTREE_BRANCHES[$i]}"
        local path="${PROJECT_ROOT}/${dir}"

        if [ ! -d "$path" ]; then
            continue
        fi

        cd "$path"
        echo -e "${CYAN}  📁 $dir${NC} (${branch})"

        # 获取相对于main的改动文件
        local changed_files=$(git diff --name-only main 2>/dev/null || echo "")

        if [ -z "$changed_files" ]; then
            changed_files=$(git diff --name-only HEAD 2>/dev/null || echo "")
            if [ -z "$changed_files" ]; then
                echo -e "     ${GREEN}✓ 无改动${NC}\n"
                continue
            fi
        fi

        # 记录改动文件
        while IFS= read -r file; do
            if [ -n "$file" ]; then
                echo "$file|$dir" >> "$tmpfile"
                echo -e "     ${YELLOW}•${NC} $file"
            fi
        done <<< "$changed_files"

        echo ""
    done

    cd "$MAIN_WORKTREE"

    # 检测冲突
    echo -e "${BLUE}🔍 检测潜在冲突...${NC}\n"

    local total_conflicts=0
    local high_risk_conflicts=0

    # 统计每个文件被修改的次数
    local conflict_tmpfile="/tmp/conflicts_$$"
    : > "$conflict_tmpfile"

    if [ -s "$tmpfile" ]; then
        sort "$tmpfile" | awk -F'|' '{
            file=$1
            dir=$2
            if (seen[file]) {
                if (!conflict[file]) {
                    conflict[file]=dirs[file]
                    conflict[file]=conflict[file] "," dir
                    print file "|" conflict[file]
                } else {
                    conflict[file]=conflict[file] "," dir
                }
            } else {
                seen[file]=1
                dirs[file]=dir
            }
        }' > "$conflict_tmpfile"

        if [ -s "$conflict_tmpfile" ]; then
            while IFS='|' read -r file worktrees; do
                total_conflicts=$((total_conflicts + 1))

                local count=$(echo "$worktrees" | tr ',' '\n' | wc -l | tr -d ' ')

                # 计算风险分数
                local risk_score=$((count * 30))

                if is_high_risk_file "$file"; then
                    risk_score=$((risk_score + 40))
                fi

                case "$file" in
                    *Service.java|*Controller.java)
                        risk_score=$((risk_score + 20))
                        ;;
                    *config*|*.yml|*.properties)
                        risk_score=$((risk_score + 30))
                        ;;
                    *.xml)
                        if echo "$file" | grep -q "mapper"; then
                            risk_score=$((risk_score + 15))
                        fi
                        ;;
                esac

                # 限制最高100分
                if [ $risk_score -gt 100 ]; then
                    risk_score=100
                fi

                # 确定风险等级
                local risk_color="$GREEN"
                local risk_label="🟢 低危"

                if [ $risk_score -ge 70 ]; then
                    risk_color="$RED"
                    risk_label="🔴 高危"
                    high_risk_conflicts=$((high_risk_conflicts + 1))
                elif [ $risk_score -ge 40 ]; then
                    risk_color="$YELLOW"
                    risk_label="🟡 中危"
                fi

                echo -e "${risk_color}  ⚠️  冲突文件: $file${NC}"
                echo -e "     风险评分: ${risk_color}${risk_score}/100${NC} $risk_label"
                echo -e "     修改位置: $(echo $worktrees | tr ',' ', ')"
                echo ""
            done < "$conflict_tmpfile"
        else
            echo -e "${GREEN}  ✓ 未检测到冲突，所有改动相互独立${NC}\n"
        fi
    else
        echo -e "${GREEN}  ✓ 所有 worktree 无改动${NC}\n"
    fi

    # 生成报告
    print_separator
    echo -e "\n${CYAN}📋 冲突分析报告${NC}\n"
    echo -e "${CYAN}总体统计:${NC}"
    echo -e "  • 活跃 worktree: ${#WORKTREE_DIRS[@]}"
    echo -e "  • 潜在冲突文件: ${total_conflicts}"
    echo -e "  • 高危冲突: ${RED}${high_risk_conflicts}${NC}"
    echo ""

    echo -e "${CYAN}💡 建议:${NC}"
    if [ $high_risk_conflicts -gt 0 ]; then
        echo -e "  ${RED}• 发现高危冲突！建议立即协调各窗口的修改${NC}"
        echo -e "  ${YELLOW}• 优先处理配置文件和核心业务文件的冲突${NC}"
    elif [ $total_conflicts -gt 0 ]; then
        echo -e "  ${YELLOW}• 存在中低风险冲突，合并前请仔细review${NC}"
    else
        echo -e "  ${GREEN}• 当前改动相互独立，可以安全合并${NC}"
    fi
    echo ""

    # 清理临时文件
    rm -f "$tmpfile" "$conflict_tmpfile"
}

# 3. 合并前预检
pre_merge_check() {
    echo -e "${BLUE}🔬 合并前预检（dry-run）...${NC}\n"

    cd "$MAIN_WORKTREE"

    for branch in "${WORKTREE_BRANCHES[@]}"; do
        echo -e "${CYAN}  检查合并: ${branch} -> main${NC}"

        # 执行dry-run merge
        if git merge --no-commit --no-ff "$branch" &>/dev/null; then
            echo -e "     ${GREEN}✓ 可以干净合并${NC}"
            git merge --abort &>/dev/null || true
        else
            echo -e "     ${RED}✗ 合并会产生冲突${NC}"

            # 获取冲突文件
            local conflict_files=$(git diff --name-only --diff-filter=U 2>/dev/null || echo "")
            if [ -n "$conflict_files" ]; then
                echo -e "     ${RED}冲突文件:${NC}"
                while IFS= read -r cfile; do
                    if [ -n "$cfile" ]; then
                        echo -e "       ${YELLOW}•${NC} $cfile"
                    fi
                done <<< "$conflict_files"
            fi

            git merge --abort &>/dev/null || true
        fi
        echo ""
    done
}

# 4. 查看 worktree 列表
list_worktrees() {
    echo -e "${CYAN}📂 当前 Worktree 列表:${NC}\n"
    git worktree list
    echo ""
}

# 5. 实时监控
watch_mode() {
    echo -e "${BLUE}👁️  进入实时监控模式（每30秒检查一次）${NC}"
    echo -e "${YELLOW}按 Ctrl+C 退出${NC}\n"
    print_separator

    while true; do
        clear
        print_header
        scan_and_detect
        echo -e "${BLUE}⏰ 下次检查: 30秒后${NC}"
        sleep 30
    done
}

# ==================== 主菜单 ====================

show_menu() {
    print_header

    echo -e "${CYAN}请选择操作:${NC}"
    echo -e "  ${GREEN}1${NC}. 完整冲突检测（扫描 + 预检 + 报告）"
    echo -e "  ${GREEN}2${NC}. 快速检查"
    echo -e "  ${GREEN}3${NC}. 仅扫描改动和检测冲突"
    echo -e "  ${GREEN}4${NC}. 合并前预检"
    echo -e "  ${GREEN}5${NC}. 实时监控模式"
    echo -e "  ${GREEN}6${NC}. 查看 worktree 列表"
    echo -e "  ${GREEN}0${NC}. 退出"
    echo ""
    echo -ne "${YELLOW}请输入选项 [0-6]: ${NC}"
}

# ==================== 主程序 ====================

main() {
    # 检查是否在git仓库中
    if ! git rev-parse --git-dir &>/dev/null; then
        echo -e "${RED}错误: 不在git仓库中${NC}"
        exit 1
    fi

    # 如果有命令行参数
    if [ $# -gt 0 ]; then
        case "$1" in
            --full|-f)
                print_header
                scan_and_detect
                pre_merge_check
                ;;
            --quick|-q)
                print_header
                quick_check
                ;;
            --watch|-w)
                watch_mode
                ;;
            --scan|-s)
                print_header
                scan_and_detect
                ;;
            --list|-l)
                print_header
                list_worktrees
                ;;
            --help|-h)
                echo "使用方法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  -f, --full     完整检测"
                echo "  -q, --quick    快速检查"
                echo "  -w, --watch    实时监控"
                echo "  -s, --scan     扫描改动和检测冲突"
                echo "  -l, --list     查看 worktree 列表"
                echo "  -h, --help     显示帮助"
                echo ""
                echo "无参数运行进入交互式菜单"
                ;;
            *)
                echo -e "${RED}未知选项: $1${NC}"
                echo "使用 --help 查看帮助"
                exit 1
                ;;
        esac
        exit 0
    fi

    # 交互式菜单
    while true; do
        show_menu
        read -r choice

        case $choice in
            1)
                clear
                print_header
                scan_and_detect
                pre_merge_check
                echo -ne "\n${YELLOW}按回车继续...${NC}"
                read -r
                clear
                ;;
            2)
                clear
                print_header
                quick_check
                echo -ne "\n${YELLOW}按回车继续...${NC}"
                read -r
                clear
                ;;
            3)
                clear
                print_header
                scan_and_detect
                echo -ne "\n${YELLOW}按回车继续...${NC}"
                read -r
                clear
                ;;
            4)
                clear
                print_header
                pre_merge_check
                echo -ne "\n${YELLOW}按回车继续...${NC}"
                read -r
                clear
                ;;
            5)
                clear
                watch_mode
                ;;
            6)
                clear
                print_header
                list_worktrees
                echo -ne "\n${YELLOW}按回车继续...${NC}"
                read -r
                clear
                ;;
            0)
                echo -e "\n${GREEN}再见！${NC}\n"
                exit 0
                ;;
            *)
                echo -e "${RED}无效选项，请重新选择${NC}"
                sleep 1
                clear
                ;;
        esac
    done
}

# 运行主程序
main "$@"
