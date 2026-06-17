#!/bin/bash
# 一键更新部署脚本
# 用于Deepin小主机

set -e

echo "========================================="
echo "  CareerAI 一键更新脚本"
echo "========================================="
echo ""

PROJECT_DIR="$HOME/ai_career_advisor"

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# 拉取最新代码
echo "[1/3] 拉取最新代码..."
git pull origin main
echo "  ✓ 代码更新完成"

# 停止服务
echo "[2/3] 停止服务..."
docker-compose down
echo "  ✓ 服务已停止"

# 重新构建并启动
echo "[3/3] 重新部署..."
docker-compose up -d --build
echo "  ✓ 部署完成"

echo ""
echo "========================================="
echo "  更新完成！"
echo "========================================="
echo ""
echo "访问地址: https://your-domain.com"
echo ""
echo "查看日志: docker-compose logs -f"
echo ""
