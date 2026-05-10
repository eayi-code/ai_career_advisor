# AI职业决策支持系统 - 项目记忆文件

## 一、项目概述

### 1.1 项目名称
基于AI智能体的就业与副业决策支持系统

### 1.2 项目描述
一个面向求职者和职场人群的智能化职业规划平台，通过AI智能体技术提供个性化的职业匹配、副业推荐、技能差距分析等服务。系统采用ReAct推理模式，具备工具调用、记忆管理、多Agent协作能力。

### 1.3 核心特性
- 多智能体协作架构（职业规划、技能分析、副业分析、简历优化）
- ReAct推理模式，推理过程可视化
- 短期对话记忆 + 长期向量记忆（ChromaDB + Ollama）
- 混合意图识别（关键词+LLM回退）
- Apple设计语言落地页
- 内部页面白色+蓝色主题
- 对话气泡毛玻璃效果
- 全中文界面
- 对话状态保持，支持继续历史对话
- 打断生成功能
- Toast消息提示

---

## 二、技术栈

### 2.1 后端
- **框架**: Flask 3.x
- **ORM**: Flask-SQLAlchemy
- **数据库**: MySQL 8.0
- **迁移**: Flask-Migrate
- **认证**: Flask-Login

### 2.2 AI相关
- **智能体框架**: LangChain + LangGraph (v1.2.15)
- **推理模式**: ReAct (Thought → Action → Observation)
- **向量数据库**: ChromaDB
- **嵌入模型**: Ollama qwen3-embedding:0.6b (本地部署)
- **LLM**: 通过OpenAI兼容API调用

### 2.3 前端
- **模板引擎**: Jinja2
- **样式**: 自定义CSS (style.css)
- **脚本**: 原生JavaScript (main.js, modal.js)
- **字体**: Inter (Google Fonts) / SF Pro (Apple系统字体)
- **设计风格**: 
  - 落地页：CSS动画背景（浅色系流动渐变）
  - 内部页面：白色背景 + 蓝色主题 (#0066cc)
  - 对话气泡：毛玻璃效果（backdrop-filter: blur）

### 2.4 开发环境
- **Python版本**: 3.11 (Conda环境: career_advisor)
- **IDE**: PyCharm
- **项目目录**: D:\Opencode_workplace\ai_career_advisor

---

## 三、目录结构

```
ai_career_advisor/
├── .env                        # 环境变量配置
├── requirements.txt            # Python依赖
├── run.py                      # Flask启动文件
├── init_data.py                # 数据初始化脚本
├── DESIGN.md                   # Apple设计规范文档
├── PROJECT_MEMORY.md           # 项目记忆文件（本文件）
│
├── app/                        # 主应用目录
│   ├── __init__.py             # Flask应用工厂
│   ├── config.py               # 配置类
│   │
│   ├── agents/                 # 智能体模块
│   │   ├── base_agent.py       # 智能体基类（ReAct推理）
│   │   ├── career_agent.py     # 4个专业Agent定义
│   │   └── orchestrator.py     # 多Agent编排器（混合意图识别）
│   │
│   ├── tools/                  # 工具模块
│   │   ├── job_tools.py        # 职位搜索、薪资查询
│   │   ├── skill_tools.py      # 技能差距分析、学习路径
│   │   ├── market_tools.py     # 副业搜索、ROI计算
│   │   └── resume_tools.py     # 简历解析、优化、ATS评分
│   │
│   ├── memory/                 # 记忆模块
│   │   ├── short_term.py       # 短期记忆（对话窗口）
│   │   └── long_term.py        # 长期记忆（ChromaDB）
│   │
│   ├── models/                 # 数据模型
│   │   ├── user.py             # 用户表（含头像字段）
│   │   ├── profile.py          # 用户档案表
│   │   ├── history.py          # 对话历史表
│   │   ├── job.py              # 职位表、职位技能关联表
│   │   ├── skill.py            # 技能表、技能分类表、学习资源表
│   │   └── side_job.py         # 副业表
│   │
│   ├── routes/                 # 路由模块
│   │   ├── auth.py             # 认证路由（登录、注册、登出）
│   │   ├── career.py           # 业务路由（对话、用户中心）
│   │   └── api.py              # API接口
│   │
│   ├── static/                 # 静态资源
│   │   ├── css/style.css       # 全局样式
│   │   ├── js/
│   │   │   ├── main.js         # 主脚本
│   │   │   └── modal.js        # 弹窗组件（含toast和confirm）
│   │   └── uploads/avatars/    # 用户头像存储
│   │
│   └── templates/              # 页面模板
│       ├── base.html           # 基础模板
│       ├── index.html          # 落地页（Apple设计风格）
│       ├── auth/
│       │   ├── login.html      # 登录页
│       │   └── register.html   # 注册页
│       └── career/
│           ├── chat.html       # 智能对话（核心页面）
│           └── profile.html    # 用户中心
│
├── migrations/                 # 数据库迁移文件
└── chroma_data/                # ChromaDB向量数据存储
```

---

## 四、数据库设计

### 4.1 用户表 (users)
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar VARCHAR(255) DEFAULT '',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 用户档案表 (user_profiles)
```sql
CREATE TABLE user_profiles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    education VARCHAR(20) DEFAULT 'bachelor',
    major VARCHAR(100),
    skills JSON,
    work_experience INT DEFAULT 0,
    current_job_title VARCHAR(100),
    target_industry VARCHAR(100),
    target_salary_min FLOAT,
    target_salary_max FLOAT,
    location_preference VARCHAR(100),
    interests JSON,
    career_goals TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 4.3 对话历史表 (analysis_history)
```sql
CREATE TABLE analysis_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    conversation_id VARCHAR(50) NOT NULL,
    title VARCHAR(200),
    analysis_type VARCHAR(50),
    agent_used VARCHAR(50),
    input_data JSON,
    result_data JSON,
    reasoning_steps JSON,
    tools_used JSON,
    messages JSON,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 4.4 职位表 (jobs)
- 32条职位数据
- 包含薪资、经验要求、城市、行业等字段

### 4.5 职位技能关联表 (job_skills)
- 关联职位和技能

### 4.6 技能表 (skills)
- 18条技能数据
- 包含学习资源、难度、市场需求

### 4.7 副业表 (side_jobs)
- 15条副业数据
- 包含收入范围、时间投入、平台推荐

---

## 五、核心模块说明

### 5.1 智能体架构

#### BaseAgent (app/agents/base_agent.py)
- 智能体基类，实现ReAct推理模式
- 使用LangChain的create_agent创建Agent
- 集成短期记忆和长期记忆
- 提供run()方法执行推理

#### 专业Agent (app/agents/career_agent.py)
- CareerAgent: 职业规划，工具search_jobs、query_salary
- SkillAgent: 技能分析，工具analyze_skill_gap、recommend_learning_path
- SideJobAgent: 副业分析，工具search_side_jobs、calculate_side_job_roi
- ResumeAgent: 简历优化，工具parse_resume、analyze_jd、optimize_resume、ats_score、generate_resume

#### Orchestrator (app/agents/orchestrator.py)
- 多Agent编排器
- 混合意图识别：关键词匹配（分层权重）+ LLM回退
- 置信度阈值：0.6以上直接使用关键词结果，低于则调用LLM分类

### 5.2 工具系统

工具从数据库读取数据（非硬编码），通过SQLAlchemy ORM查询。

#### 工具列表
| Agent | 工具 | 功能 |
|-------|------|------|
| CareerAgent | search_jobs | 搜索职位 |
| CareerAgent | query_salary | 查询薪资 |
| SkillAgent | analyze_skill_gap | 分析技能差距 |
| SkillAgent | recommend_learning_path | 推荐学习路径 |
| SideJobAgent | search_side_jobs | 搜索副业 |
| SideJobAgent | calculate_side_job_roi | 计算副业ROI |
| ResumeAgent | parse_resume | 解析简历 |
| ResumeAgent | analyze_jd | 分析职位描述 |
| ResumeAgent | optimize_resume | 优化简历 |
| ResumeAgent | ats_score | ATS评分 |
| ResumeAgent | generate_resume | 生成简历 |

### 5.3 记忆系统

#### 短期记忆 (app/memory/short_term.py)
- 基于Python字典存储对话历史
- 按user_id分组，窗口大小限制

#### 长期记忆 (app/memory/long_term.py)
- 基于ChromaDB向量数据库
- 使用Ollama本地嵌入模型
- 持久化存储到./chroma_data目录

### 5.4 API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/agent/chat | 智能体对话 |
| GET | /api/history | 获取对话历史列表 |
| GET | /api/history/{id} | 获取单个对话详情 |
| DELETE | /api/history/{id} | 删除对话 |
| GET | /api/agent/tools | 获取Agent工具列表 |
| POST | /api/user/update-username | 修改用户名 |
| POST | /api/user/update-password | 修改密码 |
| POST | /api/user/update-avatar | 上传头像 |
| GET | /api/user/stats | 用户统计数据 |
| GET | /api/export/conversation/{id} | 导出对话 |

---

## 六、页面功能

### 6.1 落地页 (index.html)
- Apple设计语言（黑白为主，蓝色强调）
- 动画背景（UnicornStudio）
- 功能介绍、推理演示、统计数据
- Logo: CareerAI（分层几何图标）

### 6.2 登录/注册 (auth/login.html, auth/register.html)
- 用户名+密码登录
- 用户名+邮箱+密码注册
- Toast消息提示（3秒自动消失）
- Logo: CareerAI

### 6.3 智能对话 (career/chat.html)
- 核心页面，登录后默认进入
- 左侧边栏：新建对话、对话历史列表
- 中间：聊天区域
- 右侧：推理过程、工具调用展示
- 功能：发送消息、停止生成、继续历史对话、删除对话
- Logo: CareerAI

### 6.4 用户中心 (career/profile.html)
- 用户头像（点击上传）
- 基本信息（可修改用户名、密码）
- 使用统计（对话次数、Agent使用分布）
- 对话历史（导出、删除）
- 职业档案编辑
- Logo: CareerAI

---

## 七、配置说明

### 7.1 环境变量 (.env)
```
SECRET_KEY=dev-secret-key
DATABASE_URL=mysql+pymysql://root:password@localhost/career_advisor
OPENAI_API_KEY=sk-any-key
OPENAI_BASE_URL=https://your-api-endpoint/v1
OPENAI_MODEL=gpt-3.5-turbo
CHROMA_PERSIST_DIR=./chroma_data
```

### 7.2 启动命令
```bash
conda activate career_advisor
cd D:\Opencode_workplace\ai_career_advisor
flask run
```

### 7.3 数据初始化
```bash
python init_data.py
```

### 7.4 数据库迁移
```bash
flask db migrate -m "描述"
flask db upgrade
```

---

## 八、开发记录

### 2026-05-06 完成功能
1. 项目初始化和基础架构搭建
2. 数据库模型设计和创建
3. 智能体框架实现（ReAct推理）
4. 工具系统实现（6个工具）
5. 记忆系统实现（短期+长期）
6. 前端页面设计和实现
7. 用户认证系统
8. 对话功能完整实现
9. 扩充数据（32职位、18技能、15副业）
10. 用户中心功能（头像、改名、改密码、统计、导出）
11. 打断生成功能
12. 删除控制台，简化导航
13. 落地页Apple设计风格
14. Logo重新设计（CareerAI）
15. Toast消息提示系统
16. 简洁确认弹窗

### 2026-05-09 完成功能
1. 聊天界面优化
   - 消息复制按钮（hover显示，毛玻璃样式）
   - 对话气泡毛玻璃效果（backdrop-filter: blur(40px)）
   - 欢迎页面美化（功能卡片、图标）
   - 快速问题按钮美化（胶囊形状、图标）
   - Agent选择器添加"简历优化"选项
2. 落地页动画优化
   - CSS动画替代UnicornStudio
   - 浅色系流动渐变背景
   - CareerAI文字紫粉渐变
   - 打字机效果（推理演示区域）
   - 功能卡片hover效果
3. 简历Agent实现（ResumeAgent）
   - 5个工具：parse_resume、analyze_jd、optimize_resume、ats_score、generate_resume
   - 专业系统提示词
   - 前端入口（欢迎卡片、Agent选择器）
4. 意图识别优化
   - 混合方案：关键词匹配（分层权重）+ LLM回退
   - 置信度阈值：0.6
   - 支持4个Agent类型识别
5. 对话保存Bug修复
   - 问题：SQLAlchemy未检测到JSON字段变化
   - 解决：使用flag_modified标记字段为已修改
   - 修复多轮对话保存问题

---

## 九、设计规范

### 落地页
- 颜色：浅色系为主，紫粉渐变强调
- 字体：SF Pro / Inter
- 动画：CSS流动渐变背景（替代UnicornStudio）
- CareerAI文字：紫粉渐变，104-192px
- 功能卡片：hover上浮效果

### 内部页面
- 颜色：白色背景，蓝色主题 (#0066cc)
- 字体：Inter
- 侧边栏：固定左侧
- 组件：Toast提示、简洁确认弹窗

### 对话气泡
- 毛玻璃效果：backdrop-filter: blur(40px) saturate(180%)
- 用户消息：浅蓝色半透明背景
- AI消息：白色半透明背景
- 背景：彩色渐变光斑（蓝、紫、粉）
- 复制按钮：hover显示，右下角，毛玻璃样式

### Logo
- 名称：CareerAI
- 图标：分层几何图形（类似Notion风格）
- 颜色：蓝色 (#0066cc)

---

## 十、待办事项

### 10.1 功能扩展
- [ ] 简历Agent前端完善（文件上传、简历预览、PDF导出）
- [ ] 面试准备Agent（InterviewAgent）
- [ ] 市场趋势分析功能
- [ ] 数据可视化图表（Chart.js）
- [ ] 暗色模式支持

### 10.2 数据扩充
- [ ] 职位数据扩充到100+
- [ ] 技能数据扩充到50+
- [ ] 副业数据扩充到30+

### 10.3 技术优化
- [ ] 添加单元测试
- [ ] API限流保护
- [ ] 缓存优化（Redis）
- [ ] 部署文档（Docker）

---

## 十一、常见问题

### Q1: LangChain API报错
LangChain版本更新频繁，API变化大。当前使用v1.2.15。

### Q2: ChromaDB嵌入模型下载慢
使用Ollama本地嵌入模型避免下载。

### Q3: 数据库迁移失败
```bash
flask db downgrade base
flask db upgrade
```

### Q4: cryptography包缺失
```bash
pip install cryptography
```

### Q5: JSON字段保存后数据丢失
SQLAlchemy未检测到JSON字段变化，需要使用flag_modified：
```python
from sqlalchemy.orm.attributes import flag_modified
flag_modified(history, 'messages')
db.session.commit()
```

### Q6: 简历解析依赖
```bash
pip install pypdf python-docx
```

---

**最后更新**: 2026-05-09
**项目状态**: 核心功能完成，简历Agent已实现，可继续扩展
