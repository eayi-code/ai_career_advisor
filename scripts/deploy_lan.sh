#!/bin/bash
# 局域网部署脚本（简化版）

set -e

echo "========================================="
echo "  CareerAI 局域网部署脚本"
echo "========================================="
echo ""

# 安装Docker
echo "[1/4] 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "  ✓ Docker安装完成"
    echo "  ⚠ 请注销并重新登录以使Docker权限生效"
else
    echo "  ✓ Docker已安装"
fi

# 克隆项目
echo "[2/4] 克隆项目..."
PROJECT_DIR="$HOME/ai_career_advisor"
if [ ! -d "$PROJECT_DIR" ]; then
    read -p "请输入Git仓库地址: " GIT_REPO
    git clone "$GIT_REPO" "$PROJECT_DIR"
    echo "  ✓ 项目克隆完成"
else
    echo "  ✓ 项目目录已存在"
fi

cd "$PROJECT_DIR"

# 配置环境变量
echo "[3/4] 配置环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    
    # 生成随机SECRET_KEY
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/your-secret-key-here-change-in-production/$SECRET_KEY/" .env
    
    echo "  ✓ 环境变量配置完成"
    echo "  ⚠ 请编辑 .env 文件填入OpenAI API密钥"
    echo "    nano $PROJECT_DIR/.env"
else
    echo "  ✓ 环境变量已配置"
fi

# 启动服务
echo "[4/4] 启动服务..."
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
