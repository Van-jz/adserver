#!/bin/bash
# Git Worktrees 代码同步脚本

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="/Users/luoxun/dev/ads/server"

# Worktree 配置数组
WORKTREE_DIRS=(
    "ads-api"
    "ads-service"
    "ads-config"
)

WORKTREE_BRANCHES=(
    "feature/api-layer"
    "feature/service-layer"
    "feature/config-layer"
)

echo -e "${GREEN}=== Git Worktrees 代码同步 ===${NC}\n"

# 1. 检查所有 worktree 状态
echo -e "${YELLOW}检查所有 worktree 状态...${NC}"
for i in "${!WORKTREE_DIRS[@]}"; do
    dir="${WORKTREE_DIRS[$i]}"
    branch="${WORKTREE_BRANCHES[$i]}"
    path="${PROJECT_ROOT}/${dir}"

    if [ -d "$path" ]; then
        echo -e "\n📁 ${dir} (${branch})"
        cd "$path"

        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            echo -e "${RED}  ⚠️  有未提交的改动${NC}"
            git status -s
        else
            echo -e "${GREEN}  ✓ 工作区干净${NC}"
        fi
    fi
done

# 2. 提交所有 worktree 的改动
echo -e "\n${YELLOW}是否提交所有改动? (y/n)${NC}"
read -r commit_all

if [ "$commit_all" = "y" ]; then
    for i in "${!WORKTREE_DIRS[@]}"; do
        dir="${WORKTREE_DIRS[$i]}"
        path="${PROJECT_ROOT}/${dir}"

        if [ -d "$path" ]; then
            cd "$path"

            if ! git diff-index --quiet HEAD -- 2>/dev/null; then
                echo -e "\n📝 提交 ${dir} 的改动..."
                git add .
                echo "请输入提交信息 (${dir}):"
                read -r commit_msg
                git commit -m "$commit_msg"
                echo -e "${GREEN}  ✓ 提交成功${NC}"
            fi
        fi
    done
fi

# 3. 合并所有分支到 main
echo -e "\n${YELLOW}是否合并所有分支到 main? (y/n)${NC}"
read -r merge_all

if [ "$merge_all" = "y" ]; then
    cd "${PROJECT_ROOT}/ads"
    git checkout main

    for branch in "${WORKTREE_BRANCHES[@]}"; do
        if [ "$branch" != "main" ]; then
            echo -e "\n🔀 合并 ${branch}..."

            if git merge "$branch" --no-edit; then
                echo -e "${GREEN}  ✓ 合并成功${NC}"
            else
                echo -e "${RED}  ⚠️  合并冲突，请手动解决${NC}"
                echo "解决冲突后执行:"
                echo "  git add ."
                echo "  git commit"
                exit 1
            fi
        fi
    done

    echo -e "\n${GREEN}✓ 所有分支已合并到 main${NC}"
fi

# 4. 同步 main 到所有分支
echo -e "\n${YELLOW}是否将 main 同步到所有分支? (y/n)${NC}"
read -r sync_main

if [ "$sync_main" = "y" ]; then
    for i in "${!WORKTREE_DIRS[@]}"; do
        dir="${WORKTREE_DIRS[$i]}"
        branch="${WORKTREE_BRANCHES[$i]}"
        path="${PROJECT_ROOT}/${dir}"

        if [ "$branch" != "main" ] && [ -d "$path" ]; then
            echo -e "\n🔄 同步 main 到 ${branch}..."
            cd "$path"

            if git merge main --no-edit; then
                echo -e "${GREEN}  ✓ 同步成功${NC}"
            else
                echo -e "${RED}  ⚠️  同步冲突，请手动解决${NC}"
                exit 1
            fi
        fi
    done

    echo -e "\n${GREEN}✓ main 已同步到所有分支${NC}"
fi

# 5. 推送到远程
echo -e "\n${YELLOW}是否推送所有改动到远程? (y/n)${NC}"
read -r push_all

if [ "$push_all" = "y" ]; then
    for i in "${!WORKTREE_DIRS[@]}"; do
        dir="${WORKTREE_DIRS[$i]}"
        branch="${WORKTREE_BRANCHES[$i]}"
        path="${PROJECT_ROOT}/${dir}"

        if [ -d "$path" ]; then
            cd "$path"
            echo -e "\n⬆️  推送 ${branch}..."

            if git push origin "$branch"; then
                echo -e "${GREEN}  ✓ 推送成功${NC}"
            else
                echo -e "${RED}  ⚠️  推送失败${NC}"
            fi
        fi
    done
fi

echo -e "\n${GREEN}=== 同步完成 ===${NC}"
