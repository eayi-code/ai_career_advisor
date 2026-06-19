# AI职业决策支持系统 - 项目记忆文件

## 一、项目概述

### 1.1 项目名称
基于AI智能体的就业与副业决策支持系统

### 1.2 项目描述
一个面向求职者和职场人群的智能化职业规划平台，通过AI智能体技术提供个性化的职业匹配、副业推荐、技能差距分析等服务。系统采用ReAct推理模式，具备工具调用、记忆管理、多Agent协作能力。

### 1.3 核心特性
- 5个专业智能体协作（职业规划、技能分析、副业分析、简历优化、面试教练）
- ReAct推理模式，推理过程可视化
- 短期对话记忆 + 长期向量记忆（ChromaDB + Ollama）
- 混合意图识别（关键词+LLM回退）
- 复合意图支持，多Agent链式协作
- 执行步骤可视化（步骤卡片展示）
- 简历文件上传/下载（PDF/DOCX/HTML）
- 简历预览面板（右侧侧边栏，iframe渲染HTML简历）
- 用户档案记忆（偏好、技能、目标等，分层结构）
- 对话中自动提取用户信息并保存到档案
- 多目标岗位支持（target_jobs列表）
- 流式响应（SSE）
- Apple设计语言落地页
- 内部页面白色+蓝色主题
- 对话气泡毛玻璃效果
- 全中文界面
- 对话状态保持，支持继续历史对话
- 打断生成功能
- Toast消息提示
- **移动端响应式适配**（768px断点，抽屉式侧边栏，浮动输入框）
- **意图识别缓存**（相同查询0ms响应）
- **常见复合意图硬编码拆分**（避免LLM调用）
- **SSL证书自动检测修复**（certifi跨平台兼容）

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
- **LLM**: mimo-v2.5-pro（通过OpenAI兼容API调用）
- **自定义LLM**: MiMoChatOpenAI（支持reasoning_content传回）

### 2.3 前端
- **模板引擎**: Jinja2
- **样式**: 自定义CSS (style.css)
- **脚本**: 原生JavaScript (main.js, modal.js)
- **字体**: Inter (Google Fonts) / SF Pro (Apple系统字体)
- **第三方库**:
  - html2canvas：HTML转Canvas（用于截图和PDF生成）
  - jsPDF：Canvas/图片转PDF（前端PDF生成）
- **设计风格**: 
  - 落地页：CSS动画背景（浅色系流动渐变）
  - 内部页面：白色背景 + 蓝色主题 (#0066cc)
  - 对话气泡：毛玻璃效果（backdrop-filter: blur）
  - 用户中心：苹果风格，分层折叠面板

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
├── init_data.py                # 数据初始化脚本（60职位、60技能、30副业）
├── DESIGN.md                   # Apple设计规范文档
├── PROJECT_MEMORY.md           # 项目记忆文件（本文件）
│
├── app/                        # 主应用目录
│   ├── __init__.py             # Flask应用工厂
│   ├── config.py               # 配置类（含数据库连接池配置）
│   │
│   ├── agents/                 # 智能体模块
│   │   ├── base_agent.py       # 智能体基类（ReAct推理+记忆集成）
│   │   ├── career_agent.py     # 5个专业Agent定义
│   │   ├── orchestrator.py     # 多Agent编排器（复合意图+协作+自动提取）
│   │   └── custom_llm.py       # MiMoChatOpenAI（支持reasoning_content）
│   │
│   ├── tools/                  # 工具模块
│   │   ├── job_tools.py        # 职位搜索、薪资查询、职位对比、save_target_job、update_user_profile
│   │   ├── skill_tools.py      # 技能差距分析、学习路径、技能优先级
│   │   ├── market_tools.py     # 副业搜索、ROI计算、匹配度评分
│   │   ├── resume_tools.py     # 简历解析、优化、ATS评分、STAR改写、HTML简历生成
│   │   ├── interview_tools.py  # 面试题生成、自我介绍、薪资谈判、JD分析
│   │   └── resume_templates/   # HTML简历模板目录（professional.html、sidebar.html）
│   │
│   ├── memory/                 # 记忆模块
│   │   ├── short_term.py       # 短期记忆（对话窗口）
│   │   └── long_term.py        # 长期记忆（ChromaDB）
│   │
│   ├── models/                 # 数据模型
│   │   ├── user.py             # 用户表（含头像字段）
│   │   ├── profile.py          # 用户档案表（分层结构，含多目标岗位、项目经历、证书等）
│   │   ├── history.py          # 对话历史表
│   │   ├── job.py              # 职位表、职位技能关联表
│   │   ├── skill.py            # 技能表、技能分类表、学习资源表
│   │   └── side_job.py         # 副业表
│   │
│   ├── routes/                 # 路由模块
│   │   ├── auth.py             # 认证路由（登录、注册、登出）
│   │   ├── career.py           # 业务路由（对话、用户中心，处理所有档案字段）
│   │   └── api.py              # API接口（含流式响应SSE）
│   │
│   ├── static/                 # 静态资源
│   │   ├── css/style.css       # 全局样式（含折叠面板、分层表单样式）
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
│           ├── chat.html       # 智能对话（核心页面，支持流式响应）
│           └── profile.html    # 用户中心（苹果风格，分层折叠）
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
    -- 基本信息
    education VARCHAR(20) DEFAULT 'bachelor',
    major VARCHAR(100),
    skills JSON,
    work_experience INT DEFAULT 0,
    current_job_title VARCHAR(100),
    -- 求职意向
    target_job_title VARCHAR(100),           -- 当前选中的目标岗位
    target_jobs JSON,                         -- 所有目标岗位列表 [{"title":"XX","added_at":"XX"}]
    target_industry VARCHAR(100),
    target_salary_min FLOAT,
    target_salary_max FLOAT,
    location_preference VARCHAR(100),
    job_search_status VARCHAR(20) DEFAULT 'observing',  -- observing/employed/resigned/fresh
    work_preference VARCHAR(20) DEFAULT 'flexible',     -- remote/onsite/hybrid/flexible
    expected_join_time VARCHAR(20) DEFAULT 'flexible',  -- flexible/1month/3months/negotiable
    company_type_preference VARCHAR(50),                -- startup/big_company/foreign/flexible
    -- 项目经历
    projects JSON,                            -- [{"name":"","role":"","tech_stack":"","achievement":""}]
    -- 证书资质
    certifications JSON,                      -- ["证书1","证书2"]
    -- 副业信息
    available_hours_per_week INT,
    side_job_income_target FLOAT,
    -- 其他
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
- 60条职位数据
- 包含薪资、经验要求、城市、行业等字段

### 4.5 职位技能关联表 (job_skills)
- 关联职位和技能

### 4.6 技能表 (skills)
- 60条技能数据
- 包含学习资源、难度、市场需求

### 4.7 副业表 (side_jobs)
- 30条副业数据
- 包含收入范围、时间投入、平台推荐

---

## 五、架构概览（重要）

### 5.1 核心概念

本系统采用**多Agent协作架构**，由三层组成：

```
用户输入 → Orchestrator（调度器）→ Agent（智能体）→ Tool（工具）→ 数据库
```

| 概念 | 文件 | 职责 | 类比 |
|------|------|------|------|
| **Orchestrator** | `app/agents/orchestrator.py` | 接收请求、意图识别、调度Agent、合并结果 | 项目经理 |
| **Agent** | `app/agents/career_agent.py` | 执行具体领域任务，决定调用哪些工具 | 领域专家 |
| **Tool** | `app/tools/*.py` | 单一功能函数，查询数据库返回数据 | 工具/设备 |
| **BaseAgent** | `app/agents/base_agent.py` | Agent基类，封装通用逻辑（记忆、上下文、重试） | 基础模板 |
| **MiMoChatOpenAI** | `app/agents/custom_llm.py` | 自定义LLM，支持mimo模型的reasoning_content | API适配器 |

### 5.2 调用流程

```
用户："帮我写简历"
    ↓
Orchestrator._classify_intent()
    → 识别为 resume 意图
    → 检查用户档案：无目标岗位？
    → 自动添加 career 前置任务
    ↓
Orchestrator._split_composite_task()
    → 拆分为：[career确定目标岗位, resume生成简历]
    ↓
Orchestrator.process() 串行执行
    ├─ Step 1: CareerAgent.run("了解用户背景，确定目标岗位")
    │       ↓
    │   CareerAgent.build_agent() → create_agent(llm, tools, prompt)
    │   Agent.invoke(messages)
    │       ├─ LLM决定调用 search_jobs 工具
    │       ├─ Tool执行 → 返回职位数据
    │       ├─ LLM决定调用 save_target_job 工具
    │       ├─ Tool执行 → 保存到user_profiles表
    │       └─ LLM生成最终回复
    │   返回 {"success": True, "output": "...", "steps": [...]}
    │
    ├─ Step 2: ResumeAgent.run("根据目标岗位生成简历")
    │       ↓
    │   _build_context() → 读取用户档案（含刚保存的目标岗位）
    │   Agent.invoke(messages)
    │       ├─ LLM决定调用 generate_resume 工具
    │       ├─ Tool执行 → 生成HTML简历
    │       └─ LLM生成回复 + 简历内容
    │   返回 {"success": True, "output": "<!--RESUME_START-->...<!--END-->"}
    │
    ↓
Orchestrator._extract_user_info()
    → 从用户输入中提取信息保存到档案
    ↓
Orchestrator._merge_results()
    → 合并两个Agent的输出
    ↓
返回给前端（流式/非流式）
```

### 5.3 Agent与Tool的对应关系

每个Agent在初始化时绑定自己的Tool列表，Agent只能调用自己绑定的工具：

| Agent | 绑定的Tool | 数据来源 |
|-------|-----------|----------|
| CareerAgent | search_jobs, query_salary, compare_jobs, save_target_job, update_user_profile | jobs表, user_profiles表 |
| SkillAgent | analyze_skill_gap, recommend_learning_path, skill_priority | skills表, jobs表 |
| SideJobAgent | search_side_jobs, calculate_side_job_roi, side_job_match | side_jobs表 |
| ResumeAgent | parse_resume, analyze_jd, optimize_resume, ats_score, generate_resume, star_rewrite | LLM生成 |
| InterviewAgent | generate_interview_questions, optimize_self_intro, salary_negotiation_tips, analyze_job_description | LLM生成 |

### 5.4 数据流向

```
┌─────────────────────────────────────────────────────────┐
│                      数据存储层                          │
├─────────────────────────────────────────────────────────┤
│  MySQL                                                  │
│  ├─ users: 用户账号                                     │
│  ├─ user_profiles: 职业档案（技能、目标岗位、项目等）    │
│  ├─ analysis_history: 对话历史（JSON存储）               │
│  ├─ jobs: 60条职位数据                                  │
│  ├─ skills: 60条技能数据                                │
│  └─ side_jobs: 30条副业数据                             │
│                                                         │
│  ChromaDB                                               │
│  └─ agent_memory: 向量化的对话历史（长期记忆）           │
└─────────────────────────────────────────────────────────┘
         ↑                           ↑
         │ 读写                      │ 读写
         ↓                           ↓
┌─────────────────┐         ┌─────────────────┐
│  Tool执行层     │         │  记忆系统       │
│  21个工具函数   │         │  short_term.py  │
│  查询MySQL返回  │         │  long_term.py   │
└────────┬────────┘         └────────┬────────┘
         │ 调用                      │ 读写
         ↓                           ↓
┌─────────────────────────────────────────────────────────┐
│  Agent层（5个专业智能体）                                │
│  每个Agent绑定特定Tool，拥有独立系统提示词               │
│  通过BaseAgent.run()执行，内置重试和质量验证            │
└────────────────────────┬────────────────────────────────┘
                         │ 调度
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Orchestrator层（调度器）                                │
│  意图识别 → 任务拆分 → Agent调用 → 结果合并             │
│  自动信息提取 → 保存到user_profiles                     │
└────────────────────────┬────────────────────────────────┘
                         │ 返回
                         ↓
┌─────────────────────────────────────────────────────────┐
│  前端展示层                                              │
│  chat.html: 流式消息、执行步骤、简历预览                 │
│  profile.html: 分层职业档案表单                          │
└─────────────────────────────────────────────────────────┘
```

---

## 六、核心模块说明

### 5.1 智能体架构

#### BaseAgent (app/agents/base_agent.py)
- 智能体基类，实现ReAct推理模式
- 使用MiMoChatOpenAI创建Agent（支持reasoning_content）
- 集成短期记忆、长期记忆、用户档案
- 自动获取用户偏好作为上下文（_build_context读取所有档案字段）
- 支持多轮对话和局部修改
- 重试机制（max_retries=2）
- 输出质量验证（_validate_output）
- **重要**：所有DB查询前先rollback，防止事务错误

#### MiMoChatOpenAI (app/agents/custom_llm.py)
- 继承ChatOpenAI，支持mimo模型的reasoning_content
- monkey-patch `_convert_dict_to_message`：从API响应提取reasoning_content
- monkey-patch `_convert_message_to_dict`：将reasoning_content写回API请求
- 解决mimo模型多轮工具调用时"reasoning_content must be passed back"错误

#### 专业Agent (app/agents/career_agent.py)
- CareerAgent: 职业规划，工具search_jobs、query_salary、compare_jobs、save_target_job、update_user_profile
- SkillAgent: 技能分析，工具analyze_skill_gap、recommend_learning_path、skill_priority
- SideJobAgent: 副业分析，工具search_side_jobs、calculate_side_job_roi、side_job_match
- ResumeAgent: 简历优化（HTML+Tailwind CSS输出），工具parse_resume、analyze_jd、optimize_resume、ats_score、generate_resume、star_rewrite
- InterviewAgent: 面试教练，工具generate_interview_questions、optimize_self_intro、salary_negotiation_tips、analyze_job_description

#### Orchestrator (app/agents/orchestrator.py)
- 多Agent编排器（增强版）
- 混合意图识别：关键词匹配（分层权重）+ LLM回退
- 复合意图支持：识别多个意图，任务拆分
- 多Agent协作：链式调用，上下文传递
- 结果质量评估：检测输出质量
- 执行步骤记录：供前端可视化
- **自动用户信息提取**：_extract_user_info从对话中提取个人信息并保存到档案
- **智能前置任务**：用户无目标岗位时自动添加career前置任务
- **重要**：所有DB查询前先rollback，防止事务错误

### 5.2 工具系统

工具从数据库读取数据（非硬编码），通过SQLAlchemy ORM查询。

#### 工具列表
| Agent | 工具 | 功能 |
|-------|------|------|
| CareerAgent | search_jobs | 搜索职位 |
| CareerAgent | query_salary | 查询薪资 |
| CareerAgent | compare_jobs | 对比多个职位 |
| CareerAgent | save_target_job | 保存目标岗位到用户档案 |
| CareerAgent | update_user_profile | 更新用户档案字段 |
| SkillAgent | analyze_skill_gap | 分析技能差距 |
| SkillAgent | recommend_learning_path | 推荐学习路径 |
| SkillAgent | skill_priority | 技能优先级排序 |
| SideJobAgent | search_side_jobs | 搜索副业 |
| SideJobAgent | calculate_side_job_roi | 计算副业ROI |
| SideJobAgent | side_job_match | 副业匹配度评分 |
| ResumeAgent | parse_resume | 解析简历 |
| ResumeAgent | analyze_jd | 分析职位描述 |
| ResumeAgent | optimize_resume | 优化简历 |
| ResumeAgent | ats_score | 多维度ATS评分 |
| ResumeAgent | generate_resume | 生成HTML简历 |
| ResumeAgent | star_rewrite | STAR法则改写 |
| InterviewAgent | generate_interview_questions | 生成面试题 |
| InterviewAgent | optimize_self_intro | 优化自我介绍 |
| InterviewAgent | salary_negotiation_tips | 薪资谈判建议 |
| InterviewAgent | analyze_job_description | 深度分析JD |

### 5.3 记忆系统

#### 短期记忆 (app/memory/short_term.py)
- 基于Python字典存储对话历史
- 按user_id分组，窗口大小限制为10

#### 长期记忆 (app/memory/long_term.py)
- 基于ChromaDB向量数据库
- 使用Ollama本地嵌入模型
- 持久化存储到./chroma_data目录

#### 用户档案记忆
- 自动从UserProfile获取用户偏好
- 包含：职位、技能、目标行业、薪资期望、城市偏好、项目经历、证书、副业信息
- 作为上下文传递给Agent（_build_context读取所有字段）

#### 自动信息提取
- Orchestrator的_extract_user_info方法
- 从用户对话中自动提取：技能、工作年限、学历、专业、当前职位、目标岗位、目标行业、意向城市、证书、项目经历、可用时间、收入目标
- 提取结果追加到Agent回复末尾
- 用户可在用户中心查看提取的信息

### 5.4 API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/test | 测试接口（临时，可删除） |
| POST | /api/agent/chat | 智能体对话（非流式） |
| POST | /api/agent/chat/stream | 智能体对话（流式SSE） |
| POST | /api/upload/resume | 上传简历文件 |
| POST | /api/download/resume | 下载简历（支持DOCX/HTML） |
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

## 七、页面功能

### 6.1 落地页 (index.html)
- Apple设计语言（黑白为主，蓝色强调）
- CSS动画背景（浅色系流动渐变）
- 功能介绍、推理演示、统计数据
- Logo: CareerAI（分层几何图标）

### 6.2 登录/注册 (auth/login.html, auth/register.html)
- 用户名+密码登录
- 用户名+邮箱+密码注册
- Toast消息提示（3秒自动消失）
- Logo: CareerAI

### 6.3 智能对话 (career/chat.html)
- 核心页面，登录后默认进入
- 顶部栏：对话标题、推理详情按钮
- 左侧边栏：新建对话、对话历史列表
- 中间：聊天区域（消息气泡、复制按钮）
- 右侧推理详情面板（执行流程、推理过程、工具调用）
- 右侧简历预览面板（iframe渲染HTML简历，500px宽）
- 输入区域：Agent选择器、文件上传按钮、发送按钮
- 功能：发送消息、停止生成、继续历史对话、删除对话
- **流式响应**：使用fetch + ReadableStream接收SSE
- Logo: CareerAI

### 6.4 用户中心 (career/profile.html)
- **苹果风格设计**，分层折叠面板
- 用户头像（点击上传）
- 基本信息（可修改用户名、密码）
- 使用统计（对话次数、Agent使用分布）
- 对话历史（导出、删除）
- 职业档案（分层结构）：
  - 📋 基本信息：学历、专业、工作年限、当前职位、技能
  - 🎯 求职意向：目标岗位、目标行业、目标薪资、偏好城市、求职状态、工作偏好、期望入职时间、公司类型偏好
  - 💼 项目经历：动态添加/删除
  - 📜 证书资质
  - 💰 副业信息：每周可用时间、收入目标
  - 📝 职业目标
- Logo: CareerAI

---

## 八、配置说明

### 7.1 环境变量 (.env)
```
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=mysql+pymysql://root:1234@localhost/career_advisor
OPENAI_API_KEY=tp-xxx
OPENAI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
OPENAI_MODEL=mimo-v2.5-pro
CHROMA_PERSIST_DIR=D:/Opencode_workplace/ai_career_advisor/chroma_data
```

### 7.2 数据库连接池配置 (config.py)
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,    # 1小时回收连接
    'pool_pre_ping': True,   # 使用前检查连接
    'max_overflow': 20,
}
```

### 7.3 启动命令
```bash
conda activate career_advisor
cd D:\Opencode_workplace\ai_career_advisor
flask run
```

### 7.4 数据初始化
```bash
python init_data.py
```

### 7.5 数据库迁移
```bash
flask db migrate -m "描述"
flask db upgrade
```

---

## 九、开发记录

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

### 2026-05-10 完成功能
1. 简历文件上传/下载功能
   - 文件上传API（支持PDF/DOCX/TXT）
   - DOCX文件生成下载API
   - 前端文件上传按钮（回形针图标）
   - 文件预览条显示
2. 简历预览面板
   - 右侧500px宽独立面板
   - Markdown渲染预览
   - 下载DOCX按钮
   - 与推理详情面板分离
3. Agent能力增强
   - ATS多维度评分（关键词、技能、量化、格式、可读性）
   - STAR改写工具（自动STAR法则改写）
   - 面试Agent（4个工具）
   - 职位对比工具
   - 技能优先级排序工具
   - 副业匹配度评分工具
4. 数据扩充
   - 职位数据：32→60条
   - 技能数据：18→60条
   - 副业数据：15→30条
5. 记忆增强
   - Agent自动获取用户档案作为上下文
   - 包含：职位、技能、目标行业、薪资期望、城市偏好
6. 多Agent协作
   - 复意度识别（支持多个意图）
   - 任务拆分（LLM拆分子任务）
   - 链式调用（上下文传递）
   - 结果合并
7. 执行步骤可视化
   - 侧边栏新增"执行流程"面板
   - 步骤卡片显示（意图分析、Agent调用、任务拆分等）
   - 彩色图标区分类型
   - 状态指示（completed/running/failed/warning）
8. 前端布局优化
   - 固定顶部栏（显示对话标题）
   - 固定输入框底部
   - 推理详情面板可收起（320px）
   - 简历预览面板可收起（500px）
9. 多轮对话优化
   - 提示词支持"修改XX"、"换个说法"等精确指令
   - 支持局部修改和追问
10. 输出质量优化
    - 支持Markdown格式渲染（列表、代码块、表格）
    - 消息内容格式化增强
11. Bug修复
    - 修复JavaScript重复声明错误（Jinja2模板嵌套问题）
    - 修复推理详情面板无法关闭问题
    - 修复简历预览误触发问题

### 2026-05-12 完成功能
1. 智能体能力优化
   - BaseAgent增加重试机制（max_retries=2）
   - BaseAgent增加输出质量验证（_validate_output）
   - BaseAgent抽取上下文构建方法（_build_context）
   - 5个Agent提示词增加few-shot示例
2. 工具系统优化
   - job_tools所有工具增加try-catch错误处理
   - 统一错误提示格式
3. 意图识别优化
   - 关键词扩充（新增20+关键词）
   - 增加上下文感知（context参数）
   - 返回结构化结果（置信度、匹配关键词、识别理由）
4. 多Agent调度优化
   - 并行执行支持（ThreadPoolExecutor，max_workers=3）
   - 任务拆分优化（depends_on依赖关系）
   - 错误恢复策略（_execute_with_retry带重试执行）
   - 质量检查增强（0-100分评分）
   - 执行时长记录
5. 简历功能优化
   - 简历内容与对话文字分离（<!--RESUME_START-->标记）
   - 前端提取标记内容用于预览/下载
   - 简历消息隐藏复制按钮
   - 预览卡片保留"预览"按钮（关闭后可重新打开）
6. 调度可视化增强
   - 置信度显示（高/中/低颜色区分）
   - 执行时长显示
   - 质量分数显示
   - 并行执行标识（闪电图标）
   - 识别理由显示（对话气泡图标）
   - 所有emoji替换为SVG图标

### 2026-05-13 完成功能
1. **多智能体编排器完美重构**
   - 创建DAGResolver类：真正的DAG依赖图解析，支持拓扑排序
   - 创建SharedContext类：Agent间数据共享机制
   - 创建IntentClassifier类：智能意图识别（关键词+LLM+用户档案）
   - 创建ResultMerger类：LLM智能合并多Agent输出
   - 创建QualityAssessor类：多维度质量评估
   - 创建ErrorRecovery类：降级策略和备选方案
   - 支持并行执行组：无依赖任务可并行执行
   - 支持依赖图验证：检测循环依赖和缺失依赖
2. 简历生成升级为HTML格式
   - 创建resume_template.html（HTML+Tailwind CSS模板）
   - 修改ResumeAgent提示词：前端工程师人设，生成HTML简历
   - 修改GenerateResumeTool：输出HTML+Tailwind CSS代码
   - 前端预览面板：使用iframe渲染HTML简历
   - 下载接口：支持HTML和DOCX双格式
2. 多目标岗位支持
   - UserProfile添加target_jobs字段（JSON数组）
   - save_target_job工具：支持保存多个岗位
   - ResumeAgent：多岗位时询问用户选择
   - 用户中心：显示历史目标岗位列表
3. 职业档案分层重构
   - 苹果风格设计，分层折叠面板
   - 新增字段：求职状态、工作偏好、期望入职时间、公司类型偏好
   - 新增字段：项目经历（动态添加/删除）、证书资质
   - 新增字段：每周可用时间、副业收入目标
   - 表单按逻辑分组：基本信息、求职意向、项目经历、证书、副业、职业目标
   - SVG图标替换emoji
4. 自动用户信息提取
   - Orchestrator新增_extract_user_info方法
   - 支持提取：技能、工作年限、学历、专业、当前职位、目标岗位、目标行业、意向城市、证书、项目经历、可用时间、收入目标
   - 提取结果追加到Agent回复末尾
   - 用户可在对话中看到"已自动更新您的职业档案"提示
5. 流式响应实现
   - 新增/api/agent/chat/stream端点（SSE）
   - 使用Response + stream_with_context
   - 事件类型：start、steps、agent、tools、content、done、error
   - 前端使用fetch + ReadableStream接收
   - 实时更新消息内容和执行步骤
6. 多Agent协作流程优化
   - 智能前置任务：用户无目标岗位时自动添加career前置任务
   - 链式上下文传递：前面Agent的结果传递给后续Agent
   - 意图识别增强：检测用户档案决定是否需要前置任务
7. MiMoChatOpenAI自定义LLM
   - 创建app/agents/custom_llm.py
   - 解决mimo-v2.5-pro模型的reasoning_content传回问题
   - monkey-patch _convert_dict_to_message和_convert_message_to_dict
   - 支持多轮工具调用时reasoning_content正确传递
8. 数据库事务修复
   - 所有DB查询前添加db.session.rollback()
   - 修复"Can't reconnect until invalid transaction is rolled back"错误
   - 涉及文件：base_agent.py、orchestrator.py、job_tools.py、api.py
9. 数据库连接池优化
   - 添加SQLALCHEMY_ENGINE_OPTIONS配置
   - pool_recycle=3600（1小时回收）
   - pool_pre_ping=True（使用前检查）
   - 修复MySQL连接超时问题
10. 前端滚动修复
     - app-layout设置height: 100vh + overflow: hidden
     - main-content设置overflow-y: auto
     - collapse-content展开时max-height: none
     - 修复用户中心无法滚动问题

### 2026-05-20 完成功能
1. **多智能体编排器Bug修复**
   - 修复DAG解析器入度计算错误：所有task必须初始化in_degree
   - 修复Flask应用上下文在线程中丢失：并行执行时为每个线程创建app_context
   - 修复LLM返回非JSON格式：正则提取```json```包裹内容，容错解析
   - 修复意图识别降级逻辑：LLM失败时使用关键词匹配结果
   - 修复后台线程无法访问current_user：主线程获取user_id传入线程
2. **推理详情面板滚动修复**
   - 修复panel-section overflow: hidden导致内容截断
   - 添加max-height: 40vh + overflow-y: auto
   - 修复chat-side-panel overflow: hidden
3. **前端加载体验优化**
   - 添加进度提示文字（正在思考中→正在分析中→复杂任务处理中）
   - 超时提示（8秒、20秒自动更新）
4. **流式响应探索与验证**
   - 验证Flask SSE（Server-Sent Events）方案可行性
   - 结论：Flask同步阻塞特性导致SSE无法实时推送
   - 保留Celery异步方案作为可选优化（见第十二章）
5. **同步方案确认可用**
   - 使用/api/agent/chat同步端点，复合Agent正常工作
   - 单Agent：约10-20秒
   - 复合Agent（career+resume）：约65秒（5次LLM调用）

### 2026-05-20 下午 完成功能（推理详情改进）
1. **推理详情面板改进 - 内联到对话流**
   - 将推理步骤从右侧独立面板改为内联到AI消息气泡中
   - 使用时间线样式，左侧圆点图标+连接线
   - 支持折叠/展开（点击"推理过程"标题）
   - 显示工具调用详情（工具名、参数、输出预览）
   - 显示额外信息（置信度、时长、质量分数）

2. **SSE流式响应实现**
   - 新增 `/api/agent/chat/stream` 端点（SSE流式响应）
   - 使用 `queue.Queue` 在后台线程和SSE生成器之间传递步骤
   - 前端使用 `fetch + ReadableStream` 接收SSE事件
   - 实时解析 `event: step` 事件并更新UI

3. **Orchestrator回调机制**
   - `AgentOrchestrator.__init__` 新增 `on_step_callback` 参数
   - 新增 `_emit_step()` 方法调用回调函数
   - 在关键步骤调用回调：意图分析、Agent调用、质量检查、任务拆分、结果合并
   - 回调函数在后台线程中被调用，通过线程安全的 `queue.Queue` 传递数据

4. **异步轮询方案（备用）**
   - 新增 `/api/agent/chat/async` 端点（异步任务）
   - 新增 `/api/agent/task/<task_id>` 端点（查询任务状态）
   - 新增 `/api/history/save` 端点（保存对话记录）
   - 支持轮询获取实时步骤（作为SSE的备用方案）

5. **前端SSE接收实现**
   - `sendMessage()` 改用 `/api/agent/chat/stream` 端点
   - 新增 `streamAgentChat()` 函数处理SSE流
   - 新增 `handleSSEEvent()` 函数解析SSE事件
   - 新增 `updateLiveSteps()` 函数实时渲染步骤
   - 新增 `handleTaskCompleted()` 函数处理完成后的逻辑
   - 新增 `addConversationToList()` 函数将新对话添加到sidebar

6. **Bug修复**
   - 修复对话保存问题：改为在SSE端点后台线程中直接保存，而非依赖前端调用保存API
   - 修复按钮状态重置问题：在 `handleTaskCompleted()` 开头添加 `setProcessingState(false)`
   - 修复Agent构造函数：所有Agent支持 `on_tool_callback` 参数
   - 修复BaseAgent：支持工具调用回调，在工具调用前后发送状态更新

7. **Agent工具调用回调**
   - `BaseAgent.__init__` 新增 `on_tool_callback` 参数
   - 所有Agent（CareerAgent、SkillAgent、SideJobAgent、ResumeAgent、InterviewAgent）支持回调
   - 在工具调用前后发送状态更新到前端

### 2026-05-20 晚上 完成功能（用户中心AI-Native改造）
1. **设计理念更新**
   - 从"传统表单收集"改为"AI记忆镜像"
   - 用户中心定位：AI对用户的认知面板
   - 减少主动填写，强调自动沉淀

2. **后端API新增**
   - `/api/profile/completion` - 档案完善度计算（加权字段统计）
   - `/api/profile/milestones` - 决策里程碑（从对话记录提取成果标签）
   - `/api/profile/update` - 更新档案字段（支持skills的add/remove操作）

3. **前端布局重构**
   - 从长列表折叠面板改为Dashboard四宫格布局
   - 四个卡片：技能标签、决策锚点、决策里程碑、建议行动

4. **技能标签云**
   - 替换传统输入框，用标签展示技能
   - 支持添加/删除技能
   - 区分AI提取和手动添加（CSS样式区分）

5. **决策锚点卡片**
   - 只展示4个核心字段：目标岗位、期望薪资、意向城市、工作方式
   - 点击即可编辑，简化操作

6. **决策里程碑**
   - 替换传统对话历史列表
   - 从对话记录中提取成果标签（生成简历、技能分析、确定目标岗位等）

7. **档案完善度环形图**
   - 在用户头部区域展示环形进度条
   - 根据已填写字段加权计算完善度
   - 实时更新动画

8. **CSS样式新增**
   - `.completion-ring` - 档案完善度环形图
   - `.dashboard-grid` / `.dashboard-card` - Dashboard布局
   - `.skill-tags` / `.skill-tag` - 技能标签云
   - `.anchor-cards` / `.anchor-card` - 决策锚点卡片
   - `.milestones` / `.milestone` - 决策里程碑

9. **设计文档**
   - 新增 `USER_CENTER_REQUIREMENTS.md` - 传统需求文档
   - 新增 `USER_CENTER_REDESIGN.md` - AI-Native改造方案
   - 新增 `TODO_520.md` - 待办事项记录

---

## 十、设计规范

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

### 侧边面板
- 推理详情面板：320px宽，右侧滑入
- 简历预览面板：500px宽，右侧滑入，iframe渲染
- 执行步骤卡片：左侧彩色图标，右侧内容

### 用户中心（AI-Native风格）
- **设计理念**：AI记忆镜像，非传统表单
- Dashboard四宫格布局：技能标签、决策锚点、里程碑、建议行动
- 档案完善度环形图（加权计算）
- 技能标签云（支持添加/删除）
- 决策锚点卡片（4个核心字段，点击编辑）
- 决策里程碑（从对话提取成果）
- 保留传统折叠面板：基本信息、职业档案（详细表单）

### Logo
- 名称：CareerAI
- 图标：分层几何图形（类似Notion风格）
- 颜色：蓝色 (#0066cc)

### 推理详情面板（内联到对话流）
- 使用时间线样式，左侧圆点图标+连接线
- 支持折叠/展开（点击标题）
- 显示工具调用详情（工具名、参数、输出预览）
- 显示额外信息（置信度、时长、质量分数）
- 实时更新：步骤状态动画显示（running/completed）

### SSE流式响应规范
- 端点：`/api/agent/chat/stream`（POST）
- Content-Type：`text/event-stream`
- 事件类型：
  - `start`：开始事件，包含task_id和conversation_id
  - `step`：步骤更新，包含步骤数据
  - `progress`：进度更新，包含进度消息
  - `done`：完成事件，包含最终结果
  - `error`：错误事件，包含错误信息
- 前端使用 `fetch + ReadableStream` 接收
- 使用 `queue.Queue` 在后台线程和SSE生成器之间传递数据

### 线程安全规范（重要）
1. **共享数据结构选择**
   - ✅ 使用 `queue.Queue`：线程安全，自动处理锁
   - ❌ 避免使用 `list`、`dict`：非线程安全，需要手动加锁

2. **Flask上下文处理**
   - 后台线程无法访问 `current_user`、`current_app`
   - 解决方案：在主线程获取数据，传入后台线程
   - 或使用 `app.app_context()` 创建独立上下文

3. **回调函数安全**
   - 回调函数可能在后台线程中被调用
   - 确保回调函数不访问线程本地变量
   - 使用线程安全的数据结构传递数据

4. **数据库访问**
   - 后台线程中使用数据库前，先调用 `db.session.rollback()`
   - 每个线程使用独立的数据库会话

5. **示例代码**
   ```python
   # ✅ 安全的实现
   import queue
   from threading import Thread
   from flask import current_app
   
   task_queue = queue.Queue()  # 线程安全
   
   def on_step_callback(step_data):
       task_queue.put(step_data)  # 安全
   
   def run_agent():
       with app.app_context():  # 创建独立上下文
           orch = AgentOrchestrator(on_step_callback=on_step_callback)
           result = orch.process(message, user_id)
   
   thread = Thread(target=run_agent)
   thread.start()
   ```

---

## 十一、待办事项

### 10.1 功能扩展
- [x] 简历Agent前端完善（文件上传、简历预览、DOCX导出）
- [x] 面试准备Agent（InterviewAgent）
- [x] 数据扩充（职位60+、技能60+、副业30+）
- [x] 记忆增强（用户档案上下文）
- [x] 多Agent协作（复合意图、任务拆分、链式调用）
- [x] 执行步骤可视化
- [x] 智能体能力优化（提示词、重试、质量验证）
- [x] 多Agent调度优化（并行执行、错误恢复）
- [x] 简历内容与对话分离
- [x] 调度可视化增强（置信度、时长、质量分数）
- [x] 简历生成升级为HTML格式
- [x] 多目标岗位支持
- [x] 职业档案分层重构
- [x] 自动用户信息提取
- [x] 流式响应（SSE）
- [x] MiMoChatOpenAI自定义LLM
- [x] 推理详情面板改进（内联到对话流）
- [x] Orchestrator回调机制（实时步骤更新）
- [x] 用户中心AI-Native改造（Dashboard布局、技能标签云、决策锚点、里程碑）
- [ ] Next Action动态建议（需新增API）
- [ ] 市场趋势分析功能
- [ ] 数据可视化图表（Chart.js）
- [ ] 暗色模式支持

### 10.2 技术优化
- [x] 多智能体编排器重构（DAG依赖图、共享上下文、智能合并、降级策略）
- [x] 多智能体编排器Bug修复（DAG入度、Flask上下文、LLM JSON解析、意图降级）
- [x] 推理详情面板滚动修复
- [x] 前端加载体验优化（进度提示、超时提示）
- [x] SSE流式响应实现（后台线程+队列）
- [x] Orchestrator回调机制（实时步骤更新）
- [x] 线程安全规范（queue.Queue + Flask上下文）
- [x] Agent工具调用回调（当前方案：执行前后发送状态）
- [ ] **实时工具调用步骤**（需LangChain streaming，见12.2）
- [ ] 添加单元测试
- [ ] API限流保护
- [ ] 缓存优化（Redis）
- [ ] 部署文档（Docker）
- [ ] 前端框架迁移（Vue/React）
- [ ] **Celery异步执行方案**（可选，见12.1）

---

## 十二、可选优化方案

### 12.1 Celery异步执行方案

**问题**：复合Agent执行需要16-29秒，前端一直显示加载状态。

**方案**：使用Celery任务队列实现真正的异步执行。

**架构**：
```
前端 → Flask API → 创建Celery任务 → 返回任务ID
                      ↓
                Celery Worker（后台执行Agent）
                      ↓
                Redis（存储任务状态和结果）
                      ↓
前端 ← 轮询任务状态 ← 返回结果
```

**实现步骤**：

1. 安装依赖
```bash
pip install celery redis
```

2. 创建Celery配置 `app/celery_app.py`
```python
from celery import Celery

celery = Celery('career_advisor')
celery.config_from_object({
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0',
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,
})
```

3. 创建异步任务 `app/tasks.py`
```python
from app.celery_app import celery
from app import create_app

@celery.task(bind=True)
def process_agent_task(self, message, user_id, force_agent=None):
    """异步执行Agent任务"""
    app = create_app()
    with app.app_context():
        from app.agents.orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={'status': '正在执行...'})
        
        # 执行Agent
        result = orch.process(message, user_id, force_agent)
        
        return {
            'status': 'completed',
            'result': result
        }
```

4. 修改API端点 `app/routes/api.py`
```python
from app.tasks import process_agent_task

@api_bp.route('/agent/chat/async', methods=['POST'])
@login_required
def agent_chat_async():
    """创建异步任务"""
    data = request.get_json()
    message = data.get('message', '')
    agent_type = data.get('agent_type', 'auto')
    
    force_agent = agent_type if agent_type != 'auto' else None
    
    # 创建Celery任务
    task = process_agent_task.delay(message, current_user.id, force_agent)
    
    return jsonify({
        'code': 200,
        'data': {
            'task_id': task.id,
            'status': 'pending'
        }
    })

@api_bp.route('/agent/task/<task_id>', methods=['GET'])
@login_required
def get_task_status(task_id):
    """查询任务状态"""
    task = process_agent_task.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'status': 'pending',
            'message': '任务等待中...'
        }
    elif task.state == 'PROGRESS':
        response = {
            'status': 'progress',
            'message': task.info.get('status', '执行中...')
        }
    elif task.state == 'SUCCESS':
        response = {
            'status': 'completed',
            'result': task.result
        }
    else:
        response = {
            'status': 'failed',
            'message': str(task.info)
        }
    
    return jsonify({'code': 200, 'data': response})
```

5. 前端轮询 `chat.html`
```javascript
async function sendMessageAsync(message) {
    // 1. 创建任务
    const res = await fetch('/api/agent/chat/async', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ message, agent_type: agentType.value })
    });
    const { task_id } = await res.json();
    
    // 2. 轮询状态
    const pollInterval = setInterval(async () => {
        const statusRes = await fetch(`/api/agent/task/${task_id}`);
        const { data } = await statusRes.json();
        
        if (data.status === 'completed') {
            clearInterval(pollInterval);
            // 显示结果
            displayResult(data.result);
        } else if (data.status === 'failed') {
            clearInterval(pollInterval);
            showError(data.message);
        } else {
            // 更新进度
            updateProgress(data.message);
        }
    }, 1000); // 每秒轮询一次
}
```

**启动命令**：
```bash
# 启动Redis
redis-server

# 启动Celery Worker
celery -A app.celery_app worker --loglevel=info

# 启动Flask
flask run
```

**优缺点**：
| 优点 | 缺点 |
|------|------|
| 真正的异步执行 | 需要安装Redis |
| 前端可以实时显示进度 | 增加系统复杂度 |
| 支持任务重试 | 需要管理Celery Worker |
| 支持任务取消 | 部署更复杂 |

**适用场景**：
- 用户量大（100+并发）
- 需要长时间运行的任务
- 需要任务重试和取消功能

### 12.2 实时工具调用步骤（LangChain Streaming）

**问题**：当前方案只能在工具调用前后发送状态，无法实时显示工具调用过程。

**原因**：LangChain的 `agent.invoke()` 是同步阻塞调用，内部自动执行工具，无法在中间插入回调。

**方案**：使用LangChain的streaming模式，实时获取工具调用步骤。

**实现思路**：

1. **使用 `agent.stream()` 替代 `agent.invoke()`**
```python
# 当前方案（同步阻塞）
result = self.agent.invoke({"messages": [{"role": "user", "content": full_input}]})

# Streaming方案（实时获取）
for chunk in self.agent.stream({"messages": [{"role": "user", "content": full_input}]}):
    # chunk包含中间步骤
    if chunk.get("tool_calls"):
        for tool_call in chunk["tool_calls"]:
            # 实时发送工具调用步骤
            self.on_tool_callback({
                "type": "tool",
                "title": f"调用工具: {tool_call['name']}",
                "detail": f"参数: {tool_call['args']}",
                "status": "running"
            })
```

2. **修改BaseAgent.run()方法**
```python
def run(self, user_input: str, user_id: int = None) -> Dict[str, Any]:
    if not self.agent:
        self.build_agent()
    
    # 使用streaming模式
    output = ""
    steps = []
    
    for chunk in self.agent.stream({"messages": [{"role": "user", "content": full_input}]}):
        # 处理工具调用
        if chunk.get("tool_calls"):
            for tool_call in chunk["tool_calls"]:
                step = {
                    "type": "tool",
                    "title": f"调用工具: {tool_call['name']}",
                    "detail": f"参数: {tool_call['args']}",
                    "status": "running"
                }
                steps.append(step)
                if self.on_tool_callback:
                    self.on_tool_callback(step)
        
        # 处理工具结果
        if chunk.get("tool_results"):
            for result in chunk["tool_results"]:
                # 更新步骤状态为完成
                if steps:
                    steps[-1]["status"] = "completed"
                    steps[-1]["detail"] = result["content"][:100]
                    if self.on_tool_callback:
                        self.on_tool_callback(steps[-1])
        
        # 处理AI回复
        if chunk.get("content"):
            output += chunk["content"]
    
    return {"success": True, "output": output, "intermediate_steps": steps}
```

3. **修改Orchestrator._execute_single_agent()**
```python
def _execute_single_agent(self, agent_name: str, task: str, context: SharedContext) -> AgentResult:
    # 创建Agent时传入回调函数
    agent = self.agents[agent_name]
    
    # 执行Agent（现在会实时发送步骤）
    result = agent.run(enhanced_task, context.user_id)
    
    return AgentResult(...)
```

**改动范围**：
- `base_agent.py` - 修改run()方法，使用streaming模式
- `career_agent.py` - 确保所有Agent支持streaming
- `orchestrator.py` - 确保回调函数正确传递

**优点**：
- 真正的实时工具调用步骤
- 用户可以看到每个工具的调用过程
- 体验更好

**缺点**：
- 需要深入理解LangChain的streaming机制
- 改动较大，风险较高
- 可能需要处理streaming的边界情况

**适用场景**：
- 对用户体验要求高
- 需要展示详细的推理过程
- 有时间进行深入开发

**当前状态**：
- 方案已设计，待实施
- 优先级：中
- 预计工作量：2-3天

---

## 十三、扩展指南

### 新增Agent（5分钟）
1. 创建 `tools/new_tools.py`，定义工具函数
2. 创建 `agents/new_agent.py`，继承BaseAgent，定义提示词和工具
3. `orchestrator.py` 添加注册和关键词
4. `chat.html` 添加Agent选择器选项

### 新增工具（2分钟）
1. 在对应 `tools/xxx_tools.py` 添加函数
2. 在 `get_xxx_tools()` 中注册

### 新增页面（10分钟）
1. 创建 `templates/xxx.html`
2. 创建 `routes/xxx.py`
3. `__init__.py` 注册蓝图

---

## 十三、常见问题

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

### Q7: JavaScript重复声明错误
检查Jinja2模板中 `{% block %}` 是否嵌套正确，避免block内容被渲染两次。

### Q8: MySQL连接超时 "Packet sequence number wrong"
配置数据库连接池：
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 20,
}
```

### Q9: "Can't reconnect until invalid transaction is rolled back"
在所有DB查询前添加 `db.session.rollback()`：
```python
try:
    db.session.rollback()
except Exception:
    pass
result = Model.query.filter_by(...).first()
```

### Q10: mimo模型 "reasoning_content must be passed back"
使用MiMoChatOpenAI（app/agents/custom_llm.py），自动处理reasoning_content传递。

### Q11: Stream endpoint KeyError
使用 `result.get("output", "")` 而非 `result["output"]`，防止key不存在时崩溃。

### Q12: Flask应用上下文在线程中丢失
并行执行Agent时，ThreadPoolExecutor中的线程没有Flask应用上下文。
解决方案：为每个线程创建独立的应用上下文。
```python
from flask import current_app
app = current_app._get_current_object()

def execute_in_context(agent_name, task, ctx, app_obj):
    with app_obj.app_context():
        return self._execute_with_retry(agent_name, task, ctx)

with ThreadPoolExecutor() as executor:
    executor.submit(execute_in_context, agent, task, context, app)
```

### Q13: LLM返回非JSON格式导致解析失败
mimo模型有时返回` ```json ``` `包裹的内容或空内容。
解决方案：使用正则提取JSON，容错解析。
```python
import re
json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
if json_match:
    content = json_match.group(1).strip()
# 再尝试解析
```

### Q14: 后台线程无法访问current_user
Flask的current_user是线程本地变量，后台线程无法访问。
解决方案：在主线程获取user_id，传入后台线程使用。
```python
user_id = current_user.id  # 主线程获取
def run_agent():
    result = orchestrator.process(message, user_id, force_agent)  # 传入user_id
```

### Q15: Flask SSE无法实时推送（已解决）
~~Flask的Response是同步阻塞的，在streaming期间无法发送事件。~~
**解决方案**：使用后台线程+队列模式
- 后台线程执行orchestrator，通过回调函数将步骤放入queue.Queue
- SSE生成器从队列读取步骤并yield给前端
- queue.Queue是线程安全的，无需额外加锁

### Q16: SSE流式响应实现
端点：`/api/agent/chat/stream`（POST）
```python
# 后端
def on_step_callback(step_data):
    task_queue.put(step_data)  # 线程安全

def run_agent():
    with app.app_context():
        orch = AgentOrchestrator(on_step_callback=on_step_callback)
        result = orch.process(message, user_id, force_agent)

# 前端
const response = await fetch('/api/agent/chat/stream', {...});
const reader = response.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    // 解析SSE事件并更新UI
}
```

### Q17: 线程安全问题
回调函数在后台线程中被调用，需确保线程安全。
**安全方案**：
- 使用 `queue.Queue`（线程安全）
- 避免使用 `list`、`dict`（非线程安全）
- Flask上下文：使用 `app.app_context()` 创建独立上下文
- 数据传递：主线程获取数据，传入后台线程

---

### 2026-05-27 完成功能

1. **Next Action动态建议功能**
   - 新增 `/api/profile/next-actions` 端点
   - 根据用户档案和对话历史智能推荐下一步行动
   - 支持10种行动类型：完善档案、确定目标岗位、添加技能、生成简历、技能分析、面试准备、探索副业、添加项目、设定目标、开始对话
   - 前端动态渲染行动卡片，带图标和颜色
   - 支持两种跳转方式：chat（自动发送消息）、navigate（滚动到页面区域）

2. **5个智能体全面优化**

   **Orchestrator优化：**
   - 意图识别增强：关键词数量增加50%，支持上下文切换检测
   - Agent自动切换：根据对话历史自动选择最合适的Agent
   - 复合意图优化：降低触发阈值（0.3→0.25），更容易识别复合意图
   - 超时时间：60秒→120秒

   **BaseAgent优化：**
   - 上下文增强：更好地利用用户档案，限制长度避免token溢出
   - 输出格式标准化：自动检测并添加Markdown格式
   - 错误处理：友好的中文错误提示，区分超时/网络/认证等错误
   - 质量验证：增强版验证，返回详细分数和问题列表
   - 记忆窗口：10→15轮，记住更多对话历史

   **5个Agent提示词优化：**
   - CareerAgent：添加输出格式规范、搜索结果格式、示例更详细
   - SkillAgent：添加学习路径格式、差距分析格式、学习建议模板
   - SideJobAgent：添加ROI计算格式、风险提醒模板、三档收入预期
   - ResumeAgent：简化目标岗位处理流程、明确简历板块结构
   - InterviewAgent：添加面试题格式、自我介绍结构、薪资谈判话术

   **前端体验优化：**
   - 进度提示："正在分析您的问题"替代"正在思考中"
   - 错误提示：区分超时/网络/通用错误，给出具体建议
   - Agent记忆：记住上一次使用的Agent，实现上下文自动切换
   - 超时时间：60秒→120秒

3. **Agent专业图标系统**
   - 5个Agent专业SVG图标设计
     - CareerAgent（职业规划）- 指南针图标（蓝色#3b82f6）
     - SkillAgent（技能分析）- 学习图标（紫色#8b5cf6）
     - SideJobAgent（副业分析）- 钱包图标（绿色#10b981）
     - ResumeAgent（简历优化）- 文档图标（橙色#f59e0b）
     - InterviewAgent（面试教练）- 话筒图标（粉色#ec4899）
   - 自定义Agent选择器（带图标的下拉菜单）
   - 推理详情面板显示Agent图标
   - 子任务列表显示Agent图标
   - 执行步骤显示Agent图标

4. **Bug修复**
   - 修复用户中心表单字段显示"value=None"问题
   - 使用`or ''`过滤器处理None值

5. **Chrome DevTools MCP配置**
   - 配置Chrome DevTools MCP服务器用于自动化测试
   - 配置文件位置：`D:/Opencode_workplace/.opencode/opencode.json`

---

### 2026-05-27 完成功能（前端重构+项目结构优化）

1. **前端Google Material风格重构**
   - 配色体系：引入Google经典蓝(#1a73e8)，纯白背景+极淡灰
   - 对话界面：去除毛玻璃和渐变色，用户消息右对齐浅灰气泡，AI消息去气泡化纯文本
   - 输入框：浮动药丸状(Pill-shape)，聚焦时浅色阴影，无边框设计
   - 按钮：全圆角药丸形设计，Material阴影
   - 侧边栏：圆角菜单项，Hover高亮背景
   - 字体：加入Google Sans和Roboto字体
   - 滚动条：轻量透明，Hover时变色
   - 欢迎页：用户名问候语，3列Grid布局欢迎卡片

   **右侧面板重构：**
   - 推理详情面板：悬浮抽屉式设计(Floating Drawer)，圆角+阴影
   - 简历预览面板：改为居中弹出的模态框，背景半透明+模糊效果
   - 支持放大缩小功能(50%-200%)
   - 三种下载格式：HTML、PDF、图片

2. **项目结构重构（services层）**
   - `routes/api.py`：1488行 → 348行（只保留路由定义）
   - 新增 `services/chat_service.py`：对话/流式/异步/任务状态（445行）
   - 新增 `services/history_service.py`：历史记录CRUD（187行）
   - 新增 `services/user_service.py`：用户名/密码/头像/统计（136行）
   - 新增 `services/resume_service.py`：简历上传/下载（196行）
   - 新增 `services/profile_service.py`：档案完善度/里程碑/建议（333行）
   - 所有API端点路径不变，前端无需改动

3. **简历下载功能**
   - HTML下载：正常工作
   - DOCX下载：正常工作
   - PDF下载：使用前端html2canvas + jsPDF，中文完美支持（2026-06-02修复）
   - 图片下载：使用html2canvas前端截图，正常工作

4. **输入框优化**
   - 去掉背后的长方形背景框
   - 圆角药丸直接悬浮在聊天界面上
   - 透明背景，无边框

---

### 2026-06-02 完成功能

1. **PDF下载功能修复（中文乱码问题彻底解决）**
   - **问题**：xhtml2pdf生成PDF中文显示乱码
   - **解决方案**：改为前端生成PDF（html2canvas + jsPDF）
   - **技术实现**：
     - 引入jsPDF库（unpkg CDN）
     - 使用html2canvas将HTML简历渲染为Canvas
     - 使用jsPDF将Canvas转换为PDF
     - 支持自动分页处理（A4尺寸）
   - **修改文件**：
     - `base.html`：添加jsPDF CDN引入
     - `chat.html`：新增`downloadResumeAsPDF()`函数，修改`downloadFromPanel()`和`downloadResume()`函数
   - **优点**：
     - 中文完美支持（由浏览器渲染）
     - 所见即所得（与预览效果一致）
     - 无后端依赖，纯前端方案
   - **Bug修复**：
     - 修复cdnjs jsPDF CDN被ORB阻止问题（改用unpkg）
     - 优化临时容器处理（避免html2canvas对隐藏元素失败）
     - 增加jsPDF加载检查和错误处理

2. **前端PDF生成技术栈**
   - **html2canvas**：将HTML/DOM渲染为Canvas
   - **jsPDF**：将Canvas/图片转换为PDF
   - **CDN**：
     - html2canvas: `https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js`
     - jsPDF: `https://unpkg.com/jspdf@2.5.2/dist/jspdf.umd.min.js`

---

### 2026-06-03 完成功能（前端重构）

1. **CSS模块化拆分**
   - 将`style.css`（3465行）拆分为6个模块文件：
     - `base.css`（552行）：全局变量、重置、按钮、表单、落地页样式
     - `chat.css`（580行）：侧边栏、对话界面、消息气泡、输入框
     - `components.css`（620行）：推理时间线、执行步骤、Agent图标、滚动条
     - `profile.css`（380行）：用户中心、技能标签云、决策锚点
     - `resume.css`（200行）：简历预览模态框
     - `modal.css`（110行）：弹窗、Toast提示
   - `base.html`更新为引入6个CSS模块文件

2. **JavaScript提取整理**
   - 从`chat.html`提取内联JS到`chat.js`（750行）
     - 聊天页面所有逻辑：消息发送、SSE流式响应、简历预览、下载功能
     - Agent选择器、推理时间线构建、执行步骤更新
   - 从`profile.html`提取内联JS到`profile.js`（380行）
     - 用户中心逻辑：头像上传、密码修改、统计加载
     - 技能管理、决策锚点编辑、Next Actions渲染
   - `chat.html`：1731行 → 300行（减少83%）
   - `profile.html`：1556行 → 1085行（减少30%）

3. **简历预览优化**
   - 修复双重滚动条问题
   - 去掉`.resume-paper-container`子容器
   - 简历预览直接填满模态框

4. **文件结构优化**
   ```
   app/static/css/
   ├── base.css          - 全局变量、重置、基础样式
   ├── chat.css          - 聊天页面样式
   ├── components.css    - 通用组件、推理时间线
   ├── profile.css       - 用户中心样式
   ├── resume.css        - 简历预览样式
   ├── modal.css         - 弹窗、Toast
   └── style.css         - 备份原文件

   app/static/js/
   ├── main.js           - 通用脚本
   ├── modal.js          - 弹窗组件
   ├── chat.js           - 聊天页面逻辑
   └── profile.js        - 用户中心逻辑
   ```

5. **交互与动效体验升级 (Premium Interactive Animations)**
   - **欢迎卡片 3D 视差倾斜效果**：在 `chat.js` 和 `chat.css` 中，实现欢迎问题卡片随鼠标移动的 3D 旋转及微缩放动画，当鼠标移出时，配合 cubic-bezier 过渡平滑回弹。
   - **文件拖拽磁吸 snap 上传效果**：实现文件拖入窗口时，输入框胶囊轻微膨胀高亮（`.drag-over`），拖入胶囊热区时触发带有虚线边框和浮起动画的磁吸状态（`.drag-snap`）。
   - **Accordion 折叠推理步骤面板**：推理历史或当前生成时，点击头部通过切换 `.collapsed` 类名控制 max-height 属性（0 到 800px），同时旋转折叠图标；首次加载 token 流时自动折叠。
   - **Staggered 消息气泡级联滑入**：重写 `.message` 默认动画为 `msgEntrance` 弹簧动画（0.95 缩放搭配 translateY 平移），利用 JS 设置 CSS 变量 `--msg-index`，使用 `animation-delay: calc(var(--msg-index, 0) * 0.08s)` 实现列表层叠滑入。
   - **环形完善度图表绘制与数字跳动**：在 `profile.js` 和 `style.css` 中引入 `animateNumber` 缓动函数（easeOutExpo），在页面加载时完成环形 SVG dasharray 渐进绘制与百分比数字从 0% 起跳。

---

**最后更新**: 2026-06-10
**项目状态**: P0+P1优化完成，端到端测试通过，可进行答辩演示
**当前分支**: antigravity-build

### 2026-06-10 完成功能（Bug修复与优化）

1. **Orchestrator模块化重构**
   - 将orchestrator.py拆分为8个独立模块（intent/planner/executor/merger/quality/recovery/context/data_types）
   - 遵循单一职责原则，提升代码可维护性

2. **流式输出修复**
   - 修复agent.stream()在工具调用时返回空内容的问题
   - 改回agent.invoke()并在完成后发送最终内容
   - 修复复合意图处理时重复输出的问题

3. **工具调用信息显示修复**
   - 保存时从execution_steps和intermediate_steps中提取工具调用信息
   - 加载时正确解析tools_used字段
   - 修复复合意图处理时使用工具板块不显示的问题

4. **数据库连接修复**
   - 在工具函数开头添加db.session.rollback()防止连接池问题
   - 修复job_skills表查询错误

5. **推理详情面板优化**
   - 删除推理过程板块，只保留执行流程和使用工具
   - 添加panel-content类支持滚动

6. **落地页修正**
   - 将智能体数量从3个改为5个

7. **项目结构整理**
   - 删除.idea/.pytest_cache/test_screenshots等无用文件
   - 删除重复的记忆文件和过时的设计文档

8. **单元测试**
   - 重新创建test_intent.py，10个测试用例全部通过

9. **端到端测试**
   - 测试用户注册、登录、单Agent对话、复合Agent对话
   - 测试切换界面返回、工具调用显示
   - 所有核心功能正常

---

## 十四、待开发/待修复

### 14.1 ~~PDF下载中文乱码~~（已解决）
- **问题**：使用xhtml2pdf生成的PDF文件中文显示为乱码
- **原因**：xhtml2pdf对中文字体支持不完善
- **尝试过的方案**：
  - weasyprint：需要系统级依赖（GTK），Windows上安装困难
  - fpdf2：需要手动注册中文字体，配置复杂
  - xhtml2pdf：纯Python但中文乱码
- **最终解决方案**：前端html2canvas + jsPDF
  - 优点：中文完美支持、所见即所得、无后端依赖
  - 实现：2026-06-02
- **当前状态**：✅ 已解决

### 14.2 后台运行任务的实时进度拉回与重连 (Live Task Resumption & Polling)
- **目标**：在用户切换会话或刷新页面导致连接断开后，后台任务仍能持续运行并最终入库。同时，当用户切回处于"生成中"的会话时，前端页面应能够自动"认领"后台任务，重新唤醒 Loading 状态并实时显示中间推理步骤（Timeline）和最新的生成内容。
- **当前状态**：⏳ 待开发（已实现"切换页面后台任务不中断并默默入库"的功能，但"切回会话重新拉起轮询同步进度"的 UI 部分因体验和调试需要已暂时回滚，留待后续迭代开发）

---

## 十五、分支合并记录

### 2026-06-10 合并 antigravity-build 到 main

**合并时间**：2026-06-10
**合并方式**：--no-ff（保留分支历史）

**主要变更**：
- P0优化：Orchestrator模块化、Token级流式输出、Docker部署、README重写
- P1优化：结构化输出协议、数据可视化、Onboarding引导、模拟面试、单元测试、暗色模式
- Bug修复：流式输出、工具调用显示、数据库连接、复合意图处理等

**删除的文件**：
- BRANCH_MEMORY_ANTIGRAVITY_BUILD.md（重复）
- DEVELOPMENT_MEMORY_ANTIGRAVITY_BUILD.md（重复）
- DESIGN.md（过时）
- USER_CENTER_REDESIGN.md（过时）
- USER_CENTER_REQUIREMENTS.md（过时）

**当前状态**：项目已完成P0+P1优化，端到端测试通过，可进行答辩演示

---

## 十六、mimobuild分支开发记录

### 2026-06-17 mimobuild分支创建与全面优化

**分支目的**：将项目打造成面试简历加分项，突出AI工具使用能力，部署上线供他人访问

**合并时间**：2026-06-17
**分支状态**：开发中

#### 16.1 代码审查与Bug修复

**前端修复（7项）**：
1. **CSS语法损坏修复** - chat.css:687 `@keyframes` 块被破坏，删除损坏的重复代码
2. **Jinja2模板安全注入** - chat.html:300 使用 `| tojson` 过滤器安全嵌入JS字符串
3. **移动端响应式布局** - chat.css:1362 侧边栏隐藏时移除margin-left
4. **navbar空指针异常** - main.js:31 添加null检查保护
5. **简历内容误检测** - chat.js:516 移除过于宽泛的 `<div` 匹配规则
6. **内存泄漏修复** - chat.js:432 保留最近5个简历内容，自动清理旧数据
7. **废弃代码清理** - chat.js:971 清理引用不存在的 `#reasoningPanel`

**后端修复（10项）**：
1. **SECRET_KEY安全配置** - config.py:8 使用 `secrets.token_hex(32)` 动态生成
2. **生产环境debug模式** - run.py:13 从环境变量读取，生产环境默认关闭
3. **API请求验证** - api.py 所有POST端点添加 `request.get_json()` null检查
4. **注册输入验证** - auth.py:22-24 添加完整的邮箱、密码、用户名验证
5. **登出CSRF漏洞** - auth.py:64 改为POST请求 + 表单提交
6. **历史记录分页** - career.py:109 添加 `.limit(50)` 防止内存溢出
7. **类型转换异常** - career.py:27,46,50 添加try-except处理
8. **消息长度限制** - api.py 添加 `MAX_MESSAGE_LENGTH` 配置
9. **专业日志系统** - 创建 `logging_config.py` 模块替代print
10. **安全配置增强** - config.py 添加Cookie安全和上传限制

#### 16.2 部署配置

**新增文件**：
- `.env.example` - 环境变量配置示例
- `Dockerfile` - Docker镜像配置
- `docker-compose.yml` - 一键部署配置（含Nginx、MySQL）
- `nginx.conf` - Nginx反向代理配置
- `DEPLOYMENT.md` - 详细部署指南
- `app/logging_config.py` - 日志配置模块

**依赖更新**：
- requirements.txt 添加 `gunicorn>=21.2.0`

#### 16.3 Git配置优化

**`.gitignore` 更新**：
- 添加日志文件排除 (*.log, logs/)
- 添加虚拟环境排除 (venv/, .venv/)
- 添加上传文件排除 (app/static/uploads/avatars/*)
- 添加临时文件排除 (*.tmp, *.bak)

#### 16.4 当前状态

**已完成**：
- ✅ 22项Bug修复和安全加固
- ✅ 部署配置（Docker、Nginx、日志）
- ✅ Git配置优化
- ✅ API限流配置（flask-limiter）
- ✅ 数据库索引优化（7个索引）
- ✅ 备份脚本（MySQL + ChromaDB）
- ✅ 恢复脚本
- ✅ 健康检查脚本
- ✅ Docker健康检查配置
- ✅ 日志轮转配置

**待完成**：
- ⏳ 前端UI/UX优化（需要更精细的设计调整）
- ⏳ Redis缓存配置（可选）
- ⏳ CDN加速配置（可选）

---

## 十七、小主机部署记录

### 2026-06-17 Deepin小主机部署

**部署环境**：
- 硬件：富士通Q558（i3-9100T, 8G RAM, 256G SSD）
- 系统：Deepin Linux
- IP地址：10.43.84.249
- 部署方式：Docker + docker-compose

**部署过程**：

1. **代码推送到GitHub**
   - 仓库地址：https://github.com/eayi-code/ai_career_advisor
   - 分支：main

2. **小主机环境配置**
   - 安装Docker：`sudo apt install docker.io`
   - 安装docker-compose：升级到v2.24.5
   - 配置SSH：开启root登录和密码认证

3. **Docker镜像加速**
   - 配置国内镜像源（docker.1ms.run, dockerhub.icu等）
   - 解决Docker Hub被墙问题

4. **数据库初始化**
   - 进入容器：`docker exec -it ai_career_advisor-app-1 bash`
   - 执行迁移：`flask db upgrade`
   - 初始化数据：`python init_data.py`

5. **环境变量配置**
   - SECRET_KEY：自动生成
   - DATABASE_URL：mysql+pymysql://root:password@db:3306/career_advisor
   - OPENAI_API_KEY：使用小米API
   - OPENAI_BASE_URL：https://token-plan-cn.xiaomimimo.com/v1
   - OPENAI_MODEL：mimo-v2.5-pro
   - VISION_API_KEY：使用MiniMax API
   - VISION_MODEL：MiniMax-M3

**部署命令**：

```bash
# 克隆项目
cd ~
git clone https://github.com/eayi-code/ai_career_advisor.git
cd ai_career_advisor

# 配置环境变量
cp .env.example .env
nano .env  # 填入配置

# 启动服务
sudo docker-compose -f docker-compose.lan.yml up -d

# 初始化数据库
sudo docker exec -it ai_career_advisor-app-1 bash
flask db upgrade
python init_data.py
exit

# 重启服务
sudo docker-compose -f docker-compose.lan.yml restart app
```

**访问地址**：
- 局域网：http://10.43.84.249:5000
- 手机访问：连接同一WiFi，浏览器输入地址

**常见问题**：

1. **docker-compose版本太旧**
   - 症状：`Not supported URL scheme http+docker`
   - 解决：升级到v2.24.5

2. **Docker Hub被墙**
   - 症状：下载镜像超时
   - 解决：配置国内镜像加速器

3. **数据库表不存在**
   - 症状：`Table 'career_advisor.users' doesn't exist`
   - 解决：进入容器执行`flask db upgrade`

4. **sudo需要密码**
   - 解决：使用`echo "password" | sudo -S command`

**运维命令**：

```bash
# 查看服务状态
sudo docker-compose -f docker-compose.lan.yml ps

# 查看日志
sudo docker-compose -f docker-compose.lan.yml logs -f

# 重启服务
sudo docker-compose -f docker-compose.lan.yml restart

# 更新代码
cd ~/ai_career_advisor
git pull
sudo docker-compose -f docker-compose.lan.yml up -d --build

# 进入容器
sudo docker exec -it ai_career_advisor-app-1 bash

# 备份数据库
sudo docker exec ai_career_advisor-db-1 mysqldump -u root -p career_advisor > backup.sql
```

**数据持久化**：
- MySQL数据：`ai_career_advisor_mysql_data` 卷
- ChromaDB数据：`ai_career_advisor_chroma_data` 卷
- 应用日志：`ai_career_advisor_app_logs` 卷
- 备份目录：`ai_career_advisor_backups` 卷

**下一步**：
- 配置Cloudflare Tunnel实现外网访问
- 配置自动备份定时任务
- 配置HTTPS证书

---

## 十八、部署文档

### 已创建的文档

1. **DEPLOYMENT.md** - 详细部署指南
2. **DEPLOY_DEEPIN.md** - Deepin系统部署指南
3. **DEPLOY_GUIDE.md** - 部署与运维指南（含求职技能点）

### 文档内容概览

| 文档 | 内容 |
|------|------|
| DEPLOYMENT.md | Docker部署、环境配置、常见问题 |
| DEPLOY_DEEPIN.md | Deepin系统特定部署步骤 |
| DEPLOY_GUIDE.md | 核心原理、部署流程、网络配置、运维命令、求职技能点 |

### 求职技能点

| 技能 | 说明 |
|------|------|
| Docker容器化 | 使用Docker部署Flask+MySQL应用 |
| Docker Compose | 多容器编排和管理 |
| Nginx反向代理 | 负载均衡和静态文件服务 |
| Linux运维 | 命令行操作、服务管理 |
| Git版本控制 | 代码管理和团队协作 |
| CI/CD | 持续集成/持续部署 |
| 内网穿透 | Cloudflare Tunnel配置 |
| 数据库管理 | MySQL备份恢复 |

---

## 十九、PWA配置

### 已完成

- ✅ manifest.json - PWA应用清单
- ✅ sw.js - Service Worker（离线缓存）
- ✅ icon-*.png - 8种尺寸的应用图标
- ✅ base.html - 添加PWA meta标签和Service Worker注册

### PWA功能

| 功能 | 说明 |
|------|------|
| 添加到主屏幕 | 手机用户可像APP一样使用 |
| 离线访问 | 静态资源缓存，断网也能访问 |
| 全屏模式 | 隐藏浏览器地址栏 |
| 启动画面 | 类似原生APP的启动体验 |

---

## 二十、当前状态总结

### 已完成

- ✅ 22项Bug修复和安全加固
- ✅ 部署配置（Docker、Nginx、日志）
- ✅ Git配置优化
- ✅ API限流配置（flask-limiter）
- ✅ 数据库索引优化（7个索引）
- ✅ 备份脚本（MySQL + ChromaDB）
- ✅ 恢复脚本
- ✅ 健康检查脚本
- ✅ Docker健康检查配置
- ✅ 日志轮转配置
- ✅ PWA配置
- ✅ Deepin小主机部署
- ✅ 部署文档
- ✅ 移动端全面优化（7个布局Bug + 视觉打磨 + 触摸优化）
- ✅ SSL证书自动修复（certifi跨平台）
- ✅ 性能优化（意图识别缓存 + 并行执行 + Prompt精简）
- ✅ 聊天界面简化（移除内联推理时间线）

### 待完成

- ⏳ Redis缓存配置（可选）
- ⏳ CDN加速配置（可选）
- ⏳ Cloudflare Tunnel配置（外网访问）
- ⏳ 自动备份定时任务
- ⏳ HTTPS证书配置

---

## 二十一、移动端适配开发记录

### 2026-06-18 移动端响应式适配

**目标**：让项目在手机上正常显示和使用

**已完成的工作**：

1. **创建移动端CSS文件**
   - 新建 `app/static/css/mobile.css`
   - 使用媒体查询隔离移动端和桌面端样式
   - 使用 `.desktop-only` 和 `.mobile-plus-btn` 类控制显示

2. **修复侧边栏问题**
   - 问题：`chat.css` 中的 `display: none` 覆盖了 `mobile.css` 的 `transform` 样式
   - 解决：删除 `chat.css` 中的移动端媒体查询，统一在 `mobile.css` 中管理
   - 侧边栏改为抽屉式，使用 `transform: translateX(-100%)` 隐藏

3. **添加汉堡菜单**
   - 在 `chat.html` 和 `profile.html` 添加汉堡菜单按钮
   - 添加侧边栏遮罩层
   - 实现点击遮罩层关闭侧边栏

4. **添加+号菜单**
   - 输入框左侧添加+号按钮（移动端显示）
   - 点击弹出菜单，包含"上传文件"和"切换智能体"
   - 桌面端隐藏+号按钮，显示原有的Agent选择器和上传按钮

5. **优化输入框**
   - 悬浮在底部（position: fixed）
   - 毛玻璃背景效果
   - 发送按钮改为圆形蓝色
   - 消息区域留出底部空间

6. **参照ChatGPT/Gemini风格重构**
   - 配色：纯白背景 + 浅灰消息气泡 + 蓝色强调
   - 消息气泡：用户右对齐浅灰，AI左对齐无背景
   - 入场动画：从下方淡入
   - 侧边栏：300px宽，从左侧滑入

**遇到的问题**：

1. **CSS优先级冲突**：`chat.css` 的 `display: none` 覆盖了 `mobile.css` 的样式
2. **浏览器缓存**：修改CSS后需要强制刷新才能看到效果
3. **输入框布局**：发送按钮和Agent选择器的大小需要反复调整
4. **历史对话加载**：数据库中有完整消息，但用户反馈只显示第一条（可能是缓存问题）

**待优化**：

- ⏳ 移动端UI效果还需进一步打磨
- ⏳ 需要参照taste-skill的设计规范进行更精细的优化
- ⏳ 用户交互体验（触摸反馈、动画流畅度）
- ⏳ 业务场景适配（欢迎页面、对话历史、用户中心）

**相关文件**：

| 文件 | 修改内容 |
|------|----------|
| `app/static/css/mobile.css` | 新建，移动端响应式样式 |
| `app/static/css/chat.css` | 删除移动端媒体查询，添加mobile-plus-btn隐藏样式 |
| `app/templates/base.html` | 引入mobile.css |
| `app/templates/career/chat.html` | 添加汉堡菜单、遮罩层、+号菜单 |
| `app/templates/career/profile.html` | 添加汉堡菜单、遮罩层、移动端顶部栏 |
| `app/templates/index.html` | 添加汉堡菜单 |
| `app/static/js/chat.js` | 添加toggleSidebar、toggleMobileMenu等函数 |
| `app/static/js/main.js` | 添加toggleNavMenu函数 |

**设计参考**：

- ChatGPT移动端：简洁聊天界面、底部输入框、圆形发送按钮
- Gemini移动端：消息气泡样式、侧边栏抽屉
- taste-skill：设计规范（配色、字体、动画、交互）

**最后更新**: 2026-06-19
**当前状态**: 移动端全面优化完成，性能优化完成，UI简化完成

---

## 二十二、移动端全面优化与性能优化

### 2026-06-19 移动端优化 + 性能优化 + UI简化

**目标**：修复移动端布局Bug、优化响应速度、简化聊天界面

#### 22.1 移动端布局Bug修复（7项）

| Bug | 问题 | 修复 |
|-----|------|------|
| Bug1 | profile页 `.profile-header` 负margin导致横向溢出 | mobile.css重置 `.main-content` padding + 收口 `.profile-header/info/content` |
| Bug2 | `.anchor-cards` 在mobile.css被强制改回2列 | 改为 `1fr` 单列 |
| Bug3 | 薪资区间双数字框在窄屏并排 | profile.html抽出 `.salary-range` class，移动端纵向堆叠 |
| Bug4 | `.resume-paper` 的3rem padding在全屏预览挤压内容 | mobile.css覆盖为1rem |
| Bug5 | `.modal-*` / `.toast*` 零移动端适配 | modal.css补768px媒体查询块 |
| Bug6 | mobile.css缓存版本 `?v=1.0.0` 与其他不同步 | base.html全部bump到 `?v=1.0.4` |
| Bug7 | chat.css的 `@keyframes glowGold` 有乱码残留+重复定义 | 删除损坏段，保留唯一完整版 |

#### 22.2 移动端视觉与交互打磨

**对话页**：
- 侧边栏宽度改为 `min(300px, 85vw)`
- 发送按钮用SVG上箭头图标替代 `::after` 三角hack
- 气泡配色保持（用户浅灰 #F0F0F0，AI透明）

**用户中心**：
- 折叠面板、Next Action卡片padding收紧
- 决策锚点改为单列
- 薪资输入框移动端纵向堆叠

**落地页**：
- hero标题下限收紧到 `clamp(36px,9vw,56px)`
- 防≤360px屏溢出

**登录页**：
- `#toastContainer` 加 `left/right` 兜底防右侧溢出

**执行步骤/时间线**：
- 推理面板内执行步骤、时间线字号/padding/换行适配窄屏

#### 22.3 触摸与无障碍

- 触摸目标列表扩充到18类元素（min 44px）
- 统一 `:active scale(0.98)` 按压反馈
- `prefers-reduced-motion` 覆盖面扩充到所有新增动画元素

#### 22.4 SSL证书自动修复

**问题**：系统环境变量 `SSL_CERT_FILE` 指向不存在的miniconda证书路径，导致AI调用失败

**修复**：
- `config.py`：自动检测坏SSL路径，用certifi跨平台修复
- `load_dotenv()` 不带 `override`，不影响Docker部署

#### 22.5 性能优化（意图识别 + 并行执行 + Prompt精简）

**意图识别优化**：
- 添加意图缓存（最近100条结果，相同查询0ms）
- 动态置信度阈值：有复合意图指示词时降低到0.25
- 主意图优先逻辑（>55%且领先15%时直接使用）
- 复合意图指示词检测（"并"、"和"、"同时"等）

**并行执行优化**：
- 常见复合意图硬编码拆分（避免LLM调用）
  - career + resume
  - career + interview
  - career + skill
  - resume + interview
  - career + resume + interview

**Prompt优化**：
- 意图识别prompt精简（减少~60% token）
- 任务拆分prompt精简（减少~50% token）
- 结果合并prompt精简（减少~40% token）

**预期效果**：
- 简单单意图：无LLM意图识别调用，响应时间减少10-15秒
- 常见复合意图：无LLM任务拆分调用，响应时间减少10-15秒
- 相同查询：缓存命中，0ms

#### 22.6 UI简化（聊天界面）

**问题**：
- 聊天气泡内的推理时间线和右侧推理面板重复展示相同内容
- 加载状态显示冗余

**优化**：
- 移除聊天气泡内的内联推理时间线（reasoning-timeline）
- 简化为纯进度指示器（loading dots + 动态文字）
- 加载文字随步骤更新：正在思考... → 意图分析... → 调用Agent...
- 保留右侧推理面板供需要查看详情的用户

#### 22.7 提交记录

| Commit | 内容 |
|--------|------|
| `fb45cd0` | 移动端优化 + SSL修复 |
| `cc48c57` | 性能优化（意图识别+并行执行+Prompt精简） |
| `6b75500` | 修复复合意图识别问题 |
| `bbd0937` | 简化聊天气泡加载状态，移除内联推理时间线 |

**相关文件**：

| 文件 | 修改内容 |
|------|----------|
| `app/static/css/mobile.css` | +197行，全面移动端适配 |
| `app/static/css/modal.css` | +54行，弹窗/Toast移动端适配 |
| `app/static/css/chat.css` | -9行，删除损坏的glowGold代码 |
| `app/templates/base.html` | CSS版本号统一到v=1.0.4 |
| `app/templates/career/profile.html` | 薪资容器class化+基础样式 |
| `app/templates/index.html` | 落地页hero标题收紧+间距优化 |
| `app/config.py` | SSL证书自动检测修复 |
| `app/agents/orchestrator.py` | 意图识别优化+并行执行优化+Prompt精简 |
| `app/static/js/chat.js` | 移除内联推理时间线，简化加载状态 |
