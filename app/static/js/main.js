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

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
    
    lastScroll = currentScroll;
});

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
