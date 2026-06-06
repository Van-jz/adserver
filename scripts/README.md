# 日志处理和URL转换自动化系统

## 系统概述

本系统实现了从日志文件中提取URL、应用频率控制、并执行curl请求的完整自动化流程。

### 主要功能

1. **增量日志处理** - 只处理新增的日志数据，避免重复处理
2. **频率控制** - 严格控制URL处理频率（总体20%，每个pixel_id每天最多10个）
3. **状态管理** - 跟踪处理进度，支持断点续传
4. **完整日志** - 所有操作都有详细的日志记录

### 系统架构

```
Cron (定时执行)
  ↓
orchestrator.py (主编排器)
  ↓
  ├─> extract_log_incremental.py (提取新日志)
  │     └─> 输出: clicks_temp.txt
  ├─> url_frequency_controller.py (频率控制)
  │     └─> 输入: clicks_temp.txt
  │     └─> 输出: clicks.txt
  └─> convert_enhanced.py (执行curl请求)
        └─> 输入: clicks.txt
        └─> 输出: convert_results.log
```

## 文件说明

### 核心脚本

1. **orchestrator.py** - 主编排脚本，协调所有步骤
2. **extract_log_incremental.py** - 增量日志提取脚本
3. **url_frequency_controller.py** - URL频率控制脚本
4. **convert_enhanced.py** - URL转换和curl请求脚本

### 配置和状态文件

1. **orchestrator_config.json** - 主配置文件
2. **orchestrator_state.json** - 运行状态（自动生成）
3. **frequency_state.json** - 频率控制状态（自动生成）
4. **pixelid_token.txt** - pixel_id和token的映射关系（需要手动维护）

### 数据文件

1. **clicks_temp.txt** - 临时提取的URL（中间文件）
2. **clicks.txt** - 经过频率控制后的URL（输入到convert）

### 日志文件

1. **orchestrator.log** - 主编排日志
2. **convert_results.log** - curl请求详细日志

## 部署步骤

### 1. 准备环境

```bash
# 安装Python 3（如果未安装）
sudo yum install python3

# 验证Python版本
python3 --version
```

### 2. 部署脚本

```bash
# 创建脚本目录
mkdir -p /home/home/admin/scripts
cd /home/home/admin/scripts

# 复制所有脚本文件到此目录
# - orchestrator.py
# - extract_log_incremental.py
# - url_frequency_controller.py
# - convert_enhanced.py
# - setup_cron.sh
# - orchestrator_config.json

# 设置执行权限
chmod +x orchestrator.py extract_log_incremental.py url_frequency_controller.py convert_enhanced.py setup_cron.sh
```

### 3. 准备配置文件

编辑 `orchestrator_config.json`：

```json
{
  "log_dir": "/home/home/admin/data/info",
  "log_prefix": "info.prod0320",
  "pixelid_token_file": "/home/home/admin/scripts/pixelid_token.txt",
  "clicks_temp_file": "/home/home/admin/scripts/clicks_temp.txt",
  "clicks_file": "/home/home/admin/scripts/clicks.txt",
  "frequency_state_file": "/home/home/admin/scripts/frequency_state.json",
  "state_file": "/home/home/admin/scripts/orchestrator_state.json",
  "orchestrator_log": "/home/home/admin/scripts/orchestrator.log",
  "convert_log": "/home/home/admin/scripts/convert_results.log",
  "total_ratio": 0.2,
  "max_per_pixel_id": 10,
  "sleep_seconds": 5,
  "scripts_dir": "/home/home/admin/scripts"
}
```

### 4. 准备 pixelid_token.txt

创建 `pixelid_token.txt` 文件，格式如下：

```
pixel_id_1 token_1
pixel_id_2 token_2
pixel_id_3 token_3
```

每行一个映射关系，pixel_id和token之间用空格分隔。

### 5. 测试运行

```bash
cd /home/home/admin/scripts

# 手动运行一次测试
python3 orchestrator.py --config orchestrator_config.json

# 查看日志
tail -f orchestrator.log
```

### 6. 配置Crontab

使用提供的脚本自动配置：

```bash
./setup_cron.sh
```

或手动配置：

```bash
# 编辑crontab
crontab -e

# 添加以下行（每5分钟执行一次）
*/5 * * * * cd /home/home/admin/scripts && python3 orchestrator.py >> logs/cron.log 2>&1
```

## 配置说明

### orchestrator_config.json 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| log_dir | 日志文件目录 | /home/home/admin/data/info |
| log_prefix | 日志文件前缀 | info.prod0320 |
| total_ratio | URL总体处理比例 | 0.2 (20%) |
| max_per_pixel_id | 每个pixel_id每天最大处理数 | 10 |
| sleep_seconds | curl请求间隔（秒） | 5 |

## 工作流程详解

### 步骤1: 增量日志提取

`extract_log_incremental.py` 从上次处理位置继续读取日志文件：

1. 读取上次处理的文件位置（从状态文件）
2. 从该位置开始解析新的日志行
3. 提取包含 click_id 和 pixel_id 的 URL
4. 只保留 pixel_id 在白名单中的 URL
5. 输出到 `clicks_temp.txt`
6. 更新处理位置

**关键特性：**
- 支持日志文件滚动（part_0 到 part_1）
- 不会重复处理已处理的数据
- 不会清空输出文件（追加模式）

### 步骤2: 频率控制

`url_frequency_controller.py` 应用两层频率限制：

1. **总体比例限制**：使用确定性哈希函数，只处理20%的URL
2. **pixel_id限制**：每个pixel_id每天最多处理10个URL

**关键特性：**
- 使用MD5哈希保证同一URL每次运行结果一致
- 按日期自动重置计数器
- 状态持久化到 `frequency_state.json`

### 步骤3: 执行curl请求

`convert_enhanced.py` 对每个URL执行curl请求：

1. 第一个请求：EVENT_COMPLETE_REGISTRATION（必发）
2. 第二个请求：EVENT_PURCHASE（50%概率）
3. 记录详细的请求和响应日志

**关键特性：**
- 完整的日志记录到 `convert_results.log`
- 支持自定义请求间隔
- 错误处理和重试机制

## 监控和维护

### 查看日志

```bash
# 主编排日志
tail -f /home/home/admin/scripts/orchestrator.log

# curl请求日志
tail -f /home/home/admin/scripts/convert_results.log

# cron执行日志
tail -f /home/home/admin/scripts/logs/cron.log
```

### 查看状态

```bash
# 查看当前处理位置
cat /home/home/admin/scripts/orchestrator_state.json

# 查看频率控制状态
cat /home/home/admin/scripts/frequency_state.json
```

### 重置状态

如果需要从头开始处理：

```bash
# 删除状态文件
rm /home/home/admin/scripts/orchestrator_state.json
rm /home/home/admin/scripts/frequency_state.json

# 下次运行会自动从头开始
```

### 手动触发处理

```bash
cd /home/home/admin/scripts
python3 orchestrator.py
```

## 故障排查

### 问题1: 没有提取到URL

**检查：**
1. 日志文件路径是否正确
2. pixelid_token.txt 是否包含有效的pixel_id
3. 日志文件是否有新数据

**解决：**
```bash
# 检查日志文件
ls -lh /home/home/admin/data/info/

# 检查pixelid_token.txt
cat pixelid_token.txt
```

### 问题2: curl请求失败

**检查：**
1. 网络连接是否正常
2. token是否有效
3. 请求URL格式是否正确

**解决：**
```bash
# 查看详细错误
tail -100 convert_results.log

# 手动测试一个URL
curl -v "https://www.adsnebula.com/log/common/gapi?..."
```

### 问题3: 频率控制不生效

**检查：**
1. frequency_state.json 的日期是否正确
2. 配置文件中的 total_ratio 和 max_per_pixel_id 是否正确

**解决：**
```bash
# 查看频率控制状态
cat frequency_state.json

# 重新测试频率控制
python3 url_frequency_controller.py --input clicks_temp.txt --output clicks.txt
```

## 重要注意事项

1. **日志文件路径映射**：生产环境容器将 `/data/disk0/home` 映射到 `/home`，请确保路径正确

2. **pixelid_token.txt 安全**：此文件包含敏感的 token 信息，请妥善保管

3. **磁盘空间**：定期清理旧的日志文件和临时文件

4. **频率限制**：
   - 总体20%是基于提取出的URL数量，不是原始日志数量
   - 每个pixel_id每天10个是累计值，会在每天0点自动重置

5. **确定性处理**：系统使用哈希函数确保同一个URL每次运行都得到相同的结果，这是为了避免重复处理

## 性能优化建议

1. **调整执行频率**：根据日志增长速度调整cron执行频率
2. **调整sleep时间**：根据服务器负载调整curl请求间隔
3. **批量处理**：如果URL数量很大，可以分批处理

## 升级和维护

### 更新脚本

```bash
# 备份当前版本
cp orchestrator.py orchestrator.py.bak

# 更新新版本
# 复制新的脚本文件

# 测试新版本
python3 orchestrator.py --config orchestrator_config.json
```

### 备份状态

```bash
# 定期备份状态文件
cp orchestrator_state.json orchestrator_state.json.$(date +%Y%m%d)
cp frequency_state.json frequency_state.json.$(date +%Y%m%d)
```

## 联系支持

如有问题，请查看日志文件并联系技术支持团队。
