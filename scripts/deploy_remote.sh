#!/bin/bash
# 一键部署脚本 - 在小主机上执行

set -e

echo "========================================="
echo "  CareerAI 一键部署脚本"
echo "========================================="
echo ""

# 更新系统
echo "[1/7] 更新系统..."
sudo apt update -y

# 安装Docker
echo "[2/7] 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "  ✓ Docker安装完成"
else
    echo "  ✓ Docker已安装"
fi

# 安装Git
echo "[3/7] 安装Git..."
if ! command -v git &> /dev/null; then
    sudo apt install git -y
    echo "  ✓ Git安装完成"
else
    echo "  ✓ Git已安装"
fi

# 克隆项目
echo "[4/7] 克隆项目..."
PROJECT_DIR="$HOME/ai_career_advisor"
if [ ! -d "$PROJECT_DIR" ]; then
    git clone https://github.com/你的用户名/你的仓库.git "$PROJECT_DIR"
    echo "  ✓ 项目克隆完成"
else
    echo "  ✓ 项目目录已存在"
fi

cd "$PROJECT_DIR"

# 配置环境变量
echo "[5/7] 配置环境变量..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Flask配置
SECRET_KEY=$(openssl rand -hex 32)
FLASK_DEBUG=false

# 数据库配置
DATABASE_URL=mysql+pymysql://root:password@db:3306/career_advisor

# OpenAI API配置
OPENAI_API_KEY=你的API密钥
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# ChromaDB配置
CHROMA_PERSIST_DIR=/app/chroma_data

# 日志配置
LOG_LEVEL=INFO
EOF
    echo "  ✓ 环境变量配置完成"
    echo "  ⚠ 请编辑 ~/ai_career_advisor/.env 填入OpenAI API密钥"
else
    echo "  ✓ 环境变量已配置"
fi

# 创建必要目录
echo "[6/7] 创建目录..."
mkdir -p backups logs
echo "  ✓ 目录创建完成"

# 启动服务
echo "[7/7] 启动服务..."
docker-compose -f docker-compose.lan.yml up -d
echo "  ✓ 服务启动完成"

# 获取IP地址
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
echo "访问地址: http://$IP_ADDRESS:5000"
echo ""
echo "手机访问："
echo "  1. 确保手机和电脑在同一WiFi"
echo "  2. 浏览器访问上面的地址"
echo ""
echo "常用命令："
echo "  查看日志: docker-compose -f docker-compose.lan.yml logs -f"
echo "  停止服务: docker-compose -f docker-compose.lan.yml down"
echo "  重启服务: docker-compose -f docker-compose.lan.yml restart"
echo ""
echo "========================================="
