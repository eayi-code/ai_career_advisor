# 520待办事项 - 用户中心改造

**日期**: 2026-05-20
**状态**: 暂停，待继续

---

## 已完成

### 后端API
- [x] `/api/profile/completion` - 档案完善度计算API
- [x] `/api/profile/milestones` - 决策里程碑API
- [x] `_extract_achievements()` - 从对话记录提取成果标签

### CSS样式
- [x] 档案完善度环形图样式 (`.completion-ring`)
- [x] Dashboard布局样式 (`.dashboard-grid`, `.dashboard-card`)
- [x] 技能标签云样式 (`.skill-tags`, `.skill-tag`)
- [x] 决策锚点卡片样式 (`.anchor-cards`, `.anchor-card`)
- [x] 决策里程碑样式 (`.milestones`, `.milestone`)
- [x] Next Action卡片样式 (`.next-actions`, `.next-action`)

### 前端HTML
- [x] Dashboard四宫格布局（技能标签、决策锚点、里程碑、建议行动）
- [x] 删除旧的对话历史折叠面板

### 前端JavaScript
- [x] `loadProfileCompletion()` - 加载档案完善度
- [x] `editAnchor()` - 编辑锚点字段
- [x] `addSkill()` / `denySkill()` - 添加/删除技能

---

## 待完成（P1优先级）

### 1. Next Action动态生成
- **问题**: 当前Next Action是硬编码的
- **方案**: 调用 `/api/profile/next-actions` 获取动态建议（需新增此API）

### 2. 技能来源标记
- **问题**: 当前skills字段是简单数组，不区分AI提取/手动添加
- **方案**: 可选改造skills为对象数组 `[{name, source, emphasized}]`
- **优先级**: P2，当前可不做

---

## 已完成（520下午继续完成）

### 档案完善度环形图
- 在 `.profile-stats` 区域添加了环形图HTML
- 添加了 `.ring-bg` 和 `.ring-fill` 圆形进度条
- `loadProfileCompletion()` 函数正确更新进度

### 后端API完善
- 新增 `/api/profile/update` 端点
- 支持字段: target_job_title, target_salary_min/max, location_preference, work_preference, skills
- skills支持 add/remove 操作

### 锚点编辑和技能更新
- `updateAnchorField()` 改为调用 `/api/profile/update`
- `updateSkill()` 改为调用 `/api/profile/update`
- 修改成功后刷新页面显示最新数据

---

## 文件清单

### 已修改
- `app/routes/api.py` - 新增completion、milestones、update API
- `app/static/css/style.css` - 新增AI-Native用户中心样式
- `app/templates/career/profile.html` - 重构为Dashboard布局，添加环形图

---

## 下次继续时的步骤

1. 在 `api.py` 添加 `/api/profile/update` 端点
2. 在 `profile.html` 的 `.profile-info` 区域添加档案完善度环形图
3. 测试锚点编辑和技能添加功能
4. 提交Git存档

---

**备注**: 这是AI-Native用户中心改造的P0功能，完成后可测试基本体验。P1功能（双模式切换、能力雷达图）后续再做。
