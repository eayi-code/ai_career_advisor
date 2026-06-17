#!/bin/bash
# Cloudflare Tunnel 配置脚本

set -e

echo "========================================="
echo "  Cloudflare Tunnel 配置"
echo "========================================="
echo ""

# 检查是否已登录
if ! cloudflared tunnel list &> /dev/null; then
    echo "请先登录Cloudflare："
    echo "  cloudflared tunnel login"
    echo ""
    echo "登录后会打开浏览器，选择你的域名"
    exit 1
fi

# 创建隧道
TUNNEL_NAME="career-advisor"
echo "[1/4] 创建隧道: $TUNNEL_NAME"

if cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
    echo "  ✓ 隧道已存在"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
else
    cloudflared tunnel create "$TUNNEL_NAME"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    echo "  ✓ 隧道创建成功"
fi

echo "  隧道ID: $TUNNEL_ID"

# 获取域名
echo ""
echo "[2/4] 配置域名"
read -p "请输入你的域名 (例如: career.yourdomain.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "  使用默认子域名: $TUNNEL_NAME.trycloudflare.com"
    DOMAIN="$TUNNEL_NAME.trycloudflare.com"
fi

# 配置DNS
echo ""
echo "[3/4] 配置DNS路由"
cloudflared tunnel route dns "$TUNNEL_NAME" "$DOMAIN"
echo "  ✓ DNS配置完成"

# 创建配置文件
echo ""
echo "[4/4] 创建配置文件"
CONFIG_DIR="$HOME/.cloudflared"
mkdir -p "$CONFIG_DIR"

cat > "$CONFIG_DIR/config.yml" << EOF
tunnel: $TUNNEL_ID
credentials-file: $CONFIG_DIR/$TUNNEL_ID.json

ingress:
  - hostname: $DOMAIN
    service: http://localhost:5000
    originRequest:
      noTLSVerify: true
  - service: http_status:404
EOF

echo "  ✓ 配置文件创建完成: $CONFIG_DIR/config.yml"

echo ""
echo "========================================="
echo "  配置完成！"
echo "========================================="
echo ""
echo "启动隧道："
echo "  cloudflared tunnel run $TUNNEL_NAME"
echo ""
echo "设置开机自启："
echo "  sudo cloudflared service install"
echo "  sudo systemctl enable cloudflared"
echo "  sudo systemctl start cloudflared"
echo ""
echo "访问地址："
echo "  https://$DOMAIN"
echo ""
echo "========================================="
