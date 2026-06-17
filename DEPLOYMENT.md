# 部署指南

## 快速开始

### 方式一：Docker Compose 部署（推荐）

1. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

2. **启动服务**
```bash
docker-compose up -d
```

3. **初始化数据库**
```bash
docker-compose exec app flask db upgrade
docker-compose exec app python init_data.py
```

4. **访问应用**
打开浏览器访问 `http://localhost:5000`

### 方式二：本地部署

1. **安装依赖**
```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件
```

3. **初始化数据库**
```bash
flask db upgrade
python init_data.py
```

4. **启动应用**
```bash
# 开发模式
flask run

# 生产模式
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 run:app
```

## 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SECRET_KEY` | Flask密钥（必须修改） | 自动生成 |
| `DATABASE_URL` | 数据库连接字符串 | mysql+pymysql://root:password@localhost/career_advisor |
| `OPENAI_API_KEY` | OpenAI API密钥 | 无 |
| `OPENAI_BASE_URL` | OpenAI API地址 | https://api.openai.com/v1 |
| `OPENAI_MODEL` | 使用的模型 | gpt-3.5-turbo |
| `CHROMA_PERSIST_DIR` | ChromaDB数据目录 | ./chroma_data |
| `FLASK_DEBUG` | 调试模式 | false |
| `LOG_LEVEL` | 日志级别 | INFO |
| `LOG_FILE` | 日志文件路径 | app.log |
| `PORT` | 应用端口 | 5000 |

## 生产环境配置建议

### 1. 安全配置
- 修改 `SECRET_KEY` 为随机字符串
- 使用强密码的数据库用户
- 启用 HTTPS
- 配置防火墙

### 2. 性能优化
- 增加 `gunicorn` workers 数量（建议 CPU核心数 * 2 + 1）
- 配置 Nginx 反向代理
- 启用 Redis 缓存（可选）

### 3. 监控
- 查看日志：`tail -f app.log`
- 监控进程：`docker-compose logs -f`

## Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    location /static {
        alias /path/to/your/app/static;
        expires 1d;
    }
}
```

## 常见问题

### Q: 数据库连接失败
A: 检查 `DATABASE_URL` 配置，确保数据库服务已启动

### Q: ChromaDB 初始化失败
A: 检查 `CHROMA_PERSIST_DIR` 目录权限

### Q: 端口被占用
A: 修改 `PORT` 环境变量或停止占用端口的进程

---

## 备份与恢复

### 备份数据库

```bash
# 手动备份
python scripts/backup.py

# 定时备份（添加到crontab）
# 每天凌晨2点备份
0 2 * * * cd /path/to/project && python scripts/backup.py
```

### 恢复数据库

```bash
# 查看可用备份
python scripts/restore.py

# 按提示选择要恢复的备份
```

### 备份策略建议

- 每天自动备份一次
- 保留最近7天的备份
- 定期将备份文件同步到远程存储
- 恢复前先备份当前数据

---

## 监控与健康检查

### 健康检查端点

```bash
# 检查API状态
curl http://localhost:5000/api/test

# 完整健康检查
python scripts/healthcheck.py
```

### 监控指标

- API响应时间
- 数据库连接状态
- ChromaDB状态
- 系统资源使用

---

## 日志管理

### 日志位置

- 应用日志：`logs/app.log`
- Nginx日志：`/var/log/nginx/`
- Docker日志：`docker-compose logs`

### 日志轮转

日志文件会自动轮转，保留最近5个备份，每个最大10MB。

---

## 安全建议

1. **修改默认密码**：数据库、管理员账户
2. **启用HTTPS**：配置SSL证书
3. **限制访问**：配置防火墙规则
4. **定期更新**：保持依赖包最新
5. **监控告警**：配置异常告警
