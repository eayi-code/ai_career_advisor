#!/bin/bash
# CareerAI 一键部署脚本
# 在小主机上执行：curl -sL https://raw.githubusercontent.com/eayi-code/ai_career_advisor/main/scripts/deploy.sh | bash

set -e

echo "========================================="
echo "  CareerAI 一键部署脚本"
echo "========================================="
echo ""

# 安装Docker
echo "[1/5] 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "  [OK] Docker安装完成"
else
    echo "  [OK] Docker已安装"
fi

# 安装Docker Compose
echo "[2/5] 安装Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo apt install docker-compose -y
    echo "  [OK] Docker Compose安装完成"
else
    echo "  [OK] Docker Compose已安装"
fi

# 克隆项目
echo "[3/5] 克隆项目..."
PROJECT_DIR="$HOME/ai_career_advisor"
if [ ! -d "$PROJECT_DIR" ]; then
    git clone https://github.com/eayi-code/ai_career_advisor.git "$PROJECT_DIR"
    echo "  [OK] 项目克隆完成"
else
    cd "$PROJECT_DIR" && git pull
    echo "  [OK] 项目已更新"
fi

cd "$PROJECT_DIR"

# 配置环境变量
echo "[4/5] 配置环境变量..."
if [ ! -f ".env" ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
FLASK_DEBUG=false
DATABASE_URL=mysql+pymysql://root:password@db:3306/career_advisor
OPENAI_API_KEY=sk-请填入你的API密钥
OPENAI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
OPENAI_MODEL=mimo-v2.5-pro
CHROMA_PERSIST_DIR=/app/chroma_data
LOG_LEVEL=INFO
EOF
    echo "  [OK] 环境变量配置完成"
    echo ""
    echo "  *** 重要 ***"
    echo "  请编辑 ~/ai_career_advisor/.env 填入你的OpenAI API密钥："
    echo "  nano ~/ai_career_advisor/.env"
    echo ""
else
    echo "  [OK] 环境变量已存在"
fi

# 创建必要目录
mkdir -p backups logs

# 启动服务
echo "[5/5] 启动服务..."
docker-compose -f docker-compose.lan.yml up -d
echo "  [OK] 服务启动完成"

# 获取IP地址
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
echo "  访问地址: http://${IP_ADDRESS}:5000"
echo ""
echo "  手机访问："
echo "    1. 确保手机和电脑在同一WiFi"
echo "    2. 浏览器访问上面的地址"
echo "    3. 可添加到主屏幕作为APP使用"
echo ""
echo "  常用命令："
echo "    查看日志: docker-compose -f docker-compose.lan.yml logs -f"
echo "    停止服务: docker-compose -f docker-compose.lan.yml down"
echo "    重启服务: docker-compose -f docker-compose.lan.yml restart"
echo "    更新项目: cd ~/ai_career_advisor && git pull && docker-compose -f docker-compose.lan.yml up -d --build"
echo ""
echo "========================================="
