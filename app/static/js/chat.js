// chat.js - 聊天页面主要逻辑

// 全局变量
let currentConversationId = '';
let autoMessage = '';
let currentAbortController = null;
let isProcessing = false;
let uploadedFileContent = null;
let uploadedFileName = null;
let uploadedFilePreview = null; // 新增：图片预览base64
let currentResumeContent = null;
let currentZoomLevel = 1;
let lastUsedAgent = null;
let currentStreamedText = '';
let activeLoadingBubble = null;
let currentTaskId = null;
let isNewConversation = false;

// 任务持久化相关
const TASK_STORAGE_KEY = 'ai_career_task';
const TASK_RESTORE_INTERVAL = 2000; // 任务恢复轮询间隔（毫秒）
let taskRestoreTimer = null;

// 浮动任务状态栏相关
let taskStatusBarVisible = false;

// XSS防护：转义HTML特殊字符
function escapeHtml(text) {
    if (!text) return '';
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, c => map[c]);
}

// DOM元素引用（需要在DOMContentLoaded后初始化）
let chatMessages, chatInput, sendBtn, fileInput, filePreview;

// 配置 marked.js 自定义代码块渲染（支持 ChatGPT/Gemini 风格的代码复制与标题栏）
if (window.marked) {
    marked.use({
        renderer: {
            code(codeText, infostring) {
                const lang = infostring || 'code';
                const escaped = codeText
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;');
                
                return `<div class="code-block-wrapper">` +
                            `<div class="code-block-header">` +
                                `<span class="code-block-lang">${lang}</span>` +
                                `<button class="code-block-copy-btn" onclick="copyCodeBlock(this)">` +
                                    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>` +
                                    `<span>复制代码</span>` +
                                `</button>` +
                            `</div>` +
                            `<pre><code class="language-${lang}">${escaped}</code></pre>` +
                       `</div>`;
            }
        }
    });
}

// 复制代码块辅助函数
function copyCodeBlock(button) {
    const wrapper = button.closest('.code-block-wrapper');
    if (!wrapper) return;
    const codeEl = wrapper.querySelector('pre code');
    if (!codeEl) return;
    
    const textToCopy = codeEl.textContent;
    
    navigator.clipboard.writeText(textToCopy).then(() => {
        const textSpan = button.querySelector('span');
        const originalText = textSpan.textContent;
        textSpan.textContent = '已复制！';
        button.classList.add('copied');
        
        setTimeout(() => {
            textSpan.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('无法复制代码: ', err);
    });
}

// 初始化函数
async function initChatPage(conversationId, autoMsg) {
    currentConversationId = conversationId;
    isNewConversation = !currentConversationId;
    autoMessage = autoMsg;
    
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendBtn = document.getElementById('sendBtn');
    fileInput = document.getElementById('fileInput');
    filePreview = document.getElementById('filePreview');
    
    if (currentConversationId) {
        await loadConversation(currentConversationId);
    }
    
    if (autoMessage) {
        // Clear query parameters from URL to prevent re-triggering on back navigation or refresh
        try {
            const url = new URL(window.location.href);
            url.searchParams.delete('q');
            window.history.replaceState(null, '', url.pathname + url.search);
        } catch (e) {
            console.error('Failed to update history state:', e);
        }
        
        setTimeout(() => {
            chatInput.value = autoMessage;
            sendMessage();
        }, 500);
    }
    
    fileInput.addEventListener('change', handleFileUpload);
    sendBtn.onclick = sendMessage;
    
    // 输入框自动撑高与 Enter 发送 / Shift+Enter 换行逻辑
    chatInput.addEventListener('input', function() {
        this.style.height = '32px';
        const newHeight = Math.min(this.scrollHeight, 160);
        this.style.height = newHeight + 'px';
    });
    
    chatInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!isProcessing) {
                sendMessage();
            }
        }
    });
    
    // 初始化欢迎卡片 3D 悬浮磁吸动效
    initWelcomeCardsTilt();
    
    // 初始化文件拖拽高亮上传动效
    initDragAndDropUpload();
    
    // 点击外部关闭Agent下拉菜单
    document.addEventListener('click', function(e) {
        const selector = document.getElementById('agentSelector');
        if (selector && !selector.contains(e.target)) {
            const dropdown = document.getElementById('agentDropdown');
            const btn = document.getElementById('agentSelectorBtn');
            if (dropdown) dropdown.classList.remove('show');
            if (btn) btn.classList.remove('active');
        }
    });
    
    // 初始化任务持久化和恢复机制
    initTaskPersistence();
}

// 欢迎卡片 3D 视差倾斜效果
function initWelcomeCardsTilt() {
    const cards = document.querySelectorAll('.welcome-card');
    cards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            // 倾斜角度：限制在 8 度以内，展现出精致的微动效
            const rotateX = ((centerY - y) / centerY) * 8;
            const rotateY = ((x - centerX) / centerX) * 8;
            
            card.classList.add('is-tilting');
            card.style.transform = `perspective(600px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale(1.02)`;
        });
        
        card.addEventListener('mouseleave', () => {
            card.classList.remove('is-tilting');
            card.style.transform = 'perspective(600px) rotateX(0deg) rotateY(0deg) scale(1)';
        });
    });
}

// 文件拖拽磁吸 snap 上传效果
function initDragAndDropUpload() {
    const wrapper = document.querySelector('.chat-input-wrapper');
    if (!wrapper) return;
    
    // 阻止浏览器默认拖拽打开文件行为
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        window.addEventListener(eventName, e => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });
    
    // 当文件拖入页面时，令输入框进行初级膨胀高亮
    ['dragenter', 'dragover'].forEach(eventName => {
        window.addEventListener(eventName, () => {
            if (!isProcessing) {
                wrapper.classList.add('drag-over');
            }
        }, false);
    });
    
    // 文件拖离页面时还原
    window.addEventListener('dragleave', e => {
        if (e.clientX <= 0 || e.clientY <= 0 || e.clientX >= window.innerWidth || e.clientY >= window.innerHeight) {
            wrapper.classList.remove('drag-over', 'drag-snap');
        }
    }, false);
    
    window.addEventListener('drop', () => {
        wrapper.classList.remove('drag-over', 'drag-snap');
    }, false);
    
    // 当文件移动进输入框胶囊局部时，触发“磁吸对接”高亮
    wrapper.addEventListener('dragover', () => {
        if (!isProcessing) {
            wrapper.classList.add('drag-snap');
        }
    }, false);
    
    wrapper.addEventListener('dragleave', () => {
        wrapper.classList.remove('drag-snap');
    }, false);
    
    // 拖拽松开，认领文件上传
    wrapper.addEventListener('drop', e => {
        wrapper.classList.remove('drag-over', 'drag-snap');
        if (isProcessing) return;
        
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            handleDroppedFiles(files);
        }
    }, false);
}

function handleDroppedFiles(files) {
    if (isProcessing) return;
    const file = files[0];
    if (!file) return;
    
    const allowedExts = ['.pdf', '.docx', '.doc', '.txt', '.png', '.jpg', '.jpeg', '.webp', '.bmp'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExts.includes(ext)) {
        modal.toast('不支持的文件格式，请上传PDF、DOCX、TXT或图片文件', 'error');
        return;
    }
    
    // 赋予 fileInput 并触发原生上传逻辑
    fileInput.files = files;
    handleFileUpload({ target: fileInput });
}

// 文件上传处理
async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const allowedExts = ['.pdf', '.docx', '.doc', '.txt', '.png', '.jpg', '.jpeg', '.webp', '.bmp'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExts.includes(ext)) {
        modal.toast('不支持的文件格式，请上传PDF、DOCX、TXT或图片文件', 'error');
        fileInput.value = '';
        return;
    }
    
    const isImage = ['.png', '.jpg', '.jpeg', '.webp', '.bmp'].includes(ext);
    
    // 如果是图片，先生成预览
    if (isImage) {
        const reader = new FileReader();
        reader.onload = function(e) {
            uploadedFilePreview = e.target.result; // 保存base64用于预览
            // 更新预览区域显示图片
            updateFilePreviewUI(file.name, true);
        };
        reader.readAsDataURL(file);
    } else {
        uploadedFilePreview = null;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        modal.toast(isImage ? '正在使用AI智能识别截图岗位信息...' : '正在解析文件...', 'info');
        const res = await fetch('/api/upload/resume', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        
        if (data.code === 200) {
            uploadedFileContent = data.data.content;
            uploadedFileName = data.data.filename;
            updateFilePreviewUI(uploadedFileName, isImage);
            chatInput.placeholder = '输入优化要求，或直接发送以解析简历...';
            modal.toast('文件解析成功', 'success');
        } else {
            modal.toast(data.error || '文件解析失败', 'error');
            fileInput.value = '';
            uploadedFilePreview = null;
        }
    } catch (err) {
        modal.toast('文件上传失败', 'error');
        fileInput.value = '';
        uploadedFilePreview = null;
    }
}

// 更新文件预览UI
function updateFilePreviewUI(fileName, isImage) {
    const previewEl = document.getElementById('filePreview');
    if (!previewEl) return;
    
    if (isImage && uploadedFilePreview) {
        previewEl.innerHTML = `
            <div class="file-preview-image">
                <img src="${uploadedFilePreview}" alt="预览" />
                <div class="file-preview-info">
                    <span class="file-name">${escapeHtml(fileName)}</span>
                    <span class="file-status">解析完成</span>
                </div>
                <button class="file-remove-btn" onclick="removeFile()" title="移除">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
            </div>
        `;
    } else {
        previewEl.innerHTML = `
            <div class="file-preview-doc">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/>
                </svg>
                <span class="file-name">${escapeHtml(fileName)}</span>
                <button class="file-remove-btn" onclick="removeFile()" title="移除">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
            </div>
        `;
    }
    previewEl.style.display = 'block';
}

function removeFile() {
    uploadedFileContent = null;
    uploadedFileName = null;
    uploadedFilePreview = null;
    fileInput.value = '';
    filePreview.style.display = 'none';
    chatInput.placeholder = '输入你的问题...';
}

// 加载对话历史
async function loadConversation(id) {
    isNewConversation = false;
    try {
        const res = await fetch('/api/history/' + id);
        const data = await res.json();
        if (data.code === 200 && data.data.messages && data.data.messages.length > 0) {
            document.getElementById('welcomeMessage')?.remove();
            data.data.messages.forEach((msg, idx) => {
                const steps = msg.steps || msg.execution_steps || [];
                addMessage(msg.content, msg.role === 'user', msg.agent, steps, idx);
            });
            chatMessages.scrollTop = chatMessages.scrollHeight;
            if (data.data.title) {
                document.getElementById('chatTitle').textContent = data.data.title;
            }
            
            // 填充全局推理详情侧边栏为最后一条助手回复的详情
            const lastAssistantMsg = data.data.messages.filter(msg => msg.role === 'assistant').pop();
            if (lastAssistantMsg) {
                const execSteps = lastAssistantMsg.execution_steps || [];
                const reasonSteps = lastAssistantMsg.steps || [];
                const toolsUsedFromMsg = lastAssistantMsg.tools_used || [];
                
                // 从execution_steps中提取工具调用信息
                const toolsFromExecSteps = execSteps
                    .filter(s => s.type === 'tool' || s.action)
                    .map(s => s.action || s.title?.replace('调用工具: ', '') || '')
                    .filter(Boolean);
                
                const toolsUsed = [...new Set([...toolsUsedFromMsg, ...toolsFromExecSteps, ...reasonSteps.filter(s => s.action).map(s => s.action)])];
                
                updateExecutionSteps(execSteps);
            } else {
                // 清空为默认占位符
                document.getElementById('executionStepsPanel').innerHTML = '<p style="font-size: 0.8125rem; color: var(--text-tertiary);">发送消息后展示</p>';
            }
        }
    } catch (e) { console.error(e); }
}

// 处理状态控制
function setProcessingState(processing) {
    isProcessing = processing;
    const wrapper = document.querySelector('.chat-input-wrapper');
    const uploadBtn = document.getElementById('uploadBtn');
    const glowEl = document.getElementById('inputGlow');
    
    if (processing) {
        sendBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
        sendBtn.classList.add('stop-btn');
        sendBtn.onclick = stopProcessing;
        chatInput.disabled = true;
        if (uploadBtn) uploadBtn.disabled = true;
        if (wrapper) wrapper.classList.add('disabled');
        
        // 如果是新对话的第一次提问，激活扩散光的效果
        if (isNewConversation && glowEl) {
            glowEl.classList.add('glow-active');
        }
    } else {
        sendBtn.innerHTML = '发送';
        sendBtn.classList.remove('stop-btn');
        sendBtn.onclick = sendMessage;
        chatInput.disabled = false;
        if (uploadBtn) uploadBtn.disabled = false;
        if (wrapper) wrapper.classList.remove('disabled');
        
        // 移除扩散光效果
        if (glowEl) {
            glowEl.classList.remove('glow-active');
        }
        
        // 第一次提问已经完成，之后便不再是“新对话”状态
        if (isNewConversation) {
            isNewConversation = false;
        }
        
        // 移除正在生成的流式光标
        if (activeLoadingBubble) {
            const contentEl = activeLoadingBubble.querySelector('.message-content');
            if (contentEl) {
                contentEl.classList.remove('streaming-active');
            }
        }
        
        currentAbortController = null;
        activeLoadingBubble = null;
        currentTaskId = null;
    }
}

function stopProcessing() {
    if (currentTaskId) {
        fetch('/api/agent/task/abort/' + currentTaskId, { method: 'POST' })
            .catch(err => console.error('Failed to abort task on server:', err));
        currentTaskId = null;
    }
    // 清除localStorage中的任务状态
    clearTaskFromStorage();
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }
    
    const loadingEl = activeLoadingBubble || document.getElementById('loading');
    if (loadingEl) {
        // 移除加载点和进度指示器
        const indicator = loadingEl.querySelector('.progress-indicator');
        if (indicator) indicator.remove();
        
        const loadingDots = loadingEl.querySelector('.loading-dots');
        if (loadingDots) loadingDots.remove();
        
        // 更新进度文字为已停止
        const progressText = loadingEl.querySelector('#progressText');
        if (progressText) progressText.textContent = '已停止生成';
        
        // 移除ID防篡改，并使消息内容显示正常
        loadingEl.removeAttribute('id');
    }
    
    setProcessingState(false);
}

// 添加消息
function addMessage(content, isUser, agent, steps, index = 0, imagePreview = null) {
    const div = document.createElement('div');
    div.className = 'message ' + (isUser ? 'message-user' : 'message-agent');
    div.style.setProperty('--msg-index', index);
    const copyBtn = isUser ? '' : 
        '<button class="msg-copy-btn" onclick="copyMessage(this)" title="复制">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>' +
        '</button>';
    
    const isResume = !isUser && detectResumeContent(content, agent);
    
    let displayContent = content;
    let previewCard = '';
    let showCopyBtn = copyBtn;
    let imagePreviewHtml = '';
    
    // 如果有图片预览，生成HTML
    if (imagePreview) {
        imagePreviewHtml = `
            <div class="message-image-preview">
                <img src="${imagePreview}" alt="上传的图片" onclick="showImageModal('${imagePreview}')" />
            </div>
        `;
    }
    
    if (isResume) {
        const resumeOnly = extractResumeContent(content);
        if (resumeOnly) {
            displayContent = content.split('<!--RESUME_START-->')[0].trim() || '已为您生成简历';
            const contentId = 'resume-content-' + Date.now();
            window[contentId] = resumeOnly;
            previewCard = buildResumePreviewCard(contentId);
            showCopyBtn = '';
            
            // 清理旧的简历内容（保留最近5个）
            const resumeKeys = Object.keys(window).filter(k => k.startsWith('resume-content-'));
            if (resumeKeys.length > 5) {
                resumeKeys.slice(0, resumeKeys.length - 5).forEach(k => delete window[k]);
            }
        }
    }
    
    let reasoningContainer = '';
    if (!isUser && steps && steps.length > 0) {
        reasoningContainer = buildReasoningTimeline(steps);
    }
    
    div.innerHTML = '<div class="message-avatar">' + (isUser ? '我' : 'AI') + '</div>' +
        '<div class="message-bubble">' +
            reasoningContainer +
            imagePreviewHtml +
            '<div class="message-content">' + formatMessageContent(displayContent) + '</div>' +
            previewCard +
            showCopyBtn +
        '</div>';
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    if (isResume && previewCard) {
        const contentId = Object.keys(window).filter(k => k.startsWith('resume-content-')).pop();
        if (contentId) setTimeout(() => showResumeInPanel(contentId), 500);
    }
}

// 格式化消息内容
function formatMessageContent(content) {
    if (!content) return '';
    try {
        // Use marked for robust standard markdown parsing (tables, lists, blockquotes, code blocks)
        return marked.parse(content);
    } catch (e) {
        console.error('Failed to parse Markdown with marked, falling back to simple format:', e);
        // Basic fallback
        let html = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        return html;
    }
}

// 简历内容检测和提取
function extractResumeContent(content) {
    const startTag = '<!--RESUME_START-->';
    const endTag = '<!--RESUME_END-->';
    
    const startIdx = content.indexOf(startTag);
    const endIdx = content.indexOf(endTag);
    
    if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
        return content.substring(startIdx + startTag.length, endIdx).trim();
    }
    
    if (content.includes('<!DOCTYPE html>') || content.includes('<html')) {
        const htmlStart = content.indexOf('<!DOCTYPE html>') !== -1 ? content.indexOf('<!DOCTYPE html>') : content.indexOf('<html');
        const htmlEnd = content.lastIndexOf('</html>');
        if (htmlStart !== -1 && htmlEnd !== -1) {
            return content.substring(htmlStart, htmlEnd + 7).trim();
        }
    }
    
    const resumeKeywords = ['## 个人简介', '## 工作经验', '## 教育背景', '## 技能', '## 项目经历'];
    const hasKeywords = resumeKeywords.some(kw => content.includes(kw));
    
    if (hasKeywords && content.length > 300) {
        const firstH2 = content.indexOf('## ');
        if (firstH2 !== -1) {
            return content.substring(firstH2).trim();
        }
    }
    
    return null;
}

function detectResumeContent(content, agent) {
    if (content.includes('<!--RESUME_START-->')) return true;
    if (agent === '简历优化专家' && content.length > 200) return true;
    if (content.includes('<!DOCTYPE html>') && content.includes('tailwindcss')) return true;
    if (content.includes('<html') && content.includes('bg-primary')) return true;
    
    const resumeKeywords = ['## 个人简介', '## 工作经验', '## 教育背景', '## 技能', '## 项目经历'];
    const hasKeywords = resumeKeywords.some(kw => content.includes(kw));
    
    return hasKeywords && content.length > 300;
}

// 简历预览卡片
function buildResumePreviewCard(contentId) {
    return '<div class="resume-preview-card">' +
        '<div class="resume-preview-header">' +
            '<span class="resume-preview-title">📄 简历已生成</span>' +
            '<div class="resume-preview-actions">' +
                '<button class="btn btn-secondary" onclick="showResumeInPanel(\'' + contentId + '\')">' +
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>' +
                    '预览' +
                '</button>' +
                '<button class="btn btn-primary" onclick="downloadResume(\'' + contentId + '\', \'html\')">' +
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>' +
                    '下载' +
                '</button>' +
            '</div>' +
        '</div>' +
    '</div>';
}

function renderResumeContent(content) {
    if (content.includes('<!DOCTYPE html>') || content.includes('<html') || content.includes('tailwindcss')) {
        return content;
    }
    try {
        return marked.parse(content);
    } catch (e) {
        console.error('Failed to parse Resume Markdown with marked:', e);
        let html = content;
        html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/^- (.*?)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        html = html.replace(/\n\n/g, '</p><p>');
        html = html.replace(/\n/g, '<br>');
        html = '<p>' + html + '</p>';
        return html;
    }
}



// 简历预览模态框
function showResumeInPanel(contentId) {
    const content = window[contentId];
    if (!content) return;
    
    currentResumeContent = content;
    resumeZoomMultiplier = 1.0;
    currentTemplate = 'default';
    
    const isHTML = content.includes('<!DOCTYPE html>') || content.includes('<html') || content.includes('tailwindcss') || content.includes('<div');
    const previewContainer = document.getElementById('resumePreviewContent');
    
    if (isHTML) {
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';
        iframe.style.height = '1100px'; // 初始高度
        iframe.style.border = 'none';
        iframe.style.background = 'white';
        iframe.style.display = 'block';
        iframe.style.flex = '1';
        
        previewContainer.innerHTML = '';
        previewContainer.appendChild(iframe);
        
        iframe.onload = () => {
            adjustIframeHeight(iframe);
            // 监听 iframe 内容的变化，动态调整高度
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            if (iframeDoc && iframeDoc.body) {
                const observer = new MutationObserver(() => {
                    adjustIframeHeight(iframe);
                });
                observer.observe(iframeDoc.body, { childList: true, subtree: true, characterData: true });
            }
        };
        
        iframe.srcdoc = content;
    } else {
        previewContainer.innerHTML = renderResumeContent(content);
        // 如果是纯文本，让外层 div 样式还原
        previewContainer.style.height = 'auto';
        setTimeout(adjustResumeScale, 100);
    }
    
    document.getElementById('zoomLevel').textContent = '100%';
    
    // 重置模板选择UI
    document.querySelectorAll('.template-option').forEach(opt => {
        opt.classList.remove('active');
    });
    const defaultOpt = document.querySelector('.template-option');
    if (defaultOpt) defaultOpt.classList.add('active');
    
    document.getElementById('resumeModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
    
    // 延迟进行 scale 计算以确保尺寸就绪
    setTimeout(adjustResumeScale, 200);
}

// 获取简历中的文本内容（去除HTML标签）
function extractResumeText(html) {
    const temp = document.createElement('div');
    temp.innerHTML = html;
    return temp.textContent || temp.innerText || '';
}

// 使用模板重新渲染简历
function renderResumeWithTemplate(templateName) {
    if (!currentResumeContent) return;
    
    const previewContainer = document.getElementById('resumePreviewContent');
    const iframe = previewContainer.querySelector('iframe');
    
    if (!iframe) return;
    
    // 如果是默认模板，使用原始内容
    if (templateName === 'default') {
        iframe.srcdoc = currentResumeContent;
        return;
    }
    
    try {
        // 从原始简历内容中提取body内容
        const parser = new DOMParser();
        const doc = parser.parseFromString(currentResumeContent, 'text/html');
        const bodyContent = doc.body.innerHTML;
        
        // 通用SVG图标样式
        const svgStyle = `
            svg { width: 16px; height: 16px; display: inline-block; vertical-align: middle; flex-shrink: 0; max-width: 16px; }
            svg[width="20"], svg[width="18"] { width: 18px; height: 18px; max-width: 18px; }
            svg[width="14"] { width: 14px; height: 14px; max-width: 14px; }
            h2 svg, h3 svg { width: 18px; height: 18px; margin-right: 6px; max-width: 18px; }
            section svg { width: 16px; height: 16px; max-width: 16px; }
        `;
        
        // 获取模板样式
        const templateStyles = {
            'modern': `
                ${svgStyle}
                body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
                .resume-container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); border-radius: 8px; }
                h1 { font-size: 28px; font-weight: 700; color: #1f2937; margin: 0 0 8px 0; padding-bottom: 12px; border-bottom: 3px solid #3b82f6; }
                h2 { font-size: 18px; font-weight: 600; color: #1f2937; margin: 24px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #e5e7eb; display: flex; align-items: center; gap: 8px; }
                h3 { font-size: 16px; font-weight: 600; color: #374151; margin: 16px 0 8px 0; display: flex; align-items: center; gap: 6px; }
                p, li { font-size: 14px; color: #4b5563; line-height: 1.8; margin: 4px 0; }
                ul { padding-left: 20px; }
                strong { color: #1f2937; }
            `,
            'professional': `
                ${svgStyle}
                body { font-family: 'Georgia', 'SimSun', serif; background: #f9fafb; margin: 0; padding: 20px; color: #1f2937; }
                .resume-container { max-width: 800px; margin: 0 auto; background: white; padding: 50px 60px; box-shadow: 0 2px 20px rgba(0,0,0,0.08); }
                h1 { font-size: 28px; font-weight: 700; color: #111827; text-align: center; letter-spacing: 4px; margin: 0 0 8px 0; padding-bottom: 16px; border-bottom: 2px solid #d1d5db; }
                h2 { font-size: 16px; font-weight: 700; color: #374151; text-transform: uppercase; letter-spacing: 2px; margin: 28px 0 12px 0; padding-bottom: 8px; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center; gap: 8px; }
                h3 { font-size: 15px; font-weight: 600; color: #1f2937; margin: 16px 0 6px 0; display: flex; align-items: center; gap: 6px; }
                p, li { font-size: 14px; color: #4b5563; line-height: 1.8; margin: 4px 0; }
                ul { padding-left: 20px; }
                strong { color: #111827; }
            `,
            'creative': `
                ${svgStyle}
                body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #ecfdf5; margin: 0; padding: 20px; }
                .resume-container { max-width: 800px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
                .resume-header { background: #059669; color: white; padding: 30px 40px; }
                .resume-header h1 { font-size: 32px; font-weight: 700; color: white; margin: 0 0 8px 0; border: none; padding: 0; }
                .resume-header p { color: rgba(255,255,255,0.9); margin: 4px 0; }
                .resume-body { padding: 30px 40px; }
                h2 { font-size: 20px; font-weight: 600; color: #059669; margin: 24px 0 12px 0; display: flex; align-items: center; gap: 10px; }
                h2 svg { color: #059669; }
                h2::after { content: ''; flex: 1; height: 2px; background: linear-gradient(to right, #059669, transparent); }
                h3 { font-size: 16px; font-weight: 600; color: #1f2937; margin: 16px 0 8px 0; display: flex; align-items: center; gap: 6px; }
                p, li { font-size: 14px; color: #4b5563; line-height: 1.8; margin: 4px 0; }
                ul { padding-left: 20px; }
                strong { color: #1f2937; }
            `,
            'minimalist': `
                ${svgStyle}
                body { font-family: 'Helvetica Neue', 'Arial', 'PingFang SC', sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
                .resume-container { max-width: 800px; margin: 0 auto; background: white; display: grid; grid-template-columns: 240px 1fr; min-height: 800px; box-shadow: 0 2px 16px rgba(0,0,0,0.08); }
                .resume-sidebar { background: #1e293b; color: white; padding: 30px 20px; }
                .resume-sidebar h1 { font-size: 22px; font-weight: 700; color: white; margin: 0 0 8px 0; letter-spacing: 2px; border: none; padding: 0; }
                .resume-sidebar h3 { font-size: 12px; font-weight: 600; color: #60a5fa; text-transform: uppercase; letter-spacing: 2px; margin: 20px 0 10px 0; padding-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center; gap: 6px; }
                .resume-sidebar svg { color: #60a5fa; }
                .resume-sidebar p, .resume-sidebar li { font-size: 13px; color: #cbd5e1; line-height: 1.7; margin: 3px 0; }
                .resume-main { padding: 30px; }
                .resume-main h2 { font-size: 18px; font-weight: 600; color: #1e293b; margin: 24px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #3b82f6; display: flex; align-items: center; gap: 8px; }
                .resume-main h3 { font-size: 15px; font-weight: 600; color: #374151; margin: 14px 0 6px 0; display: flex; align-items: center; gap: 6px; }
                .resume-main p, .resume-main li { font-size: 14px; color: #4b5563; line-height: 1.7; margin: 4px 0; }
                ul { padding-left: 18px; }
                strong { color: #1f2937; }
            `,
            'tech': `
                ${svgStyle}
                body { font-family: 'SF Pro Display', 'PingFang SC', sans-serif; background: #f8fafc; margin: 0; padding: 20px; color: #334155; }
                .resume-container { max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #e2e8f0; }
                .resume-header { background: #0f172a; padding: 30px 40px; }
                .resume-header h1 { font-size: 30px; font-weight: 700; color: white; margin: 0 0 8px 0; border: none; padding: 0; }
                .resume-header p { color: #94a3b8; margin: 4px 0; }
                .resume-body { padding: 30px 40px; }
                h2 { font-size: 18px; font-weight: 600; color: #0f172a; margin: 24px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #3b82f6; display: flex; align-items: center; gap: 8px; }
                h2 svg { color: #3b82f6; }
                h3 { font-size: 16px; font-weight: 600; color: #1e293b; margin: 14px 0 6px 0; display: flex; align-items: center; gap: 6px; }
                p, li { font-size: 14px; color: #475569; line-height: 1.8; margin: 4px 0; }
                ul { padding-left: 20px; }
                strong { color: #0f172a; }
                li::marker { color: #3b82f6; }
            `,
            'elegant': `
                ${svgStyle}
                body { font-family: 'Georgia', 'SimSun', serif; background: #fefce8; margin: 0; padding: 20px; color: #333; }
                .resume-container { max-width: 800px; margin: 0 auto; background: white; padding: 50px 60px; box-shadow: 0 4px 24px rgba(0,0,0,0.06); border: 1px solid #e5e7eb; }
                h1 { font-size: 32px; font-weight: 400; color: #1f2937; text-align: center; letter-spacing: 6px; margin: 0 0 12px 0; padding-bottom: 16px; border-bottom: 1px solid #d1d5db; }
                h2 { font-size: 15px; font-weight: 400; color: #6b7280; text-transform: uppercase; letter-spacing: 3px; text-align: center; margin: 28px 0 16px 0; position: relative; display: flex; align-items: center; justify-content: center; gap: 10px; }
                h2::before, h2::after { content: ''; width: 50px; height: 1px; background: #d1d5db; }
                h2 svg { display: none; }
                h3 { font-size: 15px; font-weight: 600; color: #1f2937; margin: 14px 0 6px 0; display: flex; align-items: center; gap: 6px; }
                p, li { font-size: 14px; color: #4b5563; line-height: 1.8; margin: 4px 0; }
                ul { padding-left: 20px; }
                strong { color: #1f2937; }
                .resume-item { text-align: center; margin-bottom: 20px; }
                .resume-item h3 { margin-bottom: 4px; }
                .resume-item p { color: #6b7280; }
            `,
            'duotone': `
                ${svgStyle}
                body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
                .resume-container { max-width: 800px; margin: 0 auto; background: white; display: grid; grid-template-columns: 250px 1fr; min-height: 800px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
                .resume-sidebar { background: #1e3a5f; color: white; padding: 30px 20px; }
                .resume-sidebar h1 { font-size: 22px; font-weight: 700; color: white; margin: 0 0 8px 0; border: none; padding: 0; }
                .resume-sidebar h3 { font-size: 11px; font-weight: 600; color: #60a5fa; text-transform: uppercase; letter-spacing: 2px; margin: 18px 0 10px 0; padding-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.15); display: flex; align-items: center; gap: 6px; }
                .resume-sidebar svg { color: #60a5fa; }
                .resume-sidebar p, .resume-sidebar li { font-size: 13px; color: #cbd5e1; line-height: 1.6; margin: 3px 0; }
                .resume-main { padding: 30px; }
                .resume-main h2 { font-size: 17px; font-weight: 600; color: #1e3a5f; margin: 22px 0 10px 0; display: flex; align-items: center; gap: 10px; }
                .resume-main h2::before { content: ''; width: 4px; height: 18px; background: #2563eb; border-radius: 2px; }
                .resume-main h3 { font-size: 15px; font-weight: 600; color: #1f2937; margin: 12px 0 6px 0; display: flex; align-items: center; gap: 6px; }
                .resume-main p, .resume-main li { font-size: 14px; color: #4b5563; line-height: 1.7; margin: 4px 0; }
                ul { padding-left: 18px; }
                strong { color: #1f2937; }
            `
        };
        
        // 创建新的HTML内容
        const style = templateStyles[templateName] || '';
        
        // 包装内容
        let newHTML;
        if (['minimalist', 'duotone'].includes(templateName)) {
            // 双栏布局模板 - 从原始内容中提取侧边栏和主内容
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = bodyContent;
            
            // 找到第一个section或h2作为分界点
            let sidebarContent = '';
            let mainContent = '';
            let foundFirstSection = false;
            
            // 获取所有直接子元素
            const children = Array.from(tempDiv.children);
            for (const child of children) {
                // 检查是否是section或包含h2
                const isSection = child.tagName === 'SECTION' || child.classList.contains('section');
                const hasH2 = child.querySelector('h2') || child.tagName === 'H2';
                
                if (!foundFirstSection && (isSection || hasH2)) {
                    foundFirstSection = true;
                }
                
                if (!foundFirstSection) {
                    sidebarContent += child.outerHTML;
                } else {
                    mainContent += child.outerHTML;
                }
            }
            
            // 如果没有明确分离，使用默认分离（第一个div作为侧边栏）
            if (!sidebarContent || !mainContent) {
                // 尝试找到header或第一个div
                const header = tempDiv.querySelector('header, .header, [class*="header"]');
                if (header) {
                    sidebarContent = header.outerHTML;
                    mainContent = bodyContent.replace(header.outerHTML, '');
                } else {
                    sidebarContent = '<h1>姓名</h1><p>联系方式</p>';
                    mainContent = bodyContent;
                }
            }
            
            newHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>${style}</style>
</head>
<body>
    <div class="resume-container">
        <div class="resume-sidebar">
            ${sidebarContent}
        </div>
        <div class="resume-main">
            ${mainContent}
        </div>
    </div>
</body>
</html>`;
        } else {
            // 单栏布局模板
            newHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>${style}</style>
</head>
<body>
    <div class="resume-container">
        ${bodyContent}
    </div>
</body>
</html>`;
        }
        
        iframe.srcdoc = newHTML;
        
    } catch (e) {
        console.error('应用模板失败:', e);
        modal.toast('模板应用失败', 'error');
    }
}

// 简历编辑和模板相关变量
let isEditMode = false;
let currentTemplate = 'default';

let resumeZoomMultiplier = 1.0;

function closeResumeModal() {
    document.getElementById('resumeModal').style.display = 'none';
    document.body.style.overflow = '';
    currentResumeContent = null;
    resumeZoomMultiplier = 1.0;
    document.getElementById('zoomLevel').textContent = '100%';
    isEditMode = false;
    currentTemplate = 'default';
}

// 动态根据简历预览 Modal body 宽度对 800px width 的简历进行 transform 缩放
function adjustResumeScale() {
    const modalBody = document.querySelector('.resume-modal-body');
    const paper = document.getElementById('resumePreviewContent');
    if (!modalBody || !paper) return;
    
    const containerWidth = modalBody.clientWidth;
    const padding = window.innerWidth <= 768 ? 16 : 32; // 移动端 16px 间距，PC端 32px 间距
    const targetWidth = 800;
    
    // 计算刚好贴合容器宽度的基础比例
    let baselineScale = (containerWidth - padding) / targetWidth;
    if (baselineScale > 1) baselineScale = 1;
    
    // 应用用户的缩放系数
    const finalScale = baselineScale * resumeZoomMultiplier;
    
    // 缩放 resume-paper
    paper.style.transform = `scale(${finalScale})`;
    
    // 调整外层 wrapper 的尺寸以完全消除 transform 导致的高度塌陷/底部空白
    const paperWrapper = document.getElementById('resumePaperWrapper') || paper.parentElement;
    const iframe = paper.querySelector('iframe');
    const originalHeight = iframe ? (iframe.offsetHeight || 1100) : (paper.scrollHeight || 1100);
    
    paperWrapper.style.height = (originalHeight * finalScale) + 'px';
    paperWrapper.style.width = (targetWidth * finalScale) + 'px';
}

function zoomResume(delta) {
    resumeZoomMultiplier = Math.max(0.5, Math.min(2.0, resumeZoomMultiplier + delta));
    adjustResumeScale();
    document.getElementById('zoomLevel').textContent = Math.round(resumeZoomMultiplier * 100) + '%';
}

// 动态拉伸 iframe 高度，消除内部滚动条，杜绝双滚动条
function adjustIframeHeight(iframe) {
    try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        if (iframeDoc && iframeDoc.body) {
            // 临时将高度置为 auto，以获取准确的 scrollHeight
            iframeDoc.body.style.height = 'auto';
            iframeDoc.documentElement.style.height = 'auto';
            const contentHeight = Math.max(
                iframeDoc.body.scrollHeight,
                iframeDoc.documentElement.scrollHeight,
                iframeDoc.body.offsetHeight,
                iframeDoc.documentElement.offsetHeight
            );
            iframe.style.height = (contentHeight + 20) + 'px';
            
            // 高度改变后，必须重新计算外部 transform 和 wrapper 大小
            adjustResumeScale();
        }
    } catch (e) {
        console.error('动态拉伸iframe高度失败:', e);
    }
}

// 切换编辑模式
function toggleEditMode() {
    isEditMode = !isEditMode;
    const previewContainer = document.getElementById('resumePreviewContent');
    const editBtnText = document.getElementById('editBtnText');
    const saveEditBtn = document.getElementById('saveEditBtn');
    const iframe = previewContainer.querySelector('iframe');
    
    if (isEditMode) {
        editBtnText.textContent = '取消编辑';
        saveEditBtn.style.display = 'inline-flex';
        
        if (iframe) {
            // 在iframe中启用编辑
            try {
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                iframeDoc.body.contentEditable = 'true';
                iframeDoc.body.style.outline = '2px dashed #1a73e8';
                iframeDoc.body.style.outlineOffset = '4px';
                iframeDoc.body.style.cursor = 'text';
                
                // 添加编辑提示
                const hint = iframeDoc.createElement('div');
                hint.id = 'editHint';
                hint.style.cssText = 'position:fixed;top:10px;left:50%;transform:translateX(-50%);background:#1a73e8;color:white;padding:8px 16px;border-radius:6px;font-size:14px;z-index:9999;';
                hint.textContent = '点击任意文字即可编辑';
                iframeDoc.body.appendChild(hint);
                setTimeout(() => hint.remove(), 3000);
            } catch (e) {
                console.error('无法启用iframe编辑:', e);
                modal.toast('编辑模式不支持此简历格式', 'error');
                isEditMode = false;
                editBtnText.textContent = '编辑';
                saveEditBtn.style.display = 'none';
            }
        }
    } else {
        editBtnText.textContent = '编辑';
        saveEditBtn.style.display = 'none';
        
        if (iframe) {
            try {
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                iframeDoc.body.contentEditable = 'false';
                iframeDoc.body.style.outline = 'none';
                iframeDoc.body.style.cursor = 'default';
            } catch (e) {
                console.error('无法关闭iframe编辑:', e);
            }
        }
    }
}

// 保存简历编辑
function saveResumeEdit() {
    const previewContainer = document.getElementById('resumePreviewContent');
    const iframe = previewContainer.querySelector('iframe');
    
    if (iframe) {
        try {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            const editedContent = iframeDoc.documentElement.outerHTML;
            currentResumeContent = editedContent;
            
            // 关闭编辑模式
            isEditMode = false;
            document.getElementById('editBtnText').textContent = '编辑';
            document.getElementById('saveEditBtn').style.display = 'none';
            iframeDoc.body.contentEditable = 'false';
            iframeDoc.body.style.outline = 'none';
            
            modal.toast('修改已保存', 'success');
        } catch (e) {
            console.error('保存编辑失败:', e);
            modal.toast('保存失败', 'error');
        }
    }
}

// 切换模板面板
function toggleTemplatePanel() {
    const panel = document.getElementById('templatePanel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

// 切换模板
function switchTemplate(templateName) {
    currentTemplate = templateName;
    
    // 更新模板选择UI
    document.querySelectorAll('.template-option').forEach(opt => {
        opt.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // 隐藏模板面板
    document.getElementById('templatePanel').style.display = 'none';
    
    // 应用模板样式
    applyTemplate(templateName);
    
    // 重新渲染简历
    renderResumeWithTemplate(templateName);
    
    modal.toast('已切换到' + getTemplateName(templateName) + '模板', 'success');
}

// 获取模板名称
function getTemplateName(template) {
    const names = {
        'default': '默认模板',
        'modern': '现代简约',
        'professional': '专业商务',
        'creative': '创意设计',
        'minimalist': '简洁商务',
        'tech': '科技风格',
        'elegant': '优雅风格',
        'duotone': '双色现代'
    };
    return names[template] || template;
}

// 应用模板样式
function applyTemplate(templateName) {
    const previewContainer = document.getElementById('resumePreviewContent');
    const iframe = previewContainer.querySelector('iframe');
    
    if (!iframe) return;
    
    try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        const style = iframeDoc.getElementById('templateStyle') || iframeDoc.createElement('style');
        style.id = 'templateStyle';
        
        const templates = {
            'default': '',
            'modern': `
                body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f5f5; }
                .resume { max-width: 800px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }
                h1 { font-size: 32px; font-weight: 700; color: #2c3e50; margin-bottom: 8px; }
                h2 { font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 2px solid #3498db; }
                h3 { font-size: 16px; font-weight: 600; color: #2c3e50; margin-bottom: 5px; }
                p, li { font-size: 14px; color: #555; line-height: 1.8; }
            `,
            'professional': `
                body { font-family: 'Georgia', 'SimSun', serif; background: #f5f5f5; color: #333; }
                .resume { max-width: 800px; margin: 0 auto; background: white; padding: 50px 60px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }
                h1 { font-size: 32px; font-weight: 700; color: #1a365d; text-align: center; letter-spacing: 4px; margin-bottom: 8px; }
                h2 { font-size: 16px; font-weight: 700; color: #1a365d; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid #e2e8f0; }
                h3 { font-size: 15px; font-weight: 700; color: #2d3748; margin-bottom: 5px; }
                p, li { font-size: 14px; color: #4a5568; line-height: 1.8; }
            `,
            'creative': `
                body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f0fdf4; color: #333; }
                .resume { max-width: 800px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
                header { background: #059669; color: white; padding: 40px; text-align: center; }
                h1 { font-size: 36px; font-weight: 700; color: white; margin-bottom: 10px; }
                h2 { font-size: 20px; font-weight: 600; color: #059669; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
                h2::after { content: ''; flex: 1; height: 2px; background: linear-gradient(to right, #059669, transparent); }
                h3 { font-size: 16px; font-weight: 600; color: #1f2937; margin-bottom: 5px; }
                p, li { font-size: 14px; color: #4b5563; line-height: 1.8; }
                section { padding: 0 40px 30px; }
            `,
            'minimalist': `
                body { font-family: 'Helvetica Neue', 'Arial', 'PingFang SC', sans-serif; background: #f5f5f5; color: #333; }
                .resume { max-width: 800px; margin: 0 auto; background: white; display: grid; grid-template-columns: 250px 1fr; min-height: 1000px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }
                header, .sidebar { background: #2c3e50; color: white; padding: 40px 25px; }
                main, .main-content { padding: 40px 35px; }
                h1 { font-size: 24px; font-weight: 700; color: white; letter-spacing: 2px; margin-bottom: 8px; }
                h2 { font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 2px solid #3498db; }
                h3 { font-size: 14px; font-weight: 600; color: #3498db; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 15px; }
                p, li { font-size: 13px; color: #555; line-height: 1.7; }
            `,
            'tech': `
                body { font-family: 'SF Pro Display', 'PingFang SC', sans-serif; background: #f8fafc; color: #334155; }
                .resume { max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }
                header { background: #1e293b; padding: 40px; }
                h1 { font-size: 32px; font-weight: 700; color: white; margin-bottom: 10px; }
                h2 { font-size: 18px; font-weight: 600; color: #1e293b; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 2px solid #3b82f6; }
                h3 { font-size: 16px; font-weight: 600; color: #334155; margin-bottom: 5px; }
                p, li { font-size: 14px; color: #475569; line-height: 1.8; }
                section { padding: 30px 40px; }
                .item { background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6; border-radius: 8px; padding: 18px; margin-bottom: 20px; }
            `,
            'elegant': `
                body { font-family: 'Georgia', 'SimSun', serif; background: #f5f0eb; color: #333; }
                .resume { max-width: 800px; margin: 0 auto; background: white; padding: 50px 60px; box-shadow: 0 4px 30px rgba(0,0,0,0.1); border: 1px solid #e0d5c7; }
                h1 { font-size: 36px; font-weight: 400; color: #2c2c2c; letter-spacing: 8px; text-align: center; margin-bottom: 10px; }
                h2 { font-size: 16px; font-weight: 400; color: #8b7355; text-transform: uppercase; letter-spacing: 4px; text-align: center; margin-bottom: 20px; position: relative; }
                h2::before, h2::after { content: ''; position: absolute; top: 50%; width: 60px; height: 1px; background: #d4c5b2; }
                h2::before { left: 0; }
                h2::after { right: 0; }
                h3 { font-size: 16px; font-weight: 600; color: #2c2c2c; margin-bottom: 5px; }
                p, li { font-size: 14px; color: #555; line-height: 1.8; }
                .item { text-align: center; margin-bottom: 25px; }
            `,
            'duotone': `
                body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f5f5; color: #333; }
                .resume { max-width: 800px; margin: 0 auto; background: white; display: grid; grid-template-columns: 260px 1fr; min-height: 1000px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
                header, .sidebar { background: #1e3a5f; color: white; padding: 35px 25px; }
                main, .main-content { padding: 35px 30px; }
                h1 { font-size: 22px; font-weight: 700; color: white; margin-bottom: 6px; }
                h2 { font-size: 17px; font-weight: 600; color: #1e3a5f; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
                h2::before { content: ''; width: 4px; height: 20px; background: #2563eb; border-radius: 2px; }
                h3 { font-size: 12px; font-weight: 600; color: #2563eb; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.15); }
                p, li { font-size: 13px; color: #4b5563; line-height: 1.7; }
                .item { background: #f9fafb; border-left: 3px solid #2563eb; border-radius: 8px; padding: 16px; margin-bottom: 18px; }
            `
        };
        
        style.textContent = templates[templateName] || '';
        
        if (!iframeDoc.getElementById('templateStyle')) {
            iframeDoc.head.appendChild(style);
        }
    } catch (e) {
        console.error('应用模板失败:', e);
    }
}

// 后台离线捕获已渲染 iframe 的内容为 Canvas（固定宽度 794px，保持 A4 纸张排版）
function captureIframeContent(sourceIframe, width = 794) {
    return new Promise((resolve, reject) => {
        try {
            const tempIframe = document.createElement('iframe');
            tempIframe.style.position = 'fixed';
            tempIframe.style.left = '-9999px';
            tempIframe.style.top = '0';
            tempIframe.style.width = width + 'px';
            tempIframe.style.height = '1200px'; // 初始高度
            tempIframe.style.border = 'none';
            tempIframe.style.zIndex = '99999';
            
            document.body.appendChild(tempIframe);
            
            const sourceDoc = sourceIframe.contentDocument || sourceIframe.contentWindow.document;
            const tempDoc = tempIframe.contentDocument || tempIframe.contentWindow.document;
            
            // 写入完整的 documentElement HTML
            tempDoc.open();
            tempDoc.write(sourceDoc.documentElement.outerHTML);
            tempDoc.close();
            
            const executeCapture = async () => {
                try {
                    await new Promise(r => setTimeout(r, 600));
                    
                    const body = tempDoc.body;
                    const html = tempDoc.documentElement;
                    const height = Math.max(body.scrollHeight, body.offsetHeight, html.clientHeight, html.scrollHeight, html.offsetHeight);
                    tempIframe.style.height = height + 'px';
                    
                    // 等待重绘完成
                    await new Promise(r => setTimeout(r, 200));
                    
                    const canvas = await html2canvas(tempDoc.body, {
                        scale: 2,
                        useCORS: true,
                        logging: false,
                        backgroundColor: '#ffffff',
                        allowTaint: true,
                        width: width,
                        height: height,
                        windowWidth: width,
                        windowHeight: height
                    });
                    
                    document.body.removeChild(tempIframe);
                    resolve(canvas);
                } catch (err) {
                    if (tempIframe.parentNode) {
                        document.body.removeChild(tempIframe);
                    }
                    reject(err);
                }
            };
            
            tempIframe.onload = executeCapture;
            // 兜底执行，防止 onload 未触发
            setTimeout(() => {
                if (tempIframe.parentNode) {
                    executeCapture();
                }
            }, 800);
            
        } catch (e) {
            reject(e);
        }
    });
}

// 后台离线捕获原生 HTML 字符串内容为 Canvas（固定宽度 794px）
function captureHTMLContent(htmlContent, width = 794) {
    return new Promise((resolve, reject) => {
        try {
            const tempIframe = document.createElement('iframe');
            tempIframe.style.position = 'fixed';
            tempIframe.style.left = '-9999px';
            tempIframe.style.top = '0';
            tempIframe.style.width = width + 'px';
            tempIframe.style.height = '1200px';
            tempIframe.style.border = 'none';
            tempIframe.style.zIndex = '99999';
            
            document.body.appendChild(tempIframe);
            
            const tempDoc = tempIframe.contentDocument || tempIframe.contentWindow.document;
            
            tempDoc.open();
            tempDoc.write(htmlContent);
            tempDoc.close();
            
            const executeCapture = async () => {
                try {
                    await new Promise(r => setTimeout(r, 600));
                    
                    const body = tempDoc.body;
                    const html = tempDoc.documentElement;
                    const height = Math.max(body.scrollHeight, body.offsetHeight, html.clientHeight, html.scrollHeight, html.offsetHeight);
                    tempIframe.style.height = height + 'px';
                    
                    await new Promise(r => setTimeout(r, 200));
                    
                    const canvas = await html2canvas(tempDoc.body, {
                        scale: 2,
                        useCORS: true,
                        logging: false,
                        backgroundColor: '#ffffff',
                        allowTaint: true,
                        width: width,
                        height: height,
                        windowWidth: width,
                        windowHeight: height
                    });
                    
                    document.body.removeChild(tempIframe);
                    resolve(canvas);
                } catch (err) {
                    if (tempIframe.parentNode) {
                        document.body.removeChild(tempIframe);
                    }
                    reject(err);
                }
            };
            
            tempIframe.onload = executeCapture;
            setTimeout(() => {
                if (tempIframe.parentNode) {
                    executeCapture();
                }
            }, 800);
            
        } catch (e) {
            reject(e);
        }
    });
}

// 下载功能
async function downloadResumeAsImage() {
    if (!currentResumeContent) return;
    
    try {
        modal.toast('正在生成图片...', 'info');
        
        const previewContainer = document.getElementById('resumePreviewContent');
        const existingIframe = previewContainer ? previewContainer.querySelector('iframe') : null;
        
        let canvas = null;
        if (existingIframe) {
            canvas = await captureIframeContent(existingIframe, 794);
        } else {
            const isHTML = currentResumeContent.includes('<!DOCTYPE html>') || currentResumeContent.includes('<html') || currentResumeContent.includes('tailwindcss') || currentResumeContent.includes('<div');
            let finalHTML = currentResumeContent;
            if (!isHTML) {
                finalHTML = `
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body { font-family: 'Microsoft YaHei', 'SimSun', Arial, sans-serif; padding: 40px; line-height: 1.6; }
                    </style>
                </head>
                <body>
                    ${renderResumeContent(currentResumeContent)}
                </body>
                </html>`;
            }
            canvas = await captureHTMLContent(finalHTML, 794);
        }
        
        if (!canvas) throw new Error('无法生成Canvas');
        
        const link = document.createElement('a');
        link.download = 'resume.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
        
        modal.toast('图片下载成功', 'success');
    } catch (err) {
        console.error('下载图片失败:', err);
        modal.toast('下载图片失败', 'error');
    }
}

async function downloadResumeAsPDF(content) {
    if (!content) content = currentResumeContent;
    if (!content) return;
    
    try {
        modal.toast('正在生成PDF...', 'info');
        
        if (!window.jspdf || !window.jspdf.jsPDF) {
            console.error('jsPDF未加载');
            modal.toast('PDF库加载失败，请刷新页面重试', 'error');
            return;
        }
        
        const previewContainer = document.getElementById('resumePreviewContent');
        const existingIframe = previewContainer ? previewContainer.querySelector('iframe') : null;
        
        let canvas = null;
        
        if (content === currentResumeContent && existingIframe) {
            canvas = await captureIframeContent(existingIframe, 794);
        } else {
            const isHTML = content.includes('<!DOCTYPE html>') || content.includes('<html') || content.includes('tailwindcss') || content.includes('<div');
            let finalHTML = content;
            if (!isHTML) {
                finalHTML = `
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body { font-family: 'Microsoft YaHei', 'SimSun', Arial, sans-serif; padding: 40px; line-height: 1.6; }
                    </style>
                </head>
                <body>
                    ${renderResumeContent(content)}
                </body>
                </html>`;
            }
            canvas = await captureHTMLContent(finalHTML, 794);
        }
        
        if (!canvas) throw new Error('无法生成Canvas');
        
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('p', 'mm', 'a4');
        
        const pdfWidth = 210;
        const pdfHeight = 297;
        const margin = 10;
        
        const imgWidth = pdfWidth - margin * 2;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        
        let heightLeft = imgHeight;
        let position = margin;
        let page = 0;
        
        const imgData = canvas.toDataURL('image/jpeg', 0.92);
        pdf.addImage(imgData, 'JPEG', margin, position, imgWidth, imgHeight);
        heightLeft -= (pdfHeight - margin * 2);
        
        while (heightLeft > 0) {
            page++;
            pdf.addPage();
            position = -(pdfHeight - margin * 2) * page + margin;
            pdf.addImage(imgData, 'JPEG', margin, position, imgWidth, imgHeight);
            heightLeft -= (pdfHeight - margin * 2);
        }
        
        pdf.save('resume.pdf');
        modal.toast('PDF下载成功', 'success');
    } catch (err) {
        console.error('生成PDF失败:', err);
        modal.toast('PDF生成失败: ' + err.message, 'error');
    }
}

function toggleSidePanel() {
    const panel = document.getElementById('sidePanel');
    if (panel.classList.contains('expanded')) {
        panel.classList.remove('expanded');
        panel.classList.add('collapsed');
    } else {
        panel.classList.add('expanded');
        panel.classList.remove('collapsed');
    }
}

// 通用简历文件下载（HTML/非PDF格式）
async function _fetchAndDownloadResume(content, format) {
    try {
        const res = await fetch('/api/download/resume', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ content: content, filename: 'resume', format: format })
        });
        
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'resume.' + format;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            modal.toast('下载成功', 'success');
        } else {
            const data = await res.json();
            modal.toast(data.error || '下载失败', 'error');
        }
    } catch (err) {
        modal.toast('下载失败', 'error');
    }
}

async function downloadFromPanel(format = 'html') {
    if (!currentResumeContent) return;
    if (format === 'pdf') {
        await downloadResumeAsPDF(currentResumeContent);
        return;
    }
    await _fetchAndDownloadResume(currentResumeContent, format);
}

async function downloadResume(contentId, format = 'html') {
    const content = window[contentId];
    if (!content) return;
    if (format === 'pdf') {
        await downloadResumeAsPDF(content);
        return;
    }
    await _fetchAndDownloadResume(content, format);
}

// 复制消息
function copyMessage(btn) {
    const content = btn.parentElement.querySelector('.message-content').innerText;
    navigator.clipboard.writeText(content).then(() => {
        btn.classList.add('copied');
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
        setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>';
        }, 2000);
    });
}

// 推理时间线构建
function buildReasoningTimeline(steps) {
    const iconMap = {
        'intent_analysis': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
        'agent_call': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M12 2a4 4 0 014 4v2a4 4 0 01-8 0V6a4 4 0 014-4z"/><path d="M6 10v8a6 6 0 0012 0v-8"/></svg>',
        'task_split': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M12 22v-8.3a4 4 0 00-1.172-2.872L3 3"/><path d="m15 9 6-6"/></svg>',
        'quality_check': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>',
        'result_merge': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>',
        'parallel_start': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
        'execution_start': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
        'error_recovery': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M21 12a9 9 0 11-6.219-8.56"/><path d="M21 3v5h-5"/></svg>',
        'tool': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>'
    };

    const typeClassMap = {
        'intent_analysis': 'intent',
        'agent_call': 'agent',
        'task_split': 'split',
        'quality_check': 'check',
        'result_merge': 'merge',
        'parallel_start': 'parallel',
        'execution_start': 'parallel',
        'error_recovery': 'recovery',
        'tool': 'tool'
    };

    let html = '<div class="reasoning-timeline">';
    html += '<div class="reasoning-header" onclick="toggleReasoningTimeline(this)">';
    html += '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>';
    html += '<span>工具调用</span>';
    html += '<svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M6 9l6 6 6-6"/></svg>';
    html += '</div>';
    html += '<div class="reasoning-body">';
    
    steps.forEach((step, index) => {
        const stepType = step.type || (step.action ? 'tool' : 'intent_analysis');
        const stepTitle = escapeHtml(step.title || step.action || '处理中');
        const stepDetail = escapeHtml(step.detail || step.output || '');
        const stepStatus = step.status || 'completed';
        
        const icon = iconMap[stepType] || '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>';
        const typeClass = typeClassMap[stepType] || 'intent';
        
        html += '<div class="timeline-step">';
        if (index < steps.length - 1) {
            html += '<div class="timeline-line"></div>';
        }
        html += '<div class="timeline-dot ' + typeClass + ' ' + stepStatus + '">';
        html += icon;
        html += '</div>';
        html += '<div class="timeline-content">';
        html += '<div class="timeline-title">' + stepTitle + '</div>';
        
        if (stepDetail) {
            const truncatedDetail = stepDetail.length > 150 ? stepDetail.substring(0, 150) + '...' : stepDetail;
            html += '<div class="timeline-detail">' + truncatedDetail + '</div>';
        }
        
        let extraInfo = '';
        if (step.confidence) {
            const confidencePercent = Math.round(step.confidence * 100);
            const confidenceClass = confidencePercent >= 80 ? 'high' : confidencePercent >= 60 ? 'medium' : 'low';
            extraInfo += `<span class="confidence-badge ${confidenceClass}">${confidencePercent}%</span>`;
        }
        if (step.duration) {
            extraInfo += `<span class="duration-badge">${step.duration.toFixed(1)}s</span>`;
        }
        if (step.quality_score !== undefined) {
            const scoreClass = step.quality_score >= 80 ? 'high' : step.quality_score >= 60 ? 'medium' : 'low';
            extraInfo += `<span class="score-badge ${scoreClass}">${step.quality_score}</span>`;
        }
        
        if (extraInfo) {
            html += '<div class="timeline-meta">' + extraInfo + '</div>';
        }
        
        if (step.tool_calls && step.tool_calls.length > 0) {
            html += '<div class="tool-calls">';
            step.tool_calls.forEach(tc => {
                html += '<div class="tool-call">';
                html += '<div class="tool-name">' + (tc.name || tc.action) + '</div>';
                if (tc.args) {
                    html += '<div class="tool-args">' + JSON.stringify(tc.args).substring(0, 100) + '</div>';
                }
                if (tc.output) {
                    html += '<div class="tool-output">' + tc.output.substring(0, 80) + '</div>';
                }
                html += '</div>';
            });
            html += '</div>';
        }
        
        if (step.agent) {
            const agentIcon = getAgentIcon(step.agent);
            const agentColor = getAgentColor(step.agent);
            html += `<div class="timeline-agent" style="color: ${agentColor};">`;
            html += agentIcon || '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
            html += getAgentName(step.agent);
            html += '</div>';
        }
        
        html += '</div>';
        html += '</div>';
    });
    
    html += '</div>';
    html += '</div>';
    
    return html;
}

function toggleReasoningTimeline(header) {
    const timeline = header.closest('.reasoning-timeline');
    if (timeline) {
        timeline.classList.toggle('collapsed');
    }
}

function updateExecutionSteps(steps) {
    if (!steps || steps.length === 0) {
        document.getElementById('executionStepsPanel').innerHTML = 
            '<p style="font-size: 0.8125rem; color: var(--text-tertiary);">无执行步骤</p>';
        return;
    }

    const iconMap = {
        'intent_analysis': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
        'agent_call': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M12 2a4 4 0 014 4v2a4 4 0 01-8 0V6a4 4 0 014-4z"/><path d="M6 10v8a6 6 0 0012 0v-8"/></svg>',
        'task_split': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M12 22v-8.3a4 4 0 00-1.172-2.872L3 3"/><path d="m15 9 6-6"/></svg>',
        'quality_check': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>',
        'result_merge': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>',
        'parallel_start': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
        'execution_start': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
        'error_recovery': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M21 12a9 9 0 11-6.219-8.56"/><path d="M21 3v5h-5"/></svg>'
    };

    const typeClassMap = {
        'intent_analysis': 'intent',
        'agent_call': 'agent',
        'task_split': 'split',
        'quality_check': 'check',
        'result_merge': 'merge',
        'parallel_start': 'parallel',
        'execution_start': 'parallel',
        'error_recovery': 'recovery'
    };

    let html = '';
    steps.forEach((step, index) => {
        const icon = iconMap[step.type] || '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>';
        const typeClass = typeClassMap[step.type] || 'intent';
        const statusClass = step.status || 'completed';
        
        let extraInfo = '';
        if (step.confidence) {
            const confidencePercent = Math.round(step.confidence * 100);
            const confidenceClass = confidencePercent >= 80 ? 'high' : confidencePercent >= 60 ? 'medium' : 'low';
            extraInfo += `<span class="confidence-badge ${confidenceClass}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="10" height="10"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                ${confidencePercent}%
            </span>`;
        }
        if (step.duration) {
            extraInfo += `<span class="duration-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="10" height="10"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                ${step.duration.toFixed(1)}s
            </span>`;
        }
        if (step.score !== undefined) {
            const scoreClass = step.score >= 80 ? 'high' : step.score >= 60 ? 'medium' : 'low';
            extraInfo += `<span class="score-badge ${scoreClass}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="10" height="10"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                ${step.score}
            </span>`;
        }
        
        let subtasksHtml = '';
        if (step.subtasks && step.subtasks.length > 0) {
            subtasksHtml = '<div class="subtasks-list">';
            step.subtasks.forEach(st => {
                const dependsText = st.depends_on && st.depends_on.length > 0 ? ` (依赖: ${escapeHtml(st.depends_on.join(', '))})` : '';
                const subtaskIcon = getAgentIcon(st.agent);
                const subtaskColor = getAgentColor(st.agent);
                subtasksHtml += `<div class="subtask-item">
                    <span class="subtask-agent" style="color: ${subtaskColor}; display: inline-flex; align-items: center; gap: 4px;">
                        ${subtaskIcon || ''}
                        ${escapeHtml(getAgentName(st.agent))}
                    </span>
                    <span class="subtask-task">${escapeHtml(st.task)}</span>
                    ${dependsText ? `<span class="subtask-depends">${dependsText}</span>` : ''}
                </div>`;
            });
            subtasksHtml += '</div>';
        }
        
        let agentHtml = '';
        if (step.agent) {
            const agentIcon = getAgentIcon(step.agent);
            const agentColor = getAgentColor(step.agent);
            agentHtml = `<span class="agent-badge" style="color: ${agentColor}; display: inline-flex; align-items: center; gap: 4px;">
                ${agentIcon || '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'}
                ${escapeHtml(getAgentName(step.agent))}
            </span>`;
        }
        
        html += `
            <div class="execution-step">
                <div class="execution-step-icon ${typeClass} ${statusClass}">
                    ${icon}
                </div>
                <div class="execution-step-content">
                    <div class="execution-step-title">${escapeHtml(step.title)}</div>
                    <div class="execution-step-detail">${escapeHtml(step.detail)}</div>
                    ${step.user_intent_summary ? `<div class="execution-step-intent">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
                        ${escapeHtml(step.user_intent_summary)}
                    </div>` : ''}
                    ${step.reasoning ? `<div class="execution-step-reasoning">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
                        ${escapeHtml(step.reasoning)}
                    </div>` : ''}
                    ${subtasksHtml}
                    <div class="execution-step-meta">
                        ${agentHtml}
                        ${extraInfo}
                    </div>
                </div>
            </div>
        `;
        
        if (index < steps.length - 1) {
            html += '<div class="execution-step-connector"></div>';
        }
    });

    document.getElementById('executionStepsPanel').innerHTML = html;
    
    const panel = document.getElementById('sidePanel');
    if (!panel.classList.contains('expanded')) {
        panel.classList.add('expanded');
        panel.classList.remove('collapsed');
    }
}

// Agent图标定义
const agentIcons = {
    'career': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>
        <path d="M12 8l-2 4h4l-2 4" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="12" cy="12" r="2" fill="currentColor"/>
    </svg>`,
    'skill': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
        <path d="M2 17l10 5 10-5"/>
        <path d="M2 12l10 5 10-5"/>
        <path d="M12 8v8" stroke-linecap="round"/>
        <path d="M8 12l4-4 4 4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
    'side_job': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
        <path d="M21 12V7H5a2 2 0 010-4h14v4"/>
        <path d="M3 5v14a2 2 0 002 2h16v-5"/>
        <path d="M18 12a2 2 0 100 4 2 2 0 000-4z"/>
        <path d="M15 8h2M15 16h2" stroke-linecap="round"/>
    </svg>`,
    'resume': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <path d="M12 12h4" stroke-linecap="round"/>
        <path d="M12 16h4" stroke-linecap="round"/>
        <path d="M8 12h.01" stroke-linecap="round"/>
        <path d="M8 16h.01" stroke-linecap="round"/>
    </svg>`,
    'interview': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
        <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/>
        <path d="M19 10v2a7 7 0 01-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
        <circle cx="12" cy="8" r="1" fill="currentColor"/>
    </svg>`
};

const agentColors = {
    'career': '#3b82f6',
    'skill': '#8b5cf6',
    'side_job': '#10b981',
    'resume': '#f59e0b',
    'interview': '#ec4899'
};

function getAgentName(agentKey) {
    const nameMap = {
        'career': '职业规划顾问',
        'skill': '技能发展顾问',
        'side_job': '副业规划专家',
        'resume': '简历优化专家',
        'interview': '面试教练'
    };
    return nameMap[agentKey] || agentKey;
}

function getAgentIcon(agentKey) {
    return agentIcons[agentKey] || '';
}

function getAgentColor(agentKey) {
    return agentColors[agentKey] || '#6b7280';
}

function getAgentNameWithIcon(agentKey) {
    const icon = getAgentIcon(agentKey);
    const name = getAgentName(agentKey);
    const color = getAgentColor(agentKey);
    return `<span class="agent-badge" style="color: ${color}; display: inline-flex; align-items: center; gap: 6px;">${icon} ${name}</span>`;
}

// Agent选择器交互
function toggleAgentDropdown() {
    const dropdown = document.getElementById('agentDropdown');
    const btn = document.getElementById('agentSelectorBtn');
    dropdown.classList.toggle('show');
    btn.classList.toggle('active');
}

function selectAgent(value, text, e) {
    const dropdown = document.getElementById('agentDropdown');
    const btn = document.getElementById('agentSelectorBtn');
    const input = document.getElementById('agentType');
    const textEl = document.getElementById('agentSelectorText');
    const selectedOption = e ? e.currentTarget : document.querySelector(`.agent-option[data-value="${value}"]`);
    
    document.querySelectorAll('.agent-option').forEach(opt => opt.classList.remove('selected'));
    if (selectedOption) selectedOption.classList.add('selected');
    
    const optionIcon = selectedOption ? selectedOption.querySelector('svg') : null;
    const btnIcon = btn.querySelector('svg:first-child');
    if (optionIcon && btnIcon) {
        btnIcon.outerHTML = optionIcon.outerHTML;
    }
    
    input.value = value;
    textEl.textContent = text;
    
    dropdown.classList.remove('show');
    btn.classList.remove('active');
}

// 发送消息
async function sendMessage() {
    const msg = chatInput.value.trim();
    if ((!msg && !uploadedFileContent) || isProcessing) return;
    
    let finalMessage = msg;
    let imagePreview = null;
    if (uploadedFileContent) {
        const fileContext = `[已上传简历文件: ${uploadedFileName}]\n\n简历内容:\n${uploadedFileContent}`;
        finalMessage = msg ? `${msg}\n\n${fileContext}` : `请帮我优化这份简历\n\n${fileContext}`;
        imagePreview = uploadedFilePreview; // 保存图片预览
        removeFile();
    }
    
    chatInput.value = '';
    chatInput.style.height = '32px'; // 重置输入框高度
    
    document.getElementById('welcomeMessage')?.remove();
    addMessage(finalMessage, true, null, null, 0, imagePreview);
    
    setProcessingState(true);
    currentStreamedText = '';
    
    // 显示浮动任务状态栏
    showTaskStatusBar('任务正在后台执行中...');
    
    // 清空右侧侧边栏推理步骤面板的旧内容
    const stepsPanel = document.getElementById('executionStepsPanel');
    if (stepsPanel) {
        stepsPanel.innerHTML = '<p style="font-size: 0.8125rem; color: var(--text-tertiary);">正在分析...</p>';
    }
    
    const load = document.createElement('div');
    load.className = 'message message-agent';
    load.id = 'loading';
    load.innerHTML = '<div class="message-avatar">AI</div><div class="message-bubble">' +
        '<div class="message-content" id="loadingContent">' +
            '<div class="progress-indicator">' +
                '<div class="loading-dots"><span></span><span></span><span></span></div>' +
                '<span class="progress-text" id="progressText">正在思考...</span>' +
            '</div>' +
        '</div>' +
    '</div>';
    chatMessages.appendChild(load);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    activeLoadingBubble = load;
    
    currentAbortController = new AbortController();
    
    try {
        await streamAgentChat(finalMessage, agentType.value, lastUsedAgent, currentAbortController.signal);
    } catch (e) {
        if (e.name === 'AbortError') {
            console.log('Stream fetch aborted');
            return;
        }
        const errorEl = activeLoadingBubble || document.getElementById('loading');
        if (errorEl) {
            let errorMsg = e.message;
            if (errorMsg.includes('timeout') || errorMsg.includes('超时')) {
                errorMsg = '处理超时，请稍后重试。如果问题持续存在，可以尝试简化您的问题。';
            } else if (errorMsg.includes('network') || errorMsg.includes('网络')) {
                errorMsg = '网络连接出现问题，请检查网络后重试。';
            } else {
                errorMsg = '处理过程中遇到问题，请稍后重试。';
            }
            errorEl.querySelector('.message-content').innerHTML = `<span style="color: var(--error);">${errorMsg}</span>`;
            errorEl.removeAttribute('id');
        }
    } finally {
        setProcessingState(false);
    }
}

// SSE流式响应
async function streamAgentChat(message, agentType, lastAgent, signal) {
    const response = await fetch('/api/agent/chat/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ 
            message: message, 
            agent_type: agentType, 
            conversation_id: currentConversationId,
            last_agent: lastAgent
        }),
        signal: signal
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalResult = null;
    let allSteps = [];
    let shouldBreak = false;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split('\n');
        buffer = lines.pop();
        
        let eventType = null;
        for (const line of lines) {
            if (line.startsWith('event: ')) {
                eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
                const data = line.slice(6);
                try {
                    const parsed = JSON.parse(data);
                    handleSSEEvent(eventType, parsed, allSteps);
                    
                    if (eventType === 'done') {
                        finalResult = parsed;
                        shouldBreak = true;
                    } else if (eventType === 'error') {
                        throw new Error(parsed.error || '执行失败');
                    }
                } catch (e) {
                    if (eventType === 'error') throw e;
                    console.error('解析SSE数据失败:', e);
                }
                eventType = null;
            }
        }
        if (shouldBreak) break;
    }

    if (finalResult) {
        await handleTaskCompleted(finalResult, message);
    }
}

function handleSSEEvent(eventType, data, allSteps) {
    switch (eventType) {
        case 'start':
            currentTaskId = data.task_id;
            // 保存任务ID到localStorage，用于断线恢复
            saveTaskToStorage(data.task_id, data.conversation_id);
            if (currentConversationId !== data.conversation_id) {
                currentConversationId = data.conversation_id;
                try {
                    const url = new URL(window.location.href);
                    url.searchParams.set('id', currentConversationId);
                    window.history.replaceState(null, '', url.pathname + url.search);
                } catch (e) {
                    console.error('Failed to update URL search params:', e);
                }
            }
            break;
            
        case 'progress':
            const progressEl = activeLoadingBubble ? activeLoadingBubble.querySelector('#progressText') : document.getElementById('progressText');
            if (progressEl) progressEl.textContent = data.message;
            break;
            
        case 'step':
            const existingIndex = allSteps.findIndex(s => 
                s.type === data.type && s.title === data.title
            );
            
            if (existingIndex >= 0) {
                allSteps[existingIndex] = data;
            } else {
                allSteps.push(data);
            }
            
            // 更新加载文字为当前步骤
            const progressText = activeLoadingBubble ? activeLoadingBubble.querySelector('#progressText') : document.getElementById('progressText');
            if (progressText && data.title) {
                progressText.textContent = data.title + '...';
            }
            
            // 更新右侧推理面板
            updateExecutionSteps(allSteps);
            
            break;
            
        case 'content':
            appendStreamContent(data.content);
            break;
            
        case 'done':
            break;
            
        case 'error':
            throw new Error(data.error || '执行失败');
    }
}

// 智能自动滚动到最下方（如果用户手动向上滚动查看历史，则停止强制拉到底部）
function smartScrollToBottom() {
    if (!chatMessages) return;
    const threshold = 150; // 判定距离底部的阈值
    const isAtBottom = (chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight) <= threshold;
    if (isAtBottom) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// 追加流式文本内容
function appendStreamContent(token) {
    const loadingContent = activeLoadingBubble ? activeLoadingBubble.querySelector('.message-content') : document.getElementById('loadingContent');
    if (!loadingContent) return;
    
    // 如果是第一次接收到token，清除进度指示器并加上流式光标样式
    const indicator = loadingContent.querySelector('.progress-indicator');
    if (indicator) {
        loadingContent.innerHTML = '';
        currentStreamedText = '';
        loadingContent.classList.add('streaming-active');
    }
    
    currentStreamedText += token;
    
    // 检测是否包含简历内容，如果是则分离文字和HTML
    const isResume = detectResumeContent(currentStreamedText, '');
    if (isResume) {
        const resumeOnly = extractResumeContent(currentStreamedText);
        if (resumeOnly) {
            const displayContent = currentStreamedText.split('<!--RESUME_START-->')[0].trim() || '已为您生成简历';
            loadingContent.innerHTML = formatMessageContent(displayContent);
        } else {
            // 简历内容还在生成中，只显示文字部分
            const parts = currentStreamedText.split('<!--RESUME_START-->');
            if (parts.length > 1) {
                loadingContent.innerHTML = formatMessageContent(parts[0].trim() || '正在生成简历...');
            } else {
                loadingContent.innerHTML = formatMessageContent(currentStreamedText);
            }
        }
    } else {
        loadingContent.innerHTML = formatMessageContent(currentStreamedText);
    }
    
    // 自动流动滚动
    smartScrollToBottom();
}

// 任务完成处理
async function handleTaskCompleted(result, originalMessage) {
    const doneEl = activeLoadingBubble || document.getElementById('loading');
    if (!doneEl) return;
    
    setProcessingState(false);
    doneEl.removeAttribute('id');
    
    // 清除localStorage中的任务状态
    clearTaskFromStorage();
    
    // 隐藏浮动任务状态栏
    hideTaskStatusBar();
    
    const executionSteps = result.steps || result.execution_steps || [];
    const intermediateSteps = result.intermediate_steps || [];
    const agentUsed = result.agent_used || '';
    
    if (agentUsed) {
        lastUsedAgent = agentUsed.split(',')[0].trim();
    }
    
    const allSteps = [...executionSteps, ...intermediateSteps];
    
    updateExecutionSteps(executionSteps);
    
    // 使用result.output或currentStreamedText（流式输出的内容）
    const fullContent = result.output || currentStreamedText || '';
    const isResume = detectResumeContent(fullContent, agentUsed);
    
    if (isResume) {
        const resumeOnly = extractResumeContent(fullContent);
        if (resumeOnly) {
            const displayContent = fullContent.split('<!--RESUME_START-->')[0].trim() || '已为您生成简历';
            const contentId = 'resume-content-' + Date.now();
            window[contentId] = resumeOnly;
            doneEl.querySelector('.message-content').innerHTML = formatMessageContent(displayContent) + buildResumePreviewCard(contentId);
            setTimeout(() => showResumeInPanel(contentId), 500);
        } else {
            doneEl.querySelector('.message-content').innerHTML = formatMessageContent(fullContent);
        }
    } else {
        doneEl.querySelector('.message-content').innerHTML = formatMessageContent(fullContent);
    }
    
    const existingItem = document.getElementById('history-' + currentConversationId);
    if (!existingItem && currentConversationId) {
        const title = originalMessage ? originalMessage.substring(0, 30) : '对话';
        addConversationToList(currentConversationId, title);
        document.getElementById('chatTitle').textContent = title;
    }
}

function askQuestion(q) { chatInput.value = q; sendMessage(); }

function addConversationToList(id, firstMsg) {
    const list = document.querySelector('.chat-history-list');
    if (!list) return;
    
    document.querySelectorAll('.chat-history-item.active').forEach(item => {
        item.classList.remove('active');
    });
    
    const div = document.createElement('div');
    div.className = 'chat-history-item active';
    div.id = 'history-' + id;
    const safeTitle = escapeHtml(firstMsg.substring(0, 20));
    const safeId = escapeHtml(id);
    div.innerHTML = `
        <a href="/chat?id=${safeId}" class="chat-history-link">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
            <span class="chat-history-title">${safeTitle}...</span>
        </a>
        <button class="chat-history-delete" onclick="deleteConversation('${safeId}', event)" title="删除">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
        </button>`;
    list.insertBefore(div, list.firstChild);
}

async function deleteConversation(id, e) {
    e.stopPropagation();
    e.preventDefault();
    
    const confirmed = await modal.confirm('确定要删除这条对话吗？');
    if (!confirmed) return;
    
    try {
        const res = await fetch('/api/history/' + id, { method: 'DELETE' });
        const data = await res.json();
        if (data.code === 200) {
            const el = document.getElementById('history-' + id);
            if (el) {
                el.style.opacity = '0';
                el.style.transform = 'translateX(-20px)';
                setTimeout(() => el.remove(), 300);
            }
            if (currentConversationId === id) {
                currentConversationId = '';
                location.reload();
            }
            modal.toast('已删除', 'success');
        }
    } catch (e) {
        modal.toast('删除失败', 'error');
    }
}

// ===== Mobile Plus Menu =====
function toggleMobileMenu() {
    const menu = document.getElementById('mobilePlusMenu');
    const btn = document.getElementById('mobilePlusBtn');
    if (!menu || !btn) return;

    const isOpen = menu.classList.contains('show');
    if (isOpen) {
        closeMobileMenu();
    } else {
        menu.classList.add('show');
        btn.classList.add('active');
    }
}

function closeMobileMenu() {
    const menu = document.getElementById('mobilePlusMenu');
    const btn = document.getElementById('mobilePlusBtn');
    if (menu) menu.classList.remove('show');
    if (btn) btn.classList.remove('active');
}

function showMobileAgentSelector() {
    // Create a simple agent selector modal for mobile
    const agentOptions = [
        { value: 'auto', name: '自动选择', color: '#666' },
        { value: 'career', name: '职业规划', color: '#3b82f6' },
        { value: 'skill', name: '技能分析', color: '#8b5cf6' },
        { value: 'side_job', name: '副业分析', color: '#10b981' },
        { value: 'resume', name: '简历优化', color: '#f59e0b' },
        { value: 'interview', name: '面试教练', color: '#ec4899' }
    ];

    const currentAgent = document.getElementById('agentType')?.value || 'auto';

    let html = '<div class="mobile-agent-modal" onclick="this.remove()">';
    html += '<div class="mobile-agent-sheet" onclick="event.stopPropagation()">';
    html += '<div class="mobile-agent-header">选择智能体</div>';
    html += '<div class="mobile-agent-list">';

    agentOptions.forEach(opt => {
        const isSelected = opt.value === currentAgent;
        html += `<button class="mobile-agent-option ${isSelected ? 'selected' : ''}" 
                    onclick="selectAgent('${opt.value}', '${opt.name}', event); this.closest('.mobile-agent-modal').remove();">
            <span class="mobile-agent-dot" style="background: ${opt.color};"></span>
            <span>${opt.name}</span>
            ${isSelected ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M20 6L9 17l-5-5"/></svg>' : ''}
        </button>`;
    });

    html += '</div></div></div>';

    document.body.insertAdjacentHTML('beforeend', html);
}

// Close mobile menu when clicking outside
document.addEventListener('click', function(e) {
    const menu = document.getElementById('mobilePlusMenu');
    const btn = document.getElementById('mobilePlusBtn');
    if (menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) {
        closeMobileMenu();
    }
});

// ===== Mobile Sidebar Toggle =====
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const hamburger = document.getElementById('hamburgerBtn');

    if (!sidebar || !overlay) return;

    const isActive = sidebar.classList.contains('active');

    if (isActive) {
        // Close sidebar
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        if (hamburger) hamburger.classList.remove('active');
        document.body.style.overflow = '';
    } else {
        // Open sidebar
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

    // Close sidebar on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar && sidebar.classList.contains('active')) {
                toggleSidebar();
            }
        }
    });

    // Handle swipe to close
    let touchStartX = 0;
    let touchEndX = 0;
    const sidebar = document.querySelector('.sidebar');

    if (sidebar) {
        sidebar.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });

        sidebar.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            const swipeDistance = touchStartX - touchEndX;

            // Swipe left to close
            if (swipeDistance > 50 && sidebar.classList.contains('active')) {
                toggleSidebar();
            }
        }, { passive: true });
    }

    // 监听窗口大小变化以动态调整简历缩放
    window.addEventListener('resize', () => {
        if (document.getElementById('resumeModal').style.display === 'flex') {
            adjustResumeScale();
        }
    });
});

// ==================== 任务持久化和恢复 ====================

/**
 * 保存任务信息到localStorage
 */
function saveTaskToStorage(taskId, conversationId) {
    try {
        const taskData = {
            taskId: taskId,
            conversationId: conversationId,
            timestamp: Date.now()
        };
        localStorage.setItem(TASK_STORAGE_KEY, JSON.stringify(taskData));
        console.log('[TaskPersistence] 任务已保存到localStorage:', taskId);
    } catch (e) {
        console.error('[TaskPersistence] 保存任务失败:', e);
    }
}

/**
 * 从localStorage清除任务信息
 */
function clearTaskFromStorage() {
    try {
        localStorage.removeItem(TASK_STORAGE_KEY);
        console.log('[TaskPersistence] 任务已从localStorage清除');
    } catch (e) {
        console.error('[TaskPersistence] 清除任务失败:', e);
    }
}

/**
 * 从localStorage获取任务信息
 */
function getTaskFromStorage() {
    try {
        const data = localStorage.getItem(TASK_STORAGE_KEY);
        if (data) {
            return JSON.parse(data);
        }
    } catch (e) {
        console.error('[TaskPersistence] 读取任务失败:', e);
    }
    return null;
}

/**
 * 初始化任务持久化机制
 */
function initTaskPersistence() {
    // 检查是否有未完成的任务
    checkAndRestoreTask();
    
    // 监听页面可见性变化
    document.addEventListener('visibilitychange', handleVisibilityChange);
}

/**
 * 检查并恢复未完成的任务
 */
async function checkAndRestoreTask() {
    const savedTask = getTaskFromStorage();
    if (!savedTask) return;
    
    const { taskId, conversationId } = savedTask;
    
    // 如果当前正在处理中，不恢复
    if (isProcessing) return;
    
    // 如果没有对话ID，直接清除
    if (!conversationId) {
        clearTaskFromStorage();
        return;
    }
    
    console.log('[TaskPersistence] 发现任务，加载对话:', taskId);
    
    // 清除任务存储
    clearTaskFromStorage();
    
    // 更新URL并加载对话历史
    currentConversationId = conversationId;
    try {
        const url = new URL(window.location.href);
        url.searchParams.set('id', currentConversationId);
        window.history.replaceState(null, '', url.pathname + url.search);
    } catch (e) {}
    await loadConversation(currentConversationId);
}

/**
 * 显示任务错误
 */
function showTaskError(errorMsg) {
    const errorEl = activeLoadingBubble || document.getElementById('loading');
    if (errorEl) {
        if (errorMsg.includes('timeout') || errorMsg.includes('超时')) {
            errorMsg = '处理超时，请稍后重试。';
        } else if (errorMsg.includes('network') || errorMsg.includes('网络')) {
            errorMsg = '网络连接出现问题，请检查网络后重试。';
        }
        errorEl.querySelector('.message-content').innerHTML = `<span style="color: var(--error);">${escapeHtml(errorMsg)}</span>`;
        errorEl.removeAttribute('id');
    }
}

/**
 * 处理页面可见性变化
 */
function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
        console.log('[TaskPersistence] 页面变为可见，检查任务状态');
        // 页面变为可见时，检查是否有未完成的任务
        if (!isProcessing) {
            checkAndRestoreTask();
        }
    }
}

// ==================== 浮动任务状态栏 ====================

/**
 * 显示浮动任务状态栏
 * @param {string} text - 状态文本
 * @param {boolean} isCompleted - 是否已完成
 */
function showTaskStatusBar(text, isCompleted = false) {
    const statusBar = document.getElementById('taskStatusBar');
    if (!statusBar) return;
    
    const textEl = statusBar.querySelector('.task-status-text');
    const btnEl = statusBar.querySelector('.task-status-btn');
    const iconEl = statusBar.querySelector('.task-status-icon');
    
    if (textEl) textEl.textContent = text;
    
    if (isCompleted) {
        statusBar.classList.add('completed');
        if (btnEl) btnEl.textContent = '查看结果';
        // 移除旋转动画，显示完成图标
        if (iconEl) {
            iconEl.innerHTML = '<div class="task-status-spinner"></div>';
        }
    } else {
        statusBar.classList.remove('completed');
        if (btnEl) btnEl.textContent = '返回对话';
        // 显示旋转动画
        if (iconEl) {
            iconEl.innerHTML = '<div class="task-status-spinner"></div>';
        }
    }
    
    statusBar.style.display = 'block';
    taskStatusBarVisible = true;
}

/**
 * 隐藏浮动任务状态栏
 */
function hideTaskStatusBar() {
    const statusBar = document.getElementById('taskStatusBar');
    if (statusBar) {
        statusBar.style.display = 'none';
        statusBar.classList.remove('completed');
    }
    taskStatusBarVisible = false;
}

/**
 * 处理浮动状态栏点击事件
 */
function handleTaskStatusBarClick() {
    const savedTask = getTaskFromStorage();
    
    // 如果有保存的任务，加载对应的对话
    if (savedTask && savedTask.conversationId) {
        const conversationId = savedTask.conversationId;
        clearTaskFromStorage();
        
        // 更新URL并加载对话
        currentConversationId = conversationId;
        try {
            const url = new URL(window.location.href);
            url.searchParams.set('id', currentConversationId);
            window.history.replaceState(null, '', url.pathname + url.search);
        } catch (e) {}
        
        loadConversation(currentConversationId);
    }
    
    // 隐藏状态栏
    hideTaskStatusBar();
}

/**
 * 更新浮动状态栏为任务完成状态
 */
function updateStatusBarToCompleted() {
    const statusBar = document.getElementById('taskStatusBar');
    if (statusBar && taskStatusBarVisible) {
        showTaskStatusBar('任务已完成', true);
    }
}

// ==================== 图片预览模态框 ====================

/**
 * 显示图片大图模态框
 */
function showImageModal(imageSrc) {
    // 移除已有的模态框
    const existingModal = document.getElementById('imagePreviewModal');
    if (existingModal) existingModal.remove();
    
    const modal = document.createElement('div');
    modal.id = 'imagePreviewModal';
    modal.className = 'image-preview-modal';
    modal.onclick = function() { this.remove(); };
    modal.innerHTML = `
        <div class="image-preview-content">
            <img src="${imageSrc}" alt="图片预览" />
            <button class="image-preview-close" onclick="this.closest('.image-preview-modal').remove()">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
        </div>
    `;
    document.body.appendChild(modal);
}
