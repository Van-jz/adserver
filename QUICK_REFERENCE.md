# Git Worktrees 快速参考卡

## ✅ 完成的设置

### 1. 创建的 Worktree（3个）

```
/Users/luoxun/dev/ads/server/
├── ads/           → main (主目录)
├── ads-api/       → feature/api-layer (API层)
├── ads-service/   → feature/service-layer (Service层)
└── ads-config/    → feature/config-layer (Config层)
```

### 2. 智能工具

| 工具 | 用途 | 命令 |
|------|------|------|
| **冲突检测器** | 扫描冲突+风险评分 | `./scripts/conflict-detector.sh` |
| **代码同步** | 自动合并+推送 | `./scripts/sync-worktrees.sh` |
| **启动指南** | 显示启动命令 | `./scripts/start-guide.sh` |

## 🚀 快速开始（复制粘贴）

### 打开多个终端

```bash
# 终端1 - API层
cd /Users/luoxun/dev/ads/server/ads-api && claude code

# 终端2 - Service层
cd /Users/luoxun/dev/ads/server/ads-service && claude code

# 终端3 - Config层
cd /Users/luoxun/dev/ads/server/ads-config && claude code

# 终端4 - 监控（可选）
cd /Users/luoxun/dev/ads/server/ads && ./scripts/conflict-detector.sh --watch
```

## 📋 日常命令

```bash
# 快速检查状态
./scripts/conflict-detector.sh --quick

# 完整冲突检测
./scripts/conflict-detector.sh --full

# 查看所有 worktree
git worktree list

# 代码同步（每2-3小时）
./scripts/sync-worktrees.sh
```

## ⚠️ 冲突风险等级

| 等级 | 分数 | 说明 | 处理 |
|------|------|------|------|
| 🟢 低危 | 0-39 | 独立改动 | 正常合并 |
| 🟡 中危 | 40-69 | 轻微冲突 | 仔细review |
| 🔴 高危 | 70-100 | 配置文件冲突 | 立即协调 |

## 🎯 工作流程

```
09:00  各窗口 git pull（开始）
   ↓
11:00  ./scripts/conflict-detector.sh --quick（检查）
   ↓
14:00  ./scripts/conflict-detector.sh --full（检测）
   ↓
17:00  ./scripts/sync-worktrees.sh（合并+推送）
   ↓
17:30  各分支同步（完成）
```

## 🛠️ 常见操作

### 提交改动

```bash
# 在任一 worktree 中
git add .
git commit -m "feat: 描述改动"
```

### 手动合并

```bash
cd /Users/luoxun/dev/ads/server/ads
git checkout main
git merge feature/api-layer
git merge feature/service-layer
git merge feature/config-layer
git push origin main
```

### 解决冲突

```bash
# 编辑冲突文件，删除冲突标记
git add <冲突文件>
git commit -m "merge: 解决冲突"
```

## 📊 监控仪表板

```bash
# 实时监控（每30秒）
./scripts/conflict-detector.sh --watch
```

输出示例：
```
📊 扫描改动...
  📁 ads-api: 3个文件
  📁 ads-service: 2个文件

🔍 检测冲突...
  ⚠️  application.yml
     风险评分: 70/100 🔴 高危
     修改位置: ads-api, ads-service

💡 建议: 发现高危冲突！
```

## 🆘 紧急情况

### 忘记在哪个窗口改了什么

```bash
./scripts/conflict-detector.sh --scan
```

### 想看某个分支的代码

```bash
git show feature/api-layer:rtb/pom.xml
```

### 想临时切换分支

```bash
git stash push -m "临时保存"
git checkout 其他分支
git stash pop  # 切回来恢复
```

## 📚 详细文档

- **完整指南**: `WORKTREE_GUIDE.md`
- **冲突检测器帮助**: `./scripts/conflict-detector.sh --help`
- **Git Worktree 官方文档**: `git worktree --help`

## 🎨 分工建议

| Worktree | 负责模块 | 避免修改 |
|----------|---------|---------|
| ads-api | `api/`, `dto/req/`, `dto/resp/` | service/, config/ |
| ads-service | `service/`, `repository/`, `mapper/` | api/, config/ |
| ads-config | `config/`, `factory/`, `task/`, `utils/` | api/, service/ |

**黄金规则**:
- ✅ 各自专注不同模块
- ⚠️ 修改配置文件前通知其他窗口
- 🔄 每2-3小时检查一次冲突
- 💾 合并前先运行完整检测

---

**快速帮助**: 运行 `./scripts/start-guide.sh` 查看启动命令
