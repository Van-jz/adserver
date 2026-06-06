#!/bin/bash
# Crontab 设置脚本
# 用于配置定期执行 orchestrator.py 的 cron 任务

# 脚本目录（请修改为实际路径）
SCRIPTS_DIR="/path/to/your/scripts"

# Python3 路径
PYTHON3=$(which python3)

# 日志目录
LOG_DIR="$SCRIPTS_DIR/logs"

# 创建日志目录
mkdir -p "$LOG_DIR"

echo "========================================"
echo "Crontab 设置脚本"
echo "========================================"
echo ""
echo "脚本目录: $SCRIPTS_DIR"
echo "Python3 路径: $PYTHON3"
echo "日志目录: $LOG_DIR"
echo ""

# 检查 orchestrator_unified.py 是否存在
if [ ! -f "$SCRIPTS_DIR/orchestrator_unified.py" ]; then
    echo "错误: 找不到 orchestrator_unified.py 文件"
    echo "请确保已将所有脚本文件复制到 $SCRIPTS_DIR"
    exit 1
fi

# 显示现有的 crontab
echo "当前的 crontab 配置:"
echo "----------------------------------------"
crontab -l 2>/dev/null || echo "(无)"
echo "----------------------------------------"
echo ""

# 提示用户选择执行频率
echo "请选择执行频率:"
echo "1) 每 5 分钟执行一次"
echo "2) 每 10 分钟执行一次"
echo "3) 每 15 分钟执行一次"
echo "4) 每 30 分钟执行一次"
echo "5) 每小时执行一次"
echo "6) 自定义"
echo ""
read -p "请选择 [1-6]: " choice

case $choice in
    1)
        CRON_SCHEDULE="*/5 * * * *"
        ;;
    2)
        CRON_SCHEDULE="*/10 * * * *"
        ;;
    3)
        CRON_SCHEDULE="*/15 * * * *"
        ;;
    4)
        CRON_SCHEDULE="*/30 * * * *"
        ;;
    5)
        CRON_SCHEDULE="0 * * * *"
        ;;
    6)
        read -p "请输入 cron 表达式 (例如: */5 * * * *): " CRON_SCHEDULE
        ;;
    *)
        echo "无效的选择"
        exit 1
        ;;
esac

# 生成 crontab 条目
CRON_ENTRY="$CRON_SCHEDULE cd $SCRIPTS_DIR && $PYTHON3 orchestrator_unified.py >> $LOG_DIR/cron.log 2>&1"

echo ""
echo "将添加以下 crontab 条目:"
echo "----------------------------------------"
echo "$CRON_ENTRY"
echo "----------------------------------------"
echo ""
read -p "确认添加? [y/N]: " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "已取消"
    exit 0
fi

# 添加到 crontab
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Crontab 设置成功!"
    echo ""
    echo "新的 crontab 配置:"
    echo "----------------------------------------"
    crontab -l
    echo "----------------------------------------"
    echo ""
    echo "注意事项:"
    echo "1. 请确保 orchestrator_config.json 中的配置正确"
    echo "2. 请确保 pixelid_token.txt 文件存在并包含正确的数据"
    echo "3. 日志文件将保存在: $LOG_DIR/cron.log"
    echo "4. 可以使用 'tail -f $LOG_DIR/cron.log' 查看实时日志"
    echo "5. 要删除此任务，请运行: crontab -e，然后删除对应的行"
    echo ""
else
    echo "✗ Crontab 设置失败"
    exit 1
fi
