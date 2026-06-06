# Git Worktrees 多窗口开发指南

## 📁 Worktree 结构

已创建的3个独立工作区：

```
/Users/luoxun/dev/ads/server/
├── ads/              (主目录 - main分支)
├── ads-api/          (API层 - feature/api-layer)
├── ads-service/      (Service层 - feature/service-layer)
└── ads-config/       (Config层 - feature/config-layer)
```

### 分工建议

| Worktree | 负责模块 | 主要文件 |
|----------|---------|---------|
| **ads-api** | 控制器层 | `rtb/src/main/java/com/example/springbootscaffold/api/` |
| **ads-service** | 业务逻辑层 | `rtb/src/main/java/com/example/springbootscaffold/service/` |
| **ads-config** | 配置与工具 | `config/`, `factory/`, `task/`, `utils/` |

## 🚀 快速开始

### 1. 在不同终端打开各个 worktree

```bash
# 终端1 - API层开发
cd /Users/luoxun/dev/ads/server/ads-api
claude code

# 终端2 - Service层开发
cd /Users/luoxun/dev/ads/server/ads-service
claude code

# 终端3 - Config层开发
cd /Users/luoxun/dev/ads/server/ads-config
claude code
```

### 2. 日常工作流程

**每个窗口独立工作：**

```bash
# 在任一 worktree 中
# Claude 修改代码...

# 提交改动
git add .
git commit -m "feat: 描述你的改动"
```

**定期同步（每2-3小时）：**

```bash
# 在主目录运行同步脚本
cd /Users/luoxun/dev/ads/server/ads
./scripts/sync-worktrees.sh
```

## 🔍 智能冲突检测器

### 使用方法

**交互式菜单（推荐）：**

```bash
cd /Users/luoxun/dev/ads/server/ads
./scripts/conflict-detector.sh
```

会显示菜单：
```
1. 完整冲突检测（扫描 + 预检 + 报告）
2. 快速检查
3. 仅扫描改动
4. 合并前预检
5. 实时监控模式
6. 查看 worktree 列表
```

**命令行模式：**

```bash
# 完整检测
./scripts/conflict-detector.sh --full

# 快速检查
./scripts/conflict-detector.sh --quick

# 实时监控（每30秒检查一次）
./scripts/conflict-detector.sh --watch

# 仅扫描改动
./scripts/conflict-detector.sh --scan
```

### 功能说明

#### 1. 完整冲突检测 ⭐推荐

扫描所有 worktree 的改动，检测冲突，给出风险评分和建议：

```bash
./scripts/conflict-detector.sh --full
```

**输出示例：**

```
📊 扫描所有 worktree 的文件改动...
  📁 ads-api (feature/api-layer)
     • rtb/src/main/java/.../SspController.java
     • application.yml

  📁 ads-service (feature/service-layer)
     • rtb/src/main/java/.../SspService.java
     • application.yml

🔍 检测潜在冲突...
  ⚠️  冲突文件: application.yml
     风险评分: 70/100 🔴 高危
     修改位置: ads-api, ads-service

📋 冲突分析报告
总体统计:
  • 活跃 worktree: 3
  • 潜在冲突文件: 1
  • 高危冲突: 1

💡 建议:
  • 发现高危冲突！建议立即协调各窗口的修改
  • 优先处理配置文件和核心业务文件的冲突
```

#### 2. 快速检查

只检查是否有未提交的改动：

```bash
./scripts/conflict-detector.sh --quick
```

#### 3. 实时监控模式

后台持续监控（适合长时间开发）：

```bash
./scripts/conflict-detector.sh --watch
```

每30秒自动检查一次，实时发现冲突。

### 风险评分规则

| 分数范围 | 风险等级 | 说明 |
|---------|---------|------|
| 0-39 | 🟢 低危 | 改动独立，可安全合并 |
| 40-69 | 🟡 中危 | 需要review，可能有轻微冲突 |
| 70-100 | 🔴 高危 | 配置文件或核心文件冲突，需协调 |

**高风险文件：**
- `pom.xml` - Maven依赖
- `application*.yml` - Spring配置
- `*Service.java` - 业务逻辑
- `*Controller.java` - API端点
- `*mapper*.xml` - MyBatis映射

## 📦 代码合并流程

### 方式一：使用自动化脚本（推荐）

```bash
cd /Users/luoxun/dev/ads/server/ads
./scripts/sync-worktrees.sh
```

脚本会引导你：
1. 检查所有 worktree 状态
2. 提交所有改动
3. 合并到 main 分支
4. 同步 main 到各分支
5. 推送到远程

### 方式二：手动合并

```bash
# 1. 各窗口提交改动
cd ads-api && git add . && git commit -m "feat: API改动"
cd ads-service && git add . && git commit -m "feat: Service改动"
cd ads-config && git add . && git commit -m "feat: Config改动"

# 2. 在主目录合并
cd ads
git checkout main
git merge feature/api-layer
git merge feature/service-layer
git merge feature/config-layer

# 3. 推送
git push origin main

# 4. 同步回各分支（可选）
cd ads-api && git merge main
cd ads-service && git merge main
cd ads-config && git merge main
```

## ⚠️ 冲突处理

如果出现冲突：

```bash
# Git会标记冲突文件
git status

# 编辑冲突文件，找到冲突标记：
<<<<<<< HEAD
你的改动
=======
其他分支的改动
>>>>>>> feature/service-layer

# 手动解决冲突后
git add <冲突文件>
git commit -m "merge: 解决冲突"
```

## 💡 最佳实践

### 1. 避免冲突的关键

- ✅ **明确分工**：每个窗口专注不同模块
- ✅ **频繁同步**：每2-3小时运行一次冲突检测
- ✅ **配置文件协调**：修改 `application.yml` 前通知其他窗口
- ✅ **提前预检**：合并前运行 `--full` 检测

### 2. 常见陷阱

- ❌ 多个窗口同时修改 `pom.xml`
- ❌ 多个窗口修改同一个 Service 类
- ❌ 忘记提交就切换分支
- ❌ 长时间不同步（超过半天）

### 3. 推荐工作节奏

```
09:00 - 开始工作，各窗口 git pull
       ↓
11:00 - 第一次同步检查
       ↓
14:00 - 午后同步检查
       ↓
17:00 - 下班前合并到 main
       ↓
17:30 - 推送到远程，各分支同步
```

## 🛠️ 常用命令

```bash
# 查看所有 worktree
git worktree list

# 查看某个分支的改动
git log feature/api-layer --oneline -5

# 查看两个分支的差异
git diff feature/api-layer..feature/service-layer

# 查看哪些文件会冲突（dry-run）
git merge --no-commit --no-ff feature/api-layer
git merge --abort  # 取消预检

# 删除 worktree
git worktree remove ads-api
git branch -D feature/api-layer

# 切换到其他分支查看（在任一 worktree 中）
git show feature/service-layer:rtb/pom.xml
```

## 📊 监控仪表板

运行实时监控，在后台保持一个终端：

```bash
# 终端4 - 监控
cd /Users/luoxun/dev/ads/server/ads
./scripts/conflict-detector.sh --watch
```

这样可以随时看到：
- 各 worktree 的改动状态
- 实时冲突警报
- 风险评分变化

## 🆘 故障排除

### 问题1：提交失败 "detached HEAD"

```bash
# 切换回正确的分支
git checkout feature/api-layer
```

### 问题2：合并时说 "refusing to merge unrelated histories"

```bash
# 添加 --allow-unrelated-histories
git merge feature/api-layer --allow-unrelated-histories
```

### 问题3：worktree 被锁定

```bash
# 删除锁定文件
rm .git/worktrees/ads-api/locked
```

### 问题4：文件改动丢失

```bash
# 查看 reflog 找回
git reflog
git reset --hard HEAD@{n}
```

## 📚 进阶技巧

### 1. 跨 worktree 查看代码

```bash
# 在 ads-api 中查看 ads-service 的代码
cd ads-api
git show feature/service-layer:rtb/src/main/java/com/example/springbootscaffold/service/SspService.java
```

### 2. 部分文件合并

```bash
# 只合并某个文件
git checkout feature/api-layer -- application.yml
```

### 3. 临时切换分支（stash）

```bash
# 暂存当前改动
git stash push -m "临时保存"

# 切换到其他分支查看
git checkout feature/service-layer

# 切回来恢复
git checkout feature/api-layer
git stash pop
```

## 🎯 总结

使用 Git Worktrees + 智能冲突检测器，你可以：

- ✅ 3个 Claude Code 窗口并行工作
- ✅ 实时监控文件冲突
- ✅ 智能风险评分
- ✅ 自动化合并流程
- ✅ 零学习成本（脚本引导）

**一句话原则：**
> 各自开发，频繁检测，合并前预检，冲突立即解决

---

**需要帮助？**
- 查看脚本帮助：`./scripts/conflict-detector.sh --help`
- 查看 worktree 文档：`git worktree --help`
