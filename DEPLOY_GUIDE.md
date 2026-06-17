# CareerAI 部署与运维指南

## 一、核心原理

### 1.1 Docker 是什么

**一句话解释**：Docker 是一个"打包工具"，把你的代码和所有依赖打包成一个"集装箱"，在任何地方都能运行。

**生活类比**：

| 概念 | 类比 | 说明 |
|------|------|------|
| Docker 镜像 | APP安装包 | 包含程序和所有依赖 |
| Docker 容器 | 手机上运行的APP | 镜像运行后的实例 |
| Dockerfile | APP的构建说明 | 告诉Docker怎么打包 |
| docker-compose.yml | 多APP管理器 | 同时管理多个容器 |

**核心价值**：

```
传统部署：                          Docker部署：
安装Python                          docker-compose up -d
    ↓                                   ↓
安装依赖库                          自动完成所有安装
    ↓                                   ↓
安装MySQL                               ↓
    ↓                               一键启动所有服务
配置数据库
    ↓
启动服务
（容易出错，环境不一致）
```

### 1.2 Docker 架构

```
┌─────────────────────────────────────────┐
│           宿主机（你的小主机）            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ MySQL容器 │ │ Flask容器 │ │ Nginx容器│ │
│  │  :3306   │ │  :5000   │ │  :80     │ │
│  └──────────┘ └──────────┘ └──────────┘ │
│       ↑            ↑            ↑       │
│       └────────────┼────────────┘       │
│                    │                    │
│              Docker Network             │
└─────────────────────────────────────────┘
```

**关键点**：
- 每个容器是独立的"小电脑"
- 容器之间通过网络通信
- 容器挂了不影响宿主机
- 宿主机挂了容器也挂（共享内核）

### 1.3 docker-compose.yml 解读

```yaml
services:
  app:                    # 服务名：Flask应用
    build: .              # 用当前目录的Dockerfile构建
    ports:
      - "5000:5000"       # 端口映射：宿主机5000 → 容器5000
    environment:          # 环境变量（配置信息）
      - DATABASE_URL=...  # 数据库连接地址
    volumes:              # 数据持久化
      - chroma_data:/app/chroma_data  # 向量数据库数据
    depends_on:
      db:                 # 依赖MySQL服务
        condition: service_healthy  # MySQL健康后才启动

  db:                     # 服务名：MySQL数据库
    image: mysql:8.0      # 使用官方MySQL镜像
    volumes:
      - mysql_data:/var/lib/mysql  # 数据库数据持久化
```

**核心概念**：

| 配置项 | 作用 | 不配置的后果 |
|--------|------|--------------|
| `ports` | 端口映射 | 外部无法访问 |
| `environment` | 环境变量 | 应用无法连接数据库 |
| `volumes` | 数据持久化 | 容器重启数据丢失 |
| `depends_on` | 启动顺序 | 应用启动时数据库还没准备好 |
| `healthcheck` | 健康检查 | 不知道服务是否正常 |

---

## 二、部署流程

### 2.1 完整部署流程图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  本地开发    │ ──→ │  推送到Git   │ ──→ │  小主机拉取  │
│  修改代码    │     │  git push   │     │  git pull   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               ↓
                    ┌─────────────┐     ┌─────────────┐
                    │  访问测试    │ ←── │  启动服务    │
                    │  浏览器访问  │     │  docker up  │
                    └─────────────┘     └─────────────┘
```

### 2.2 关键命令

```bash
# 1. 构建并启动（首次部署）
sudo docker-compose -f docker-compose.lan.yml up -d --build

# 2. 查看运行状态
sudo docker-compose -f docker-compose.lan.yml ps

# 3. 查看日志
sudo docker-compose -f docker-compose.lan.yml logs -f

# 4. 停止服务
sudo docker-compose -f docker-compose.lan.yml down

# 5. 重启服务
sudo docker-compose -f docker-compose.lan.yml restart

# 6. 更新代码后重新部署
cd ~/ai_career_advisor
git pull
sudo docker-compose -f docker-compose.lan.yml up -d --build
```

### 2.3 数据持久化

**重要概念**：容器删除 ≠ 数据丢失

```yaml
volumes:
  mysql_data:      # MySQL数据（用户数据、对话历史）
  chroma_data:     # ChromaDB数据（向量记忆）
  app_logs:        # 应用日志
```

**数据位置**：

```bash
# 查看所有数据卷
docker volume ls

# 数据实际存储位置
/var/lib/docker/volumes/
```

**备份数据**：

```bash
# 备份MySQL
docker exec mysql_container mysqldump -u root -p career_advisor > backup.sql

# 恢复MySQL
docker exec -i mysql_container mysql -u root -p career_advisor < backup.sql
```

---

## 三、网络配置

### 3.1 局域网访问

```
手机 ──WiFi──→ 路由器 ──→ 小主机:5000
                           ↓
                      Docker容器
```

**前提条件**：
- 手机和小主机连接同一个WiFi
- 知道小主机的IP地址

**查看IP**：

```bash
# 小主机上执行
hostname -I
```

**访问地址**：

```
http://小主机IP:5000
```

### 3.2 内网穿透（Cloudflare Tunnel）

**目的**：让外网也能访问你的服务

```
外网用户 ──→ Cloudflare CDN ──→ Tunnel ──→ 你的小主机:5000
```

**优势**：
- 免费
- 不需要公网IP
- 自动HTTPS
- DDoS防护

**配置步骤**：

```bash
# 1. 安装cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# 2. 登录Cloudflare
cloudflared tunnel login
# 会打开浏览器，选择你的域名

# 3. 创建隧道
cloudflared tunnel create career-advisor

# 4. 配置路由
cloudflared tunnel route dns career-advisor your-domain.com

# 5. 创建配置文件
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: career-advisor
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: your-domain.com
    service: http://localhost:5000
  - service: http_status:404
EOF

# 6. 启动隧道
cloudflared tunnel run career-advisor

# 7. 设置开机自启
cloudflared service install
systemctl enable cloudflared
systemctl start cloudflared
```

**访问地址**：

```
https://your-domain.com
```

---

## 四、常用运维命令

### 4.1 Docker 命令

```bash
# 查看所有容器
docker ps -a

# 查看容器日志
docker logs <container_name>

# 进入容器
docker exec -it <container_name> bash

# 查看容器资源使用
docker stats

# 清理未使用的镜像
docker system prune
```

### 4.2 数据库操作

```bash
# 进入MySQL容器
docker exec -it <mysql_container> mysql -u root -p

# 查看数据库
SHOW DATABASES;

# 使用数据库
USE career_advisor;

# 查看表
SHOW TABLES;

# 备份数据库
docker exec <mysql_container> mysqldump -u root -p career_advisor > backup.sql

# 恢复数据库
docker exec -i <mysql_container> mysql -u root -p career_advisor < backup.sql
```

### 4.3 故障排查

```bash
# 查看容器状态
docker-compose -f docker-compose.lan.yml ps

# 查看容器日志
docker-compose -f docker-compose.lan.yml logs -f

# 重启服务
docker-compose -f docker-compose.lan.yml restart

# 重建服务
docker-compose -f docker-compose.lan.yml up -d --build

# 查看网络
docker network ls

# 查看数据卷
docker volume ls
```

---

## 五、求职技能点

### 5.1 可以写在简历上的技能

| 技能 | 说明 | 面试问题 |
|------|------|----------|
| Docker容器化 | 使用Docker部署Flask+MySQL应用 | Docker和虚拟机的区别？ |
| Docker Compose | 多容器编排和管理 | docker-compose.yml的作用？ |
| Nginx反向代理 | 负载均衡和静态文件服务 | 反向代理的原理？ |
| Linux运维 | 命令行操作、服务管理 | 如何查看日志？ |
| Git版本控制 | 代码管理和团队协作 | Git和SVN的区别？ |
| CI/CD | 持续集成/持续部署 | 什么是CI/CD？ |
| 内网穿透 | Cloudflare Tunnel配置 | 内网穿透的原理？ |
| 数据库管理 | MySQL备份恢复 | 如何备份数据库？ |

### 5.2 面试常见问题

**Q: Docker和虚拟机的区别？**

| 特性 | Docker | 虚拟机 |
|------|--------|--------|
| 启动速度 | 秒级 | 分钟级 |
| 资源占用 | 轻量 | 重量 |
| 隔离性 | 进程级 | 系统级 |
| 镜像大小 | MB级 | GB级 |
| 性能 | 接近原生 | 有损耗 |

**Q: Dockerfile的作用？**

```dockerfile
FROM python:3.11          # 基础镜像
WORKDIR /app              # 工作目录
COPY requirements.txt .   # 复制依赖文件
RUN pip install -r requirements.txt  # 安装依赖
COPY . .                  # 复制代码
CMD ["gunicorn", "run:app"]  # 启动命令
```

**Q: docker-compose.yml的作用？**

定义和管理多个容器的配置，实现一键部署。

**Q: 什么是内网穿透？**

把内网的服务暴露到外网，让外网用户也能访问。

**Q: Cloudflare Tunnel的原理？**

1. 在你的服务器运行cloudflared客户端
2. 客户端与Cloudflare服务器建立连接
3. 用户请求先到Cloudflare，再通过隧道转发到你的服务器

### 5.3 项目亮点

在面试中可以这样介绍：

> "我独立开发了一个AI职业决策系统，使用Flask+LangChain实现多Agent协作，支持流式响应和记忆管理。部署方面，我使用Docker容器化部署，通过docker-compose编排多个服务，使用Nginx反向代理，并配置了Cloudflare Tunnel实现外网访问。整个项目从开发到部署都是我独立完成的。"

---

## 六、常见问题

### Q1: 容器启动失败怎么办？

```bash
# 查看日志
docker-compose -f docker-compose.lan.yml logs

# 常见原因：
# 1. 端口被占用
sudo lsof -i :5000

# 2. 数据卷权限问题
sudo chmod -R 777 backups logs

# 3. 配置文件错误
cat .env
```

### Q2: 如何更新代码？

```bash
cd ~/ai_career_advisor
git pull
sudo docker-compose -f docker-compose.lan.yml up -d --build
```

### Q3: 如何备份数据？

```bash
# 备份MySQL
docker exec <mysql_container> mysqldump -u root -p career_advisor > backup_$(date +%Y%m%d).sql

# 备份ChromaDB
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_data/
```

### Q4: 如何恢复数据？

```bash
# 恢复MySQL
docker exec -i <mysql_container> mysql -u root -p career_advisor < backup.sql

# 恢复ChromaDB
tar -xzf chroma_backup.tar.gz
```

### Q5: 如何查看资源使用？

```bash
# 查看容器资源
docker stats

# 查看磁盘使用
df -h

# 查看内存使用
free -h
```

---

## 七、总结

### 核心知识点

1. **Docker**：容器化部署，环境隔离
2. **Docker Compose**：多容器编排，一键部署
3. **数据持久化**：volumes保证数据不丢失
4. **网络配置**：端口映射、内网穿透
5. **运维命令**：日志查看、故障排查

### 学习建议

1. **多动手**：实际操作比看书更有效
2. **多踩坑**：遇到问题解决问题是最好的学习
3. **多总结**：把解决问题的过程记录下来
4. **多分享**：写博客、做分享，加深理解

### 推荐资源

- [Docker官方文档](https://docs.docker.com/)
- [Docker Compose官方文档](https://docs.docker.com/compose/)
- [Cloudflare Tunnel文档](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
