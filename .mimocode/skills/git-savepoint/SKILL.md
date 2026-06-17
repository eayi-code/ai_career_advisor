---
name: git-savepoint
description: 创建Git存档点（安全提交）。适用于用户想要保存当前开发进度、创建可回退的检查点时。执行标准流程：状态检查 → 差异预览 → 暂存 → 提交 → 验证。
---

# Git Savepoint — Git存档点技能

## 适用场景

用户说"提交一下"、"存档"、"保存进度"、"git commit"、"创建检查点"时触发。

## 核心流程

按顺序执行以下步骤，每步确认成功后再进入下一步：

### 1. 检查工作区状态
```bash
git status
```
- 确认当前分支
- 确认有哪些变更（新增/修改/删除）
- 如果没有变更，告知用户"工作区干净，无需提交"并停止

### 2. 预览变更内容
```bash
git diff --stat
git diff          # 如果变更不多（<50行），显示完整diff
```
- 向用户简要说明改了什么
- 如果变更量很大，只展示 `--stat` 摘要

### 3. 检查是否有不该提交的文件
```bash
git status --short
```
检查并排除：
- `.env` — 环境变量（含密钥）
- `__pycache__/` — Python缓存
- `.idea/` — IDE配置
- `chroma_data/` — 向量数据库数据
- `*.pyc` — 编译文件
- `node_modules/` — 依赖包

如果发现这些文件在暂存区，先移除：
```bash
git rm -r --cached __pycache__/ 2>/dev/null
git rm --cached .env 2>/dev/null
git rm -r --cached .idea/ 2>/dev/null
git rm -r --cached chroma_data/ 2>/dev/null
```

### 4. 暂存文件
```bash
git add -A
```
或根据用户要求只暂存特定文件：
```bash
git add <file1> <file2>
```

### 5. 创建提交
根据变更内容自动生成提交信息，格式参考：
```bash
git commit -m "$(cat <<'EOF'
<简短描述变更内容>

<可选：详细说明>
EOF
)"
```

提交信息风格（参考本项目历史）：
- 中文撰写
- 简洁描述做了什么（如"添加简历工具模块"、"修复对话保存Bug"）
- 不需要前缀如 feat/fix（用户是初学者，保持简单）

### 6. 验证提交
```bash
git status
git log --oneline -3
```
- 确认"nothing to commit, working tree clean"
- 显示最新提交的hash和信息

## 向用户说明

提交完成后，用通俗语言告诉用户：
- "已经保存了当前进度"
- "如果后面想回退，可以用 `git log` 查看提交历史，用 `git checkout <hash>` 回退到这个版本"
- 如果是首次提交，说明"这是第一个存档点"

## 注意事项

- **不要自动push**：用户明确要求push时才执行 `git push`
- **检查git config**：如果提交失败提示身份信息缺失，帮用户设置：
  ```bash
  git config user.name "eayi-code"
  git config user.email "2575668907@qq.com"
  ```
- **.gitignore维护**：如果发现不该提交的文件反复出现，建议更新 `.gitignore`
- **分支意识**：如果在main/master分支上提交，提醒用户后续可以创建功能分支
