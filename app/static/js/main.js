/**
 * AI职业决策顾问 - 前端交互
 */

// ===== 滚动动画 =====
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            if (entry.target.dataset.delay) {
                entry.target.style.animationDelay = entry.target.dataset.delay;
            }
        }
    });
}, observerOptions);

// 初始化滚动观察
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
});

// ===== 导航栏滚动效果 =====
let lastScroll = 0;
const navbar = document.querySelector('.navbar');

if (navbar) {
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        lastScroll = currentScroll;
    });
}

// ===== 平滑滚动 =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// ===== 打字效果 =====
class TypeWriter {
    constructor(element, words, wait = 3000) {
        this.element = element;
        this.words = words;
        this.wait = wait;
        this.wordIndex = 0;
        this.txt = '';
        this.isDeleting = false;
        this.type();
    }

    type() {
        const current = this.wordIndex % this.words.length;
        const fullTxt = this.words[current];

        if (this.isDeleting) {
            this.txt = fullTxt.substring(0, this.txt.length - 1);
        } else {
            this.txt = fullTxt.substring(0, this.txt.length + 1);
        }

        this.element.textContent = this.txt;

        let typeSpeed = this.isDeleting ? 50 : 100;

        if (!this.isDeleting && this.txt === fullTxt) {
            typeSpeed = this.wait;
            this.isDeleting = true;
        } else if (this.isDeleting && this.txt === '') {
            this.isDeleting = false;
            this.wordIndex++;
            typeSpeed = 500;
        }

        setTimeout(() => this.type(), typeSpeed);
    }
}

// 初始化打字效果
document.addEventListener('DOMContentLoaded', () => {
    const typeElement = document.querySelector('.typewrite');
    if (typeElement) {
        const words = JSON.parse(typeElement.getAttribute('data-words'));
        new TypeWriter(typeElement, words);
    }
});

// ===== 聊天功能 =====
class ChatManager {
    constructor() {
        this.messages = [];
        this.isLoading = false;
        this.chatContainer = document.getElementById('chatMessages');
        this.input = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        
        if (this.chatContainer) {
            this.init();
        }
    }

    init() {
        this.sendBtn?.addEventListener('click', () => this.sendMessage());
        this.input?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    async sendMessage() {
        const message = this.input?.value.trim();
        if (!message || this.isLoading) return;

        this.addMessage(message, 'user');
        this.input.value = '';
        this.setLoading(true);

        try {
            const agentType = document.getElementById('agentType')?.value || 'auto';
            const response = await fetch('/api/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, agent_type: agentType })
            });

            const data = await response.json();

            if (data.code === 200) {
                this.addMessage(data.data.response, 'agent');
                this.updateReasoningPanel(data.data.reasoning_steps);
                this.updateToolsPanel(data.data.tools_used);
            } else {
                this.addMessage('抱歉，处理出错：' + (data.error || '未知错误'), 'error');
            }
        } catch (error) {
            this.addMessage('网络错误，请稍后重试', 'error');
        } finally {
            this.setLoading(false);
        }
    }

    addMessage(content, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = type === 'user' ? 'U' : 'AI';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = this.formatContent(content);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);

        this.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatContent(content) {
        // 简单的markdown格式化
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }

    setLoading(loading) {
        this.isLoading = loading;
        if (this.sendBtn) {
            this.sendBtn.disabled = loading;
        }
        if (loading) {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message message-agent';
            loadingDiv.id = 'loadingMessage';
            loadingDiv.innerHTML = `
                <div class="message-avatar">AI</div>
                <div class="message-content">
                    <div class="loading-dots">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            `;
            this.chatContainer.appendChild(loadingDiv);
            this.scrollToBottom();
        } else {
            document.getElementById('loadingMessage')?.remove();
        }
    }

    updateReasoningPanel(steps) {
        const panel = document.getElementById('reasoningPanel');
        if (!panel) return;

        if (!steps || steps.length === 0) {
            panel.innerHTML = '<p class="text-muted">发送消息后，这里将展示AI的推理过程...</p>';
            return;
        }

        let html = '';
        steps.forEach((step, i) => {
            html += `
                <div class="step-item animate-in" style="animation-delay: ${i * 0.1}s">
                    <div class="step-action">${step.action}</div>
                    <div class="step-output">${this.truncate(step.output, 100)}</div>
                </div>
            `;
        });
        panel.innerHTML = html;
    }

    updateToolsPanel(tools) {
        const panel = document.getElementById('toolsPanel');
        if (!panel) return;

        if (!tools || tools.length === 0) {
            panel.innerHTML = '<p class="text-muted">未使用工具</p>';
            return;
        }

        let html = '';
        tools.forEach(tool => {
            html += `<span class="tool-badge">${tool}</span>`;
        });
        panel.innerHTML = html;
    }

    scrollToBottom() {
        if (this.chatContainer) {
            this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        }
    }

    truncate(str, len) {
        if (!str) return '';
        return str.length > len ? str.substring(0, len) + '...' : str;
    }
}

// ===== 表单验证 =====
class FormValidator {
    constructor(form) {
        this.form = form;
        this.errors = [];
    }

    validate() {
        this.errors = [];
        const inputs = this.form.querySelectorAll('[required]');
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                this.errors.push(`${input.previousElementSibling?.textContent || '此字段'}不能为空`);
                input.classList.add('error');
            } else {
                input.classList.remove('error');
            }
        });

        // 邮箱验证
        const emailInput = this.form.querySelector('[type="email"]');
        if (emailInput && emailInput.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(emailInput.value)) {
                this.errors.push('请输入有效的邮箱地址');
            }
        }

        // 密码验证
        const passwordInput = this.form.querySelector('[name="password"]');
        if (passwordInput && passwordInput.value.length < 6) {
            this.errors.push('密码长度至少6位');
        }

        return this.errors.length === 0;
    }

    showErrors() {
        // 移除现有错误提示
        this.form.querySelectorAll('.alert-error').forEach(el => el.remove());

        if (this.errors.length > 0) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-error';
            errorDiv.innerHTML = this.errors.join('<br>');
            this.form.insertBefore(errorDiv, this.form.firstChild);
        }
    }
}

// ===== 数字动画 =====
function animateNumbers() {
    const numbers = document.querySelectorAll('[data-number]');
    
    numbers.forEach(el => {
        const target = parseInt(el.getAttribute('data-number'));
        const duration = 2000;
        const start = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            
            // 缓动函数
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = Math.floor(target * easeOut);
            
            el.textContent = current.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }

        requestAnimationFrame(update);
    });
}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
    // 初始化聊天（仅在非聊天页面）
    if (!document.getElementById('chatMessages')?.closest('.chat-layout')) {
        new ChatManager();
    }
    
    // 初始化数字动画
    const statsSection = document.querySelector('.stats');
    if (statsSection) {
        const statsObserver = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                animateNumbers();
                statsObserver.disconnect();
            }
        });
        statsObserver.observe(statsSection);
    }

    // 初始化表单验证
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const validator = new FormValidator(form);
            if (!validator.validate()) {
                e.preventDefault();
                validator.showErrors();
            }
        });
    });

    // 添加入场动画
    document.querySelectorAll('.feature-item').forEach((item, i) => {
        item.style.animationDelay = `${i * 0.1}s`;
    });
});

// ===== 工具函数 =====
const utils = {
    // 防抖
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 节流
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // 格式化日期
    formatDate(date) {
        return new Intl.DateTimeFormat('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    }
};

// ===== 移动端导航栏菜单切换 =====
function toggleNavMenu() {
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        navLinks.classList.toggle('active');
    }
}

// 点击导航链接后自动关闭菜单（移动端）
document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                const navMenu = document.querySelector('.nav-links');
                if (navMenu) {
                    navMenu.classList.remove('active');
                }
            }
        });
    });

    // 点击页面其他区域关闭导航菜单
    document.addEventListener('click', function(e) {
        const navbar = document.querySelector('.navbar');
        const navLinks = document.querySelector('.nav-links');
        if (navbar && navLinks && !navbar.contains(e.target)) {
            navLinks.classList.remove('active');
        }
    });
});

// ===== 全局后台任务状态管理器 =====
window.GlobalTaskManager = {
    STORAGE_KEY: 'ai_career_task',
    pollInterval: null,
    _checkInProgress: false,
    
    getTaskFromStorage() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            if (data) return JSON.parse(data);
        } catch (e) {
            console.error('[GlobalTask] 读取任务失败:', e);
        }
        return null;
    },
    
    saveTaskToStorage(taskId, conversationId) {
        try {
            const taskData = {
                taskId: taskId,
                conversationId: conversationId,
                timestamp: Date.now()
            };
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(taskData));
            console.log('[GlobalTask] 任务已保存:', taskId);
        } catch (e) {
            console.error('[GlobalTask] 保存任务失败:', e);
        }
    },
    
    clearTaskFromStorage() {
        try {
            localStorage.removeItem(this.STORAGE_KEY);
            console.log('[GlobalTask] 任务已清除');
        } catch (e) {
            console.error('[GlobalTask] 清除任务失败:', e);
        }
    },
    
    async checkTaskStatus() {
        // 防止并发调用
        if (this._checkInProgress) return;
        this._checkInProgress = true;
        
        try {
            await this._doCheckTaskStatus();
        } finally {
            this._checkInProgress = false;
        }
    },
    
    async _doCheckTaskStatus() {
        const savedTask = this.getTaskFromStorage();
        if (!savedTask) {
            this.stopPolling();
            return;
        }
        
        const { taskId, conversationId } = savedTask;
        
        // 判断当前是否在活动任务的对话页
        const isChatPage = window.location.pathname.includes('/chat');
        const urlParams = new URLSearchParams(window.location.search);
        const urlConversationId = urlParams.get('id');
        const isActiveChatPage = isChatPage && (
            urlConversationId === conversationId || 
            window.currentConversationId === conversationId
        );
        
        // 如果离开了活动对话页，标记 left
        if (!isActiveChatPage) {
            sessionStorage.setItem('ai_career_task_left_' + taskId, 'true');
        }
        
        const hasLeft = sessionStorage.getItem('ai_career_task_left_' + taskId) === 'true';
        
        // 获取客户端当前的流式处理状态
        const isClientProcessing = window.isProcessing === true;
        
        // 如果客户端正在通过 SSE 流式处理此任务，完全交给 SSE 自己的完成回调控制
        // 轮询器保持静默观察，不做任何干预
        if (isClientProcessing) {
            this.startPolling();
            return;
        }
        
        try {
            const response = await fetch('/api/agent/task/detail/' + taskId);
            if (response.status === 404) {
                this.clearTaskFromStorage();
                return;
            }
            
            const resData = await response.json();
            if (resData.code !== 200 || !resData.data) return;
            
            const task = resData.data;
            const status = task.status;
            
            if (status === 'completed') {
                this.stopPolling();
                
                if (!isActiveChatPage) {
                    // 用户不在活动对话页（如 /profile 或其他对话）
                    this.clearTaskFromStorage();
                    if (hasLeft) {
                        if (window.modal) {
                            window.modal.show({
                                title: '后台任务已完成',
                                content: '您发起的后台分析任务已执行完成，是否立即查看结果？',
                                type: 'confirm',
                                onConfirm: () => {
                                    window.location.href = '/chat?id=' + conversationId;
                                }
                            });
                        } else {
                            if (confirm('后台任务已完成，是否点击查看？')) {
                                window.location.href = '/chat?id=' + conversationId;
                            }
                        }
                    }
                } else {
                    // 用户在活动对话页
                    if (typeof window.loadConversation === 'function') {
                        this.clearTaskFromStorage();
                        if (typeof window.setProcessingState === 'function') {
                            window.setProcessingState(false);
                        }
                        console.log('[GlobalTask] 任务已完成，加载最新对话:', conversationId);
                        window.loadConversation(conversationId);
                    } else {
                        // chat.js 尚未就绪，保留存储数据，等待下次轮询重试
                        console.log('[GlobalTask] loadConversation 尚不可用，等待重试');
                        this.startPolling();
                    }
                }
            } else if (status === 'failed' || status === 'aborted') {
                this.stopPolling();
                this.clearTaskFromStorage();
                
                if (!isActiveChatPage) {
                    if (hasLeft && window.modal) {
                        window.modal.toast('后台任务已中止或执行失败', 'error');
                    }
                } else {
                    if (typeof window.setProcessingState === 'function') {
                        window.setProcessingState(false);
                    }
                    if (window.modal) {
                        window.modal.toast('任务执行失败: ' + (task.error || '未知错误'), 'error');
                    }
                }
            } else {
                // 进行中 (pending / running)
                this.startPolling();
                
                if (isActiveChatPage) {
                    if (typeof window.restoreRunningTask === 'function') {
                        console.log('[GlobalTask] 任务仍在运行，恢复SSE流:', taskId);
                        window.restoreRunningTask(taskId, conversationId);
                    } else {
                        console.log('[GlobalTask] restoreRunningTask 尚不可用，等待重试');
                    }
                }
            }
        } catch (error) {
            console.error('[GlobalTask] 检查任务状态出错:', error);
        }
    },
    
    startPolling() {
        if (this.pollInterval) return;
        this.pollInterval = setInterval(() => this.checkTaskStatus(), 5000);
    },
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    },
    
    init() {
        // 核心策略：在 chat 页面，不立即调用 checkTaskStatus()
        // 原因：main.js 在 DOMContentLoaded 时先于 chat.js 的 initChatPage 执行,
        //       如果此时立即检查，会与 initChatPage 中的 loadConversation 产生竞态,
        //       导致加载气泡被清空、任务存储被提前清除等严重问题。
        // 在 chat 页面，由 chat.js 的 initTaskPersistence() 在页面完全初始化后触发检查。
        // 在非 chat 页面（如 /profile），立即检查以便弹出"任务已完成"提示。
        const isChatPage = window.location.pathname.includes('/chat');
        if (!isChatPage) {
            this.checkTaskStatus();
        }
        
        // visibilitychange: 页面可见性变化（切换APP、锁屏等）
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                console.log('[GlobalTask] 页面变为可见，检查任务状态');
                this.checkTaskStatus();
            }
        });
        
        // pageshow: 从bfcache恢复时触发（手机端重要）
        window.addEventListener('pageshow', (event) => {
            if (event.persisted) {
                console.log('[GlobalTask] 页面从bfcache恢复，检查任务状态');
                this.checkTaskStatus();
            }
        });
        
        // storage: 其他标签页修改localStorage时触发
        window.addEventListener('storage', (e) => {
            if (e.key === this.STORAGE_KEY) {
                this.checkTaskStatus();
            }
        });
        
        // 在线/离线状态变化
        window.addEventListener('online', () => {
            console.log('[GlobalTask] 网络恢复，检查任务状态');
            this.checkTaskStatus();
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    window.GlobalTaskManager.init();
});

// ===== Mobile Sidebar Toggle (shared across all pages) =====
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const hamburger = document.getElementById('hamburgerBtn');

    if (!sidebar || !overlay) return;

    const isActive = sidebar.classList.contains('active');

    if (isActive) {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        if (hamburger) hamburger.classList.remove('active');
        document.body.style.overflow = '';
    } else {
        sidebar.classList.add('active');
        overlay.classList.add('active');
        if (hamburger) hamburger.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

// Close sidebar when clicking links (mobile)
document.addEventListener('DOMContentLoaded', function() {
    const sidebarLinks = document.querySelectorAll('.sidebar-link, .chat-history-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                setTimeout(() => toggleSidebar(), 100);
            }
        });
    });
});
