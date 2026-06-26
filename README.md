# CareerAI - 智能职业决策支持系统

基于多智能体协作的 AI 职业规划平台，通过 5 个专业 Agent 协同工作，为求职者提供个性化职业匹配、技能差距分析、简历生成和面试准备服务。

## 核心特性

- **5 个专业智能体**：职业规划顾问、技能发展顾问、副业规划专家、简历优化专家、面试教练
- **多意图链式协同**：自动识别复合意图，DAG 调度器并行派发多 Agent
- **ReAct 推理透明化**：实时展示思考 → 行动 → 观察 → 结论的推理过程
- **流式响应**：SSE 实时推送执行步骤和回复内容，支持断线重连
- **向量长期记忆**：基于 ChromaDB 的对话记忆，越用越懂你
- **简历自动生成**：根据用户档案和对话内容一键生成专业简历
- **职位搜索与分析**：内置 60+ 职位数据，支持薪资查询和职位对比

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangChain + LangGraph + ReAct |
| 后端 | Python / Flask / SQLAlchemy |
| 向量数据库 | ChromaDB |
| 大模型 | OpenAI API / Ollama (MiMo) |
| 前端 | 原生 JavaScript + Jinja2 + Marked.js |
| 数据库 | MySQL |
| 部署 | Docker + Docker Compose + Nginx |

## 快速开始

### 环境要求

- Python 3.10+
- MySQL 8.0+
- 可选：Ollama（本地模型）

### 安装

```bash
# 克隆项目
git clone https://github.com/eayi-code/ai_career_advisor.git
cd ai_career_advisor

# 创建虚拟环境
conda create -n career_advisor python=3.10
conda activate career_advisor

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的配置（API Key、数据库密码等）

# 初始化数据库
python init_data.py

# 创建管理员账号（可选）
python scripts/setup_admin.py

# 启动
python run.py
```

访问 `http://localhost:5000`

### Docker 部署

```bash
# 局域网部署
docker-compose -f docker-compose.lan.yml up -d

# 标准部署
docker-compose up -d
```

## 项目结构

```
├── app/
│   ├── agents/          # 智能体实现（5个Agent + 编排器）
│   ├── models/          # 数据模型（用户、历史、任务）
│   ├── routes/          # 路由（认证、对话、API、管理后台）
│   ├── services/        # 业务逻辑（对话、档案、简历）
│   ├── tools/           # Agent 工具（职位搜索、简历生成等）
│   ├── static/          # 前端资源（CSS/JS/图片）
│   ├── templates/       # Jinja2 模板
│   └── data/            # 种子数据（职位、技能、副业）
├── scripts/             # 部署和维护脚本
├── tests/               # 单元测试
├── migrations/          # 数据库迁移
├── docker-compose.yml   # Docker 编排
└── run.py               # 启动入口
```

## 管理后台

访问 `/admin/dashboard` 查看：
- 用户增长趋势（Chart.js 可视化）
- 智能体使用分布
- 实时任务监控
- 用户管理（启用/禁用/权限）

## 安全特性

- CSRF 全局保护（Flask-WTF）
- SSRF 防护（内网 IP 检测）
- 登录失败锁定（5次/15分钟）
- 文件上传验证（Pillow 格式校验 + 大小限制）
- API 速率限制（Flask-Limiter）
- 安全响应头（X-Frame-Options, CSP 等）

## 许可证

MIT License
