# Deepin + Cloudflare Tunnel 部署指南

## 前置条件

1. **Deepin系统**（基于Debian）
2. **Cloudflare账号**（免费注册：https://dash.cloudflare.com/sign-up）
3. **一个域名**（可选，Cloudflare提供免费子域名）

## 快速部署

### 步骤1：安装依赖

```bash
# 下载项目
git clone <your-repo-url> ~/ai_career_advisor
cd ~/ai_career_advisor

# 运行部署脚本
chmod +x scripts/deploy_deepin.sh
./scripts/deploy_deepin.sh
```

### 步骤2：配置环境变量

```bash
nano ~/ai_career_advisor/.env
```

填入以下内容：
```env
SECRET_KEY=your-random-secret-key-here
DATABASE_URL=mysql+pymysql://root:password@db:3306/career_advisor
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
```

### 步骤3：启动服务

```bash
cd ~/ai_career_advisor
docker-compose up -d
```

### 步骤4：配置Cloudflare Tunnel

```bash
# 登录Cloudflare
cloudflared tunnel login

# 配置隧道
chmod +x scripts/setup_cloudflare.sh
./scripts/setup_cloudflare.sh
```

### 步骤5：设置开机自启

```bash
# 复制服务文件
sudo cp scripts/cloudflared.service /etc/systemd/system/

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

## 验证部署

```bash
# 检查服务状态
docker-compose ps

# 检查Cloudflare Tunnel状态
sudo systemctl status cloudflared

# 访问测试
curl https://your-domain.com/api/test
```

## 常见问题

### Q: 如何获取免费域名？

A: 在Cloudflare注册账号后，可以购买一个域名（约$10/年），或者使用Cloudflare提供的免费子域名。

### Q: 如何查看日志？

```bash
# 应用日志
docker-compose logs -f app

# Cloudflare日志
sudo journalctl -u cloudflared -f
```

### Q: 如何更新项目？

```bash
cd ~/ai_career_advisor
git pull
docker-compose down
docker-compose up -d --build
```

### Q: 如何备份数据？

```bash
# 手动备份
python scripts/backup.py

# 查看备份
ls -la backups/
```

## 网络架构

```
用户浏览器
    ↓
Cloudflare CDN (HTTPS)
    ↓
Cloudflare Tunnel
    ↓
你的Deepin小主机 (localhost:5000)
    ↓
Docker容器 (Flask + MySQL + ChromaDB)
```

## 费用说明

| 项目 | 费用 |
|------|------|
| Cloudflare账号 | 免费 |
| Cloudflare Tunnel | 免费 |
| 域名 | ~$10/年（可选） |
| 电费 | ~¥15/月（135W电源） |
| **总计** | **0-¥15/月** |
