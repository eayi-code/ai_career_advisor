# 用户中心改造方案（AI-Native版）

## 一、设计理念

**从"表单收集"到"AI记忆镜像"**

用户中心不是一个填表的地方，而是AI对用户的认知面板。用户不需要主动填写，AI在对话中自动提取、沉淀信息。

---

## 二、现有能力盘点

### 已具备的能力（可直接复用）
| 能力 | 实现位置 | 状态 |
|------|----------|------|
| 自动信息提取 | orchestrator._extract_user_info() | ✅ 已实现 |
| 用户档案存储 | UserProfile模型 | ✅ 已实现 |
| 对话历史保存 | AnalysisHistory模型 | ✅ 已实现 |
| 技能/职位/副业数据 | jobs/skills/side_jobs表 | ✅ 已实现 |
| 5个专业Agent | career_agent.py | ✅ 已实现 |

### 需要新增的能力
| 能力 | 复杂度 | 优先级 |
|------|--------|--------|
| 档案完善度计算 | 低 | P0 |
| 双模式切换（求职/副业） | 中 | P0 |
| 技能标签可视化 | 低 | P1 |
| 决策锚点卡片 | 低 | P1 |
| 对话成果总结 | 中 | P1 |
| 能力雷达图 | 中 | P2 |
| 自然语言修改档案 | 高 | P2 |
| Next Best Action | 高 | P2 |

---

## 三、页面布局改造

### 原布局（传统表单式）
```
用户头部
├─ 使用统计（折叠）
├─ 对话历史（折叠）
├─ 基本信息（折叠）
└─ 职业档案（折叠，大量表单）
```

### 新布局（AI-Native Dashboard）
```
┌─────────────────────────────────────────────────────────┐
│  用户头部（头像 + 名称 + 档案完善度环形图）              │
├─────────────────────────────────────────────────────────┤
│  [求职突破模式] ← Toggle → [副业探索模式]               │
├────────────────────────────────┬────────────────────────┤
│  左侧：AI记忆管理              │  右侧：决策产出         │
│  ├─ 技能标签云                 │  ├─ 决策里程碑          │
│  ├─ 决策锚点卡片               │  ├─ Next Best Action   │
│  └─ 目标岗位列表               │  └─ 对话摘要           │
├────────────────────────────────┴────────────────────────┤
│  底部：使用统计 + 对话历史（简化版）                     │
└─────────────────────────────────────────────────────────┘
```

---

## 四、各模块详细设计

### 模块1：用户头部 + 档案完善度

**现有能力**：用户头像、用户名、统计数字已有

**改造点**：
- 新增"档案完善度"环形进度条
- 计算逻辑：统计已填写字段 / 总字段数

**字段权重**：
```python
PROFILE_FIELDS = {
    # 基础信息 (40%)
    'education': 5,
    'major': 5,
    'work_experience': 5,
    'current_job_title': 5,
    'skills': 10,
    
    # 求职意向 (40%)
    'target_job_title': 10,
    'target_industry': 5,
    'target_salary_min': 5,
    'location_preference': 5,
    'job_search_status': 5,
    'work_preference': 5,
    'company_type_preference': 5,
    
    # 扩展信息 (20%)
    'projects': 10,
    'certifications': 5,
    'career_goals': 5,
}

def calculate_completion(profile):
    total = sum(PROFILE_FIELDS.values())
    filled = 0
    for field, weight in PROFILE_FIELDS.items():
        value = getattr(profile, field, None)
        if value:
            if isinstance(value, list) and len(value) > 0:
                filled += weight
            elif isinstance(value, str) and value.strip():
                filled += weight
            elif isinstance(value, (int, float)) and value > 0:
                filled += weight
    return int(filled / total * 100)
```

**UI实现**：
```html
<div class="completion-ring">
    <svg viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="none" stroke="#e2e8f0" stroke-width="8"/>
        <circle cx="50" cy="50" r="45" fill="none" stroke="#0066cc" stroke-width="8"
                stroke-dasharray="{{completion * 2.83}} 283"
                transform="rotate(-90 50 50)"/>
    </svg>
    <span class="completion-text">{{completion}}%</span>
</div>
<p>AI对你的了解程度</p>
<button onclick="startAISurvey()">让AI提问完善档案</button>
```

---

### 模块2：双模式切换

**设计**：顶部Toggle开关，切换求职/副业模式

**求职突破模式展示**：
- 目标岗位匹配度
- 技能差距分析
- 面试准备状态
- 简历完善度

**副业探索模式展示**：
- 可用时间精力
- 变现技能盘点
- 副业项目收益目标
- 推荐副业方向

**实现**：
- 用一个模式状态字段存储用户当前选择
- 根据模式切换下方卡片内容
- 模式选择保存到session或user_profile

---

### 模块3：技能标签云（替换"技能"输入框）

**现有能力**：
- AI已能从对话中提取技能（_extract_user_info）
- 技能存储在profile.skills字段

**改造点**：
- 将输入框改为标签云展示
- 区分"AI提取"和"手动添加"
- 支持删除（否认AI提取）和置顶（强调）

**UI实现**：
```html
<div class="skill-tags">
    {% for skill in profile.skills %}
    <span class="tag {% if skill.auto_extracted %}tag-auto{% endif %}">
        {{ skill.name }}
        {% if skill.auto_extracted %}
            <button onclick="denySkill('{{skill.name}}')" title="这不是我的技能">×</button>
        {% endif %}
        <button onclick="emphasizeSkill('{{skill.name}}')" title="强调这项技能">⭐</button>
    </span>
    {% endfor %}
    <button class="tag-add" onclick="addSkill()">+ 添加技能</button>
</div>
```

**数据结构改造**：
```python
# 当前：skills = ['Python', 'Java', 'SQL']
# 改为：skills = [
#     {'name': 'Python', 'source': 'ai_extract', 'emphasized': True},
#     {'name': 'Java', 'source': 'manual', 'emphasized': False},
# ]
```

---

### 模块4：决策锚点卡片（替换"求职意向"表单）

**设计原则**：只展示对AI决策影响最大的字段，卡片式平铺，可直接编辑

**核心锚点**：
1. 目标岗位（最关键）
2. 期望薪资
3. 意向城市
4. 工作方式偏好

**UI实现**：
```html
<div class="anchor-cards">
    <div class="anchor-card" onclick="editInline('target_job_title')">
        <span class="anchor-label">目标岗位</span>
        <span class="anchor-value">{{ profile.target_job_title or '未设定' }}</span>
        <span class="anchor-hint">点击修改</span>
    </div>
    <div class="anchor-card" onclick="editInline('target_salary')">
        <span class="anchor-label">期望薪资</span>
        <span class="anchor-value">{{ profile.target_salary_min }}-{{ profile.target_salary_max }}K</span>
        <span class="anchor-hint">点击修改</span>
    </div>
    <div class="anchor-card" onclick="editInline('location')">
        <span class="anchor-label">意向城市</span>
        <span class="anchor-value">{{ profile.location_preference or '不限' }}</span>
        <span class="anchor-hint">点击修改</span>
    </div>
    <div class="anchor-card" onclick="editInline('work_pref')">
        <span class="anchor-label">工作方式</span>
        <span class="anchor-value">{{ work_preference_map[profile.work_preference] }}</span>
        <span class="anchor-hint">点击修改</span>
    </div>
</div>
```

**交互**：点击卡片 → 弹出小弹窗 → 修改后保存 → 触发AI重新校准

---

### 模块5：目标岗位列表（复用现有target_jobs）

**现有能力**：已支持多目标岗位存储

**改造点**：从JSON列表改为可视化卡片展示

```html
<div class="target-jobs">
    {% for job in profile.target_jobs %}
    <div class="job-card">
        <span class="job-title">{{ job.title }}</span>
        <span class="job-date">添加于 {{ job.added_at[:10] }}</span>
        <button onclick="setActiveJob('{{job.title}}')">设为目标</button>
    </div>
    {% endfor %}
</div>
```

---

### 模块6：决策里程碑（替换"对话历史"）

**设计**：不展示"2026-05-20 聊天记录"，而是总结对话成果

**成果类型**：
- 生成了简历
- 完成了技能差距分析
- 确定了目标岗位
- 获取了面试题

**实现思路**：
- 在对话保存时，根据agent_used和result内容生成成果标签
- 存储在history记录中

```python
# 保存对话时生成成果标签
def generate_achievement(history):
    agent = history.agent_used
    output = history.result_data.get('output', '')
    
    achievements = []
    if agent == 'resume' and 'RESUME_START' in output:
        achievements.append('生成了简历')
    if agent == 'skill':
        achievements.append('完成了技能分析')
    if agent == 'career' and '目标岗位' in output:
        achievements.append('确定了目标岗位')
    if agent == 'interview':
        achievements.append('获取了面试题')
    
    return achievements
```

**UI实现**：
```html
<div class="milestones">
    {% for h in histories %}
    <div class="milestone" onclick="location.href='/chat?id={{h.conversation_id}}'">
        <span class="milestone-date">{{ h.updated_at.strftime('%m-%d') }}</span>
        <span class="milestone-icon">{{ get_icon(h.agent_used) }}</span>
        <span class="milestone-title">{{ h.achievements[0] if h.achievements else h.title }}</span>
    </div>
    {% endfor %}
</div>
```

---

### 模块7：Next Best Action（AI主动建议）

**设计**：根据用户档案状态和近期对话，AI主动推送建议

**实现思路**：
- 分析用户档案缺失字段
- 结合最近对话内容
- 生成1-2个建议卡片

**建议类型**：
```python
def generate_next_actions(profile, recent_histories):
    actions = []
    
    # 未设定目标岗位
    if not profile.target_job_title:
        actions.append({
            'icon': '🎯',
            'title': '设定目标岗位',
            'desc': '明确目标后，AI可以为你提供更精准的建议',
            'action': 'start_career_chat'
        })
    
    # 技能较少
    if len(profile.skills or []) < 3:
        actions.append({
            'icon': '💡',
            'title': '补充技能信息',
            'desc': '告诉AI你会什么，获取技能差距分析',
            'action': 'start_skill_chat'
        })
    
    # 没有简历
    has_resume = any('RESUME' in (h.result_data or {}).get('output', '') 
                     for h in recent_histories)
    if not has_resume and profile.target_job_title:
        actions.append({
            'icon': '📄',
            'title': '生成简历',
            'desc': f'你已设定目标岗位"{profile.target_job_title}"，可以生成针对性简历',
            'action': 'start_resume_chat'
        })
    
    return actions[:2]  # 最多返回2个
```

---

## 五、改造优先级

### P0（必须做）
1. 档案完善度计算 + 环形图
2. 技能标签云（替换输入框）
3. 决策锚点卡片（替换表单）
4. 决策里程碑（替换对话历史列表）

### P1（应该做）
1. 双模式切换
2. 目标岗位卡片化
3. Next Best Action

### P2（可以做）
1. 能力雷达图
2. 自然语言修改档案
3. 渐进式Profiling对话

---

## 六、技术实现要点

### 后端改造
1. **新增API**：`/api/profile/completion` - 计算档案完善度
2. **新增API**：`/api/profile/next-actions` - 获取下一步建议
3. **改造存储**：skills字段改为JSON数组（支持source标记）
4. **改造对话保存**：自动生成achievements标签

### 前端改造
1. **整体布局**：从长列表改为Dashboard网格
2. **技能展示**：从输入框改为标签云组件
3. **锚点卡片**：新增卡片组件，支持点击编辑
4. **里程碑**：从列表改为时间轴样式

### 数据库改造
```sql
-- skills字段改造（可选，或保持现有JSON结构）
-- 新增mode字段
ALTER TABLE user_profiles ADD COLUMN current_mode VARCHAR(20) DEFAULT 'job';
```

---

## 七、与现有功能的衔接

### 对话中自动提取 → 用户中心展示
```
用户："我是Python开发，3年经验，想做数据分析师"
         ↓
orchestrator._extract_user_info() 提取
         ↓
自动更新profile.skills, profile.work_experience, profile.target_job_title
         ↓
用户中心刷新后看到：技能标签多了"Python"，锚点卡片显示"数据分析师"
```

### 用户中心修改 → 影响AI建议
```
用户在锚点卡片修改目标岗位："数据分析师" → "AI产品经理"
         ↓
下次对话时，_build_context()读取新目标
         ↓
AI根据新目标提供建议
```
