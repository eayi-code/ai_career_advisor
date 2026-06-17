#!/bin/bash
# Deepin系统部署脚本
# 用于安装Docker和Cloudflare Tunnel

set -e

echo "========================================="
echo "  AI职业决策系统 - Deepin部署脚本"
echo "========================================="
echo ""

# 更新系统
echo "[1/6] 更新系统..."
sudo apt update && sudo apt upgrade -y

# 安装Docker
echo "[2/6] 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "  ✓ Docker安装完成"
else
    echo "  ✓ Docker已安装"
fi

# 安装Docker Compose
echo "[3/6] 安装Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo apt install docker-compose -y
    echo "  ✓ Docker Compose安装完成"
else
    echo "  ✓ Docker Compose已安装"
fi

# 安装Cloudflare Tunnel
echo "[4/6] 安装Cloudflare Tunnel..."
if ! command -v cloudflared &> /dev/null; then
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    sudo dpkg -i cloudflared-linux-amd64.deb
    rm cloudflared-linux-amd64.deb
    echo "  ✓ Cloudflare Tunnel安装完成"
else
    echo "  ✓ Cloudflare Tunnel已安装"
fi

# 创建项目目录
echo "[5/6] 配置项目..."
PROJECT_DIR="$HOME/ai_career_advisor"
if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
    echo "  ✓ 项目目录创建完成"
else
    echo "  ✓ 项目目录已存在"
fi

# 创建环境变量文件
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cat > "$PROJECT_DIR/.env" << 'EOF'
# Flask配置
SECRET_KEY=your-secret-key-here-change-in-production
FLASK_DEBUG=false
PORT=5000

# 数据库配置
DATABASE_URL=mysql+pymysql://root:password@db:3306/career_advisor

# OpenAI API配置
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# ChromaDB配置
CHROMA_PERSIST_DIR=/app/chroma_data

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log
EOF
    echo "  ✓ 环境变量文件创建完成"
    echo "  ⚠ 请编辑 $PROJECT_DIR/.env 填入真实配置"
else
    echo "  ✓ 环境变量文件已存在"
fi

# 创建备份目录
mkdir -p "$PROJECT_DIR/backups"
mkdir -p "$PROJECT_DIR/logs"

echo ""
echo "[6/6] 部署完成！"
echo ""
echo "========================================="
echo "  下一步操作"
echo "========================================="
echo ""
echo "1. 配置环境变量："
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. 上传项目文件到："
echo "   $PROJECT_DIR/"
echo ""
echo "3. 启动服务："
echo "   cd $PROJECT_DIR && docker-compose up -d"
echo ""
echo "4. 配置Cloudflare Tunnel："
echo "   cloudflared tunnel login"
echo "   cloudflared tunnel create career-advisor"
echo "   cloudflared tunnel route dns career-advisor your-domain.com"
echo "   cloudflared tunnel run career-advisor"
echo ""
echo "5. 设置开机自启："
echo "   sudo systemctl enable cloudflared"
echo "   sudo systemctl start cloudflared"
echo ""
echo "========================================="
