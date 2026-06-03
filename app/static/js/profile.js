// profile.js - 用户中心页面逻辑

// 折叠面板切换
function toggleCollapse(id) {
    document.getElementById(id).classList.toggle('expanded');
}

// 添加项目
function addProject() {
    const container = document.getElementById('projectsContainer');
    const projectHtml = `
        <div class="project-item" style="background: var(--bg-secondary); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">项目名称</label>
                    <input type="text" name="project_name[]" class="form-input" placeholder="项目名称">
                </div>
                <div class="form-group">
                    <label class="form-label">担任角色</label>
                    <input type="text" name="project_role[]" class="form-input" placeholder="例如：前端负责人">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">技术栈</label>
                    <input type="text" name="project_tech[]" class="form-input" placeholder="例如：React, TypeScript, Node.js">
                </div>
                <div class="form-group">
                    <label class="form-label">项目成果</label>
                    <input type="text" name="project_achievement[]" class="form-input" placeholder="例如：用户增长35%">
                </div>
            </div>
            <button type="button" class="btn btn-sm btn-secondary" onclick="this.parentElement.remove()" style="margin-top: 8px;">删除</button>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', projectHtml);
}

// 初始化页面
function initProfilePage() {
    document.getElementById('basicInfo').classList.add('expanded');
    document.getElementById('careerProfile').classList.add('expanded');
    loadUserStats();
    loadProfileCompletion();
    loadNextActions();
}

// 显示编辑用户名弹窗
function showEditUsername() {
    const modal = document.getElementById('usernameModal');
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('active'), 10);
}

// 显示编辑密码弹窗
function showEditPassword() {
    const modal = document.getElementById('passwordModal');
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('active'), 10);
    document.getElementById('oldPassword').value = '';
    document.getElementById('newPassword').value = '';
}

// 关闭弹窗
function closeModal(id) {
    const modal = document.getElementById(id);
    modal.classList.remove('active');
    setTimeout(() => modal.style.display = 'none', 200);
}

// 更新用户名
async function updateUsername() {
    const newUsername = document.getElementById('newUsername').value.trim();
    if (!newUsername) {
        modal.toast('请输入用户名', 'error');
        return;
    }
    
    try {
        const res = await fetch('/api/user/update-username', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: newUsername})
        });
        const data = await res.json();
        
        if (data.code === 200) {
            document.getElementById('usernameDisplay').textContent = newUsername;
            document.querySelector('.profile-meta h1').textContent = newUsername;
            closeModal('usernameModal');
            modal.toast('用户名修改成功', 'success');
        } else {
            modal.toast(data.error || '修改失败', 'error');
        }
    } catch (e) {
        modal.toast('请求失败', 'error');
    }
}

// 更新密码
async function updatePassword() {
    const oldPassword = document.getElementById('oldPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (!oldPassword) {
        modal.toast('请输入当前密码', 'error');
        return;
    }
    
    if (!newPassword) {
        modal.toast('请输入新密码', 'error');
        return;
    }
    
    if (newPassword.length < 6) {
        modal.toast('新密码长度至少6位', 'error');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        modal.toast('两次输入的密码不一致', 'error');
        return;
    }
    
    if (oldPassword === newPassword) {
        modal.toast('新密码不能与旧密码相同', 'error');
        return;
    }
    
    try {
        const res = await fetch('/api/user/update-password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({old_password: oldPassword, new_password: newPassword})
        });
        const data = await res.json();
        
        if (data.code === 200) {
            closeModal('passwordModal');
            modal.toast('密码修改成功', 'success');
        } else {
            modal.toast(data.error || '修改失败', 'error');
        }
    } catch (e) {
        modal.toast('请求失败', 'error');
    }
}

// 加载用户统计
async function loadUserStats() {
    try {
        const res = await fetch('/api/user/stats');
        const data = await res.json();
        
        if (data.code === 200) {
            const stats = data.data;
            
            document.getElementById('statMessages').textContent = stats.total_messages;
            
            const agentUsage = stats.agent_usage;
            const agentNames = {
                'career': '职业规划',
                'skill': '技能分析',
                'side_job': '副业分析'
            };
            const agentColors = {
                'career': '#0ea5e9',
                'skill': '#8b5cf6',
                'side_job': '#10b981'
            };
            
            const maxCount = Math.max(...Object.values(agentUsage), 1);
            const barsContainer = document.querySelector('.agent-bars');
            if (barsContainer) {
                let barsHtml = '';
                for (const [agent, count] of Object.entries(agentUsage)) {
                    const width = (count / maxCount) * 100;
                    const name = agentNames[agent] || agent;
                    const color = agentColors[agent] || '#6b7280';
                    barsHtml += `
                        <div class="agent-bar-item">
                            <span class="agent-bar-label">${name}</span>
                            <div class="agent-bar-track">
                                <div class="agent-bar-fill" style="width: ${width}%; background: ${color};"></div>
                            </div>
                            <span class="agent-bar-value">${count}</span>
                        </div>
                    `;
                }
                barsContainer.innerHTML = barsHtml;
            }
            
            const activityContainer = document.querySelector('.activity-items');
            if (activityContainer && stats.daily_activity.length > 0) {
                let activityHtml = '';
                for (const item of stats.daily_activity) {
                    activityHtml += `
                        <div class="activity-item">
                            <span class="activity-date">${item.date}</span>
                            <span class="activity-count">${item.count} 次对话</span>
                        </div>
                    `;
                }
                activityContainer.innerHTML = activityHtml;
            } else if (activityContainer) {
                activityContainer.innerHTML = '<p style="font-size: 0.8125rem; color: var(--text-tertiary);">暂无活跃数据</p>';
            }
        }
    } catch (e) {
        console.error('加载统计失败:', e);
    }
}

// 导出对话
async function exportConversation(id) {
    try {
        const res = await fetch('/api/export/conversation/' + id);
        const data = await res.json();
        
        if (data.code === 200) {
            const blob = new Blob([data.data.content], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = (data.data.title || '对话记录') + '.txt';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            modal.toast('导出成功', 'success');
        } else {
            modal.toast('导出失败', 'error');
        }
    } catch (e) {
        modal.toast('导出失败', 'error');
    }
}

// 删除历史记录
async function deleteHistoryItem(id) {
    const confirmed = await modal.confirm('确定要删除这条对话记录吗？');
    if (!confirmed) return;
    
    try {
        const res = await fetch('/api/history/' + id, { method: 'DELETE' });
        const data = await res.json();
        
        if (data.code === 200) {
            const el = document.getElementById('history-row-' + id);
            if (el) {
                el.style.opacity = '0';
                el.style.transform = 'translateX(20px)';
                el.style.transition = 'all 0.3s ease';
                setTimeout(() => el.remove(), 300);
            }
            modal.toast('已删除', 'success');
        } else {
            modal.toast('删除失败', 'error');
        }
    } catch (e) {
        modal.toast('删除失败', 'error');
    }
}

// 上传头像
function uploadAvatar(input) {
    const file = input.files[0];
    if (!file) return;
    
    if (file.size > 2 * 1024 * 1024) {
        modal.toast('图片大小不能超过2MB', 'error');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            const res = await fetch('/api/user/update-avatar', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({avatar: e.target.result})
            });
            const data = await res.json();
            
            if (data.code === 200) {
                const avatarDiv = document.querySelector('.profile-avatar');
                avatarDiv.innerHTML = `<img src="${data.avatar_url}" alt="头像" id="avatarImg">`;
                modal.toast('头像更新成功', 'success');
            } else {
                modal.toast(data.error || '上传失败', 'error');
            }
        } catch (err) {
            modal.toast('请求失败', 'error');
        }
    };
    reader.readAsDataURL(file);
}

// 加载档案完善度
async function loadProfileCompletion() {
    try {
        const res = await fetch('/api/profile/completion');
        const data = await res.json();
        
        if (data.code === 200) {
            const completion = data.data.completion;
            const completionText = document.getElementById('completionText');
            const completionCircle = document.getElementById('completionCircle');
            
            if (completionText) {
                completionText.textContent = completion + '%';
            }
            if (completionCircle) {
                const circumference = 2 * Math.PI * 42;
                const dashArray = (completion / 100) * circumference;
                completionCircle.style.strokeDasharray = `${dashArray} ${circumference}`;
            }
        }
    } catch (e) {
        console.error('加载档案完善度失败:', e);
    }
}

// 加载Next Actions
async function loadNextActions() {
    try {
        const res = await fetch('/api/profile/next-actions');
        const data = await res.json();
        
        if (data.code === 200) {
            renderNextActions(data.data);
        }
    } catch (e) {
        console.error('加载建议行动失败:', e);
        renderNextActions([{
            id: 'start_chat',
            title: '开始新对话',
            desc: '与AI顾问聊聊你的职业困惑',
            icon: 'chat',
            color: '#0ea5e9',
            action: 'chat',
            target: '',
            priority: 10
        }]);
    }
}

// 渲染Next Actions
function renderNextActions(actions) {
    const container = document.getElementById('nextActions');
    if (!container) return;
    
    const iconMap = {
        'profile': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
        'target': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
        'skill': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
        'resume': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
        'chart': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
        'interview': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>',
        'money': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>',
        'project': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>',
        'goal': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="M12 18a6 6 0 100-12 6 6 0 000 12z"/><path d="M12 14a2 2 0 100-4 2 2 0 000 4z"/></svg>',
        'chat': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>'
    };
    
    let html = '';
    for (const action of actions) {
        const icon = iconMap[action.icon] || iconMap['chat'];
        const onclick = action.action === 'chat' 
            ? `location.href='/chat?q=${encodeURIComponent(action.target)}'`
            : `scrollToSection('${action.target}')`;
        
        html += `
            <div class="next-action" onclick="${onclick}" style="--action-color: ${action.color}">
                <div class="next-action-icon" style="color: ${action.color}">
                    ${icon}
                </div>
                <div class="next-action-content">
                    <div class="next-action-title">${action.title}</div>
                    <div class="next-action-desc">${action.desc}</div>
                </div>
                <div class="next-action-arrow">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M9 18l6-6-6-6"/></svg>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// 滚动到指定区域
function scrollToSection(sectionId) {
    const section = document.querySelector(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        if (!section.classList.contains('expanded')) {
            section.classList.add('expanded');
        }
    }
}

// 编辑锚点
function editAnchor(field) {
    const fieldLabels = {
        'target_job_title': '目标岗位',
        'salary': '期望薪资(K)',
        'location': '意向城市',
        'work_pref': '工作方式'
    };
    
    const label = fieldLabels[field] || field;
    const value = prompt(`请输入${label}:`);
    
    if (value !== null && value.trim()) {
        updateAnchorField(field, value.trim());
    }
}

// 更新锚点字段
async function updateAnchorField(field, value) {
    try {
        const res = await fetch('/api/profile/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({field: field, value: value})
        });
        
        const data = await res.json();
        if (data.code === 200) {
            modal.toast('更新成功', 'success');
            location.reload();
        } else {
            modal.toast(data.error || '更新失败', 'error');
        }
    } catch (e) {
        modal.toast('请求失败', 'error');
    }
}

// 添加技能
function addSkill() {
    const skill = prompt('请输入技能名称:');
    if (skill && skill.trim()) {
        updateSkill(skill.trim(), 'add');
    }
}

// 删除技能
function denySkill(skill) {
    if (confirm(`确定要移除技能"${skill}"吗？`)) {
        updateSkill(skill, 'remove');
    }
}

// 更新技能
async function updateSkill(skill, action) {
    try {
        const res = await fetch('/api/profile/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({field: 'skills', value: skill, action: action})
        });
        
        const data = await res.json();
        if (data.code === 200) {
            modal.toast('更新成功', 'success');
            location.reload();
        } else {
            modal.toast(data.error || '更新失败', 'error');
        }
    } catch (e) {
        modal.toast('请求失败', 'error');
    }
}
