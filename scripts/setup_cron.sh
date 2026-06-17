#!/bin/bash
# 数据库备份定时任务配置脚本
# 用于Linux/Docker环境

# 备份目录
BACKUP_DIR="/app/backups"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 添加crontab任务
(
    # 每天凌晨2点备份
    echo "0 2 * * * cd /app && python scripts/backup.py >> /app/logs/backup.log 2>&1"
    
    # 每周日凌晨3点清理7天前的备份
    echo "0 3 * * 0 find $BACKUP_DIR -type f -mtime +7 -delete >> /app/logs/cleanup.log 2>&1"
) | crontab -

echo "✓ 定时任务配置完成"
echo ""
echo "已配置的任务："
crontab -l
