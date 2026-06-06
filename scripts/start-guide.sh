#!/usr/bin/env bash
# 快速启动 Claude Code 在各个 worktree

# 颜色
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}=== Claude Code Worktree 快速启动 ===${NC}\n"

echo -e "${GREEN}已创建的 Worktree:${NC}"
echo -e "  1. ${YELLOW}ads-api${NC}      - API层开发 (feature/api-layer)"
echo -e "  2. ${YELLOW}ads-service${NC}  - Service层开发 (feature/service-layer)"
echo -e "  3. ${YELLOW}ads-config${NC}   - Config层开发 (feature/config-layer)"
echo ""

echo -e "${CYAN}在不同终端运行以下命令:${NC}\n"

echo -e "${GREEN}# 终端1 - API层${NC}"
echo -e "cd /Users/luoxun/dev/ads/server/ads-api && claude code"
echo ""

echo -e "${GREEN}# 终端2 - Service层${NC}"
echo -e "cd /Users/luoxun/dev/ads/server/ads-service && claude code"
echo ""

echo -e "${GREEN}# 终端3 - Config层${NC}"
echo -e "cd /Users/luoxun/dev/ads/server/ads-config && claude code"
echo ""

echo -e "${CYAN}监控冲突:${NC}"
echo -e "./scripts/conflict-detector.sh --watch"
echo ""

echo -e "${CYAN}代码同步:${NC}"
echo -e "./scripts/sync-worktrees.sh"
echo ""
