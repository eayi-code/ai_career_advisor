// chat.js - 聊天页面主要逻辑

// 全局变量
let currentConversationId = '';
let autoMessage = '';
let currentAbortController = null;
let isProcessing = false;
let uploadedFileContent = null;
let uploadedFileName = null;
let currentResumeContent = null;
let currentZoomLevel = 1;
let lastUsedAgent = null;
let currentStreamedText = '';
let activeLoadingBubble = null;
let currentTaskId = null;
let isNewConversation = false;

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
function initChatPage(conversationId, autoMsg) {
    currentConversationId = conversationId;
    isNewConversation = !currentConversationId;
    autoMessage = autoMsg;
    
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendBtn = document.getElementById('sendBtn');
    fileInput = document.getElementById('fileInput');
    filePreview = document.getElementById('filePreview');
    
    if (currentConversationId) {
        loadConversation(currentConversationId);
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
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const isImage = ['.png', '.jpg', '.jpeg', '.webp', '.bmp'].includes(ext);
        modal.toast(isImage ? '正在使用AI智能识别截图岗位信息...' : '正在解析文件...', 'info');
        const res = await fetch('/api/upload/resume', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        
        if (data.code === 200) {
            uploadedFileContent = data.data.content;
            uploadedFileName = data.data.filename;
            document.getElementById('fileName').textContent = uploadedFileName;
            filePreview.style.display = 'block';
            chatInput.placeholder = '输入优化要求，或直接发送以解析简历...';
            modal.toast('文件解析成功', 'success');
        } else {
            modal.toast(data.error || '文件解析失败', 'error');
            fileInput.value = '';
        }
    } catch (err) {
        modal.toast('文件上传失败', 'error');
        fileInput.value = '';
    }
}

function removeFile() {
    uploadedFileContent = null;
    uploadedFileName = null;
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
                const toolsUsed = [...new Set(reasonSteps.filter(s => s.action).map(s => s.action))];
                
                updateExecutionSteps(execSteps);
                updateReasoning(reasonSteps);
                updateTools(toolsUsed);
            } else {
                // 清空为默认占位符
                document.getElementById('executionStepsPanel').innerHTML = '<p style="font-size: 0.8125rem; color: var(--text-tertiary);">发送消息后展示</p>';
                document.getElementById('reasoningPanel').innerHTML = '<p style="font-size: 0.8125rem; color: var(--text-tertiary);">发送消息后展示</p>';
                document.getElementById('toolsPanel').innerHTML = '<p style="font-size: 0.8125rem; color: var(--text-tertiary);">工具调用信息</p>';
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
        
        const liveReasoning = loadingEl.querySelector('.reasoning-timeline');
        if (liveReasoning) {
            const runningDots = liveReasoning.querySelector('.loading-dots');
            if (runningDots) runningDots.remove();
            const liveProgress = liveReasoning.querySelector('#liveProgress');
            if (liveProgress) liveProgress.textContent = '已停止生成';
        }
        
        // 移除ID防篡改，并使消息内容显示正常
        loadingEl.removeAttribute('id');
    }
    
    setProcessingState(false);
}

// 添加消息
function addMessage(content, isUser, agent, steps, index = 0) {
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
    
    if (isResume) {
        const resumeOnly = extractResumeContent(content);
        if (resumeOnly) {
            displayContent = content.split('<!--RESUME_START-->')[0].trim() || '已为您生成简历';
            const contentId = 'resume-content-' + Date.now();
            window[contentId] = resumeOnly;
            previewCard = buildResumePreviewCard(contentId);
            showCopyBtn = '';
        }
    }
    
    let reasoningContainer = '';
    if (!isUser && steps && steps.length > 0) {
        reasoningContainer = buildReasoningTimeline(steps);
    }
    
    div.innerHTML = '<div class="message-avatar">' + (isUser ? '我' : 'AI') + '</div>' +
        '<div class="message-bubble">' +
            reasoningContainer +
            '<div class="message-content">' + formatMessageContent(displayContent) + '</div>' +
            previewCard +
            showCopyBtn +
        '</div>';
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    if (steps?.length) updateReasoning(steps);
    
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
    if (content.includes('<div') && content.includes('class=') && content.length > 500) return true;
    
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
    currentZoomLevel = 1;
    
    const isHTML = content.includes('<!DOCTYPE html>') || content.includes('<html') || content.includes('tailwindcss');
    const previewContainer = document.getElementById('resumePreviewContent');
    
    if (isHTML) {
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        iframe.style.background = 'white';
        iframe.style.display = 'block';
        
        previewContainer.innerHTML = '';
        previewContainer.appendChild(iframe);
        iframe.srcdoc = content;
    } else {
        previewContainer.innerHTML = renderResumeContent(content);
    }
    
    document.getElementById('zoomLevel').textContent = '100%';
    previewContainer.style.transform = 'scale(1)';
    
    document.getElementById('resumeModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeResumeModal() {
    document.getElementById('resumeModal').style.display = 'none';
    document.body.style.overflow = '';
    currentResumeContent = null;
    currentZoomLevel = 1;
}

function zoomResume(delta) {
    currentZoomLevel = Math.max(0.5, Math.min(2, currentZoomLevel + delta));
    const previewContainer = document.getElementById('resumePreviewContent');
    previewContainer.style.transform = `scale(${currentZoomLevel})`;
    document.getElementById('zoomLevel').textContent = Math.round(currentZoomLevel * 100) + '%';
}

// 下载功能
async function downloadResumeAsImage() {
    if (!currentResumeContent) return;
    
    try {
        const previewContainer = document.getElementById('resumePreviewContent');
        const iframe = previewContainer.querySelector('iframe');
        
        if (iframe) {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            const canvas = await html2canvas(iframeDoc.body, {
                scale: 2,
                useCORS: true,
                logging: false
            });
            
            const link = document.createElement('a');
            link.download = 'resume.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
        } else {
            const canvas = await html2canvas(previewContainer, {
                scale: 2,
                useCORS: true,
                logging: false
            });
            
            const link = document.createElement('a');
            link.download = 'resume.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
        }
        
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
        
        if (existingIframe && existingIframe.contentDocument && existingIframe.contentDocument.body) {
            const iframeDoc = existingIframe.contentDocument;
            if (iframeDoc.body.innerHTML.trim()) {
                canvas = await html2canvas(iframeDoc.body, {
                    scale: 2,
                    useCORS: true,
                    logging: true,
                    backgroundColor: '#ffffff',
                    allowTaint: true,
                    useOverflow: true,
                    scrollX: 0,
                    scrollY: 0
                });
            }
        }
        
        if (!canvas) {
            const tempContainer = document.createElement('div');
            tempContainer.id = 'temp-pdf-container';
            tempContainer.style.position = 'fixed';
            tempContainer.style.left = '0';
            tempContainer.style.top = '0';
            tempContainer.style.width = '794px';
            tempContainer.style.height = 'auto';
            tempContainer.style.background = 'white';
            tempContainer.style.zIndex = '99999';
            tempContainer.style.opacity = '0.01';
            document.body.appendChild(tempContainer);
            
            const isHTML = content.includes('<!DOCTYPE html>') || content.includes('<html') || content.includes('tailwindcss');
            
            if (isHTML) {
                tempContainer.innerHTML = content;
            } else {
                tempContainer.innerHTML = renderResumeContent(content);
                tempContainer.style.fontFamily = "'Microsoft YaHei', 'SimSun', Arial, sans-serif";
                tempContainer.style.padding = '40px';
            }
            
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            canvas = await html2canvas(tempContainer, {
                scale: 2,
                useCORS: true,
                logging: true,
                backgroundColor: '#ffffff',
                allowTaint: true
            });
            
            document.body.removeChild(tempContainer);
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

async function downloadFromPanel(format = 'html') {
    if (!currentResumeContent) return;
    
    if (format === 'pdf') {
        await downloadResumeAsPDF(currentResumeContent);
        return;
    }
    
    try {
        const res = await fetch('/api/download/resume', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ content: currentResumeContent, filename: 'resume', format: format })
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

async function downloadResume(contentId, format = 'html') {
    const content = window[contentId];
    if (!content) return;
    
    if (format === 'pdf') {
        await downloadResumeAsPDF(content);
        return;
    }
    
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
        const stepTitle = step.title || step.action || '处理中';
        const stepDetail = step.detail || step.output || '';
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

function updateReasoning(steps) {
    const panel = document.getElementById('reasoningPanel');
    if (!panel) return; // 如果面板不存在，直接返回
    if (!steps || steps.length === 0) {
        panel.innerHTML = '<p style="font-size: 0.8125rem; color: var(--text-tertiary);">无推理步骤</p>';
        return;
    }
    panel.innerHTML = steps.map(s => 
        '<div class="step-item"><div class="step-action">' + s.action + '</div>' +
        '<div class="step-output">' + (s.output?.substring(0, 80) || '') + '</div></div>'
    ).join('');
}

function updateTools(tools) {
    document.getElementById('toolsPanel').innerHTML = tools?.length ? 
        tools.map(t => '<span class="tool-badge">' + t + '</span>').join('') :
        '<p style="font-size: 0.8125rem; color: var(--text-tertiary);">未使用</p>';
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
                const dependsText = st.depends_on && st.depends_on.length > 0 ? ` (依赖: ${st.depends_on.join(', ')})` : '';
                const subtaskIcon = getAgentIcon(st.agent);
                const subtaskColor = getAgentColor(st.agent);
                subtasksHtml += `<div class="subtask-item">
                    <span class="subtask-agent" style="color: ${subtaskColor}; display: inline-flex; align-items: center; gap: 4px;">
                        ${subtaskIcon || ''}
                        ${getAgentName(st.agent)}
                    </span>
                    <span class="subtask-task">${st.task}</span>
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
                ${getAgentName(step.agent)}
            </span>`;
        }
        
        html += `
            <div class="execution-step">
                <div class="execution-step-icon ${typeClass} ${statusClass}">
                    ${icon}
                </div>
                <div class="execution-step-content">
                    <div class="execution-step-title">${step.title}</div>
                    <div class="execution-step-detail">${step.detail}</div>
                    ${step.user_intent_summary ? `<div class="execution-step-intent">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
                        ${step.user_intent_summary}
                    </div>` : ''}
                    ${step.reasoning ? `<div class="execution-step-reasoning">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
                        ${step.reasoning}
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

// 点击外部关闭下拉菜单
document.addEventListener('click', function(e) {
    const selector = document.getElementById('agentSelector');
    if (selector && !selector.contains(e.target)) {
        const dropdown = document.getElementById('agentDropdown');
        const btn = document.getElementById('agentSelectorBtn');
        if (dropdown) dropdown.classList.remove('show');
        if (btn) btn.classList.remove('active');
    }
});

// 发送消息
async function sendMessage() {
    const msg = chatInput.value.trim();
    if ((!msg && !uploadedFileContent) || isProcessing) return;
    
    let finalMessage = msg;
    if (uploadedFileContent) {
        const fileContext = `[已上传简历文件: ${uploadedFileName}]\n\n简历内容:\n${uploadedFileContent}`;
        finalMessage = msg ? `${msg}\n\n${fileContext}` : `请帮我优化这份简历\n\n${fileContext}`;
        removeFile();
    }
    
    chatInput.value = '';
    chatInput.style.height = '32px'; // 重置输入框高度
    
    document.getElementById('welcomeMessage')?.remove();
    addMessage(finalMessage, true);
    
    setProcessingState(true);
    currentStreamedText = '';
    
    // 清空右侧侧边栏推理步骤面板的旧内容
    const stepsPanel = document.getElementById('executionStepsPanel');
    if (stepsPanel) {
        stepsPanel.innerHTML = '<p style="font-size: 0.8125rem; color: var(--text-tertiary);">正在分析...</p>';
    }
    
    const load = document.createElement('div');
    load.className = 'message message-agent';
    load.id = 'loading';
    load.innerHTML = '<div class="message-avatar">AI</div><div class="message-bubble">' +
        '<div class="reasoning-timeline" id="liveReasoning">' +
            '<div class="reasoning-header" onclick="toggleReasoningTimeline(this)">' +
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6"/><path d="M9 16h6"/></svg>' +
                '<span id="liveProgress">正在分析您的问题...</span>' +
                '<svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" style="margin-left: auto; transition: transform 0.4s;"><path d="M6 9l6 6 6-6"/></svg>' +
            '</div>' +
            '<div class="reasoning-body" id="liveStepsBody"></div>' +
        '</div>' +
        '<div class="message-content" id="loadingContent">' +
            '<div class="progress-indicator">' +
                '<div class="loading-dots"><span></span><span></span><span></span></div>' +
                '<span class="progress-text">正在分析您的问题...</span>' +
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
            const progressEl = activeLoadingBubble ? activeLoadingBubble.querySelector('#liveProgress') : document.getElementById('liveProgress');
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
            
            updateLiveSteps(allSteps);
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
    
    // 如果是第一次接收到token，清除进度指示器并加上流式光标样式，并优雅折叠时间线
    const indicator = loadingContent.querySelector('.progress-indicator');
    if (indicator) {
        loadingContent.innerHTML = '';
        currentStreamedText = '';
        loadingContent.classList.add('streaming-active');
        
        // 自动折叠推理时间线，使用手风琴收起效果
        const liveReasoning = activeLoadingBubble ? activeLoadingBubble.querySelector('.reasoning-timeline') : document.getElementById('liveReasoning');
        if (liveReasoning) {
            liveReasoning.classList.add('collapsed');
            const liveProgress = liveReasoning.querySelector('#liveProgress');
            if (liveProgress) {
                liveProgress.textContent = '思考完毕，已开始回答';
            }
        }
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

function updateLiveSteps(steps) {
    const body = activeLoadingBubble ? activeLoadingBubble.querySelector('#liveStepsBody') : document.getElementById('liveStepsBody');
    if (!body) return;
    
    const iconMap = {
        'intent_analysis': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
        'agent_call': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M12 2a4 4 0 014 4v2a4 4 0 01-8 0V6a4 4 0 014-4z"/><path d="M6 10v8a6 6 0 0012 0v-8"/></svg>',
        'task_split': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M12 22v-8.3a4 4 0 00-1.172-2.872L3 3"/><path d="m15 9 6-6"/></svg>',
        'quality_check': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>',
        'result_merge': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>',
        'tool': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>'
    };
    
    const typeClassMap = {
        'intent_analysis': 'intent',
        'agent_call': 'agent',
        'task_split': 'split',
        'quality_check': 'check',
        'result_merge': 'merge',
        'tool': 'tool'
    };
    
    let html = '';
    steps.forEach((step, index) => {
        const stepType = step.type || (step.action ? 'tool' : 'intent_analysis');
        const stepTitle = step.title || step.action || '处理中';
        const stepDetail = step.detail || step.output || '';
        const stepStatus = step.status || 'completed';
        
        const icon = iconMap[stepType] || iconMap['tool'];
        const typeClass = typeClassMap[stepType] || 'intent';
        const statusClass = stepStatus === 'running' ? 'running' : '';
        
        html += '<div class="timeline-step" style="animation: fadeInUp 0.3s ease-out;">';
        if (index < steps.length - 1) {
            html += '<div class="timeline-line"></div>';
        }
        html += `<div class="timeline-dot ${typeClass} ${statusClass}">${icon}</div>`;
        html += '<div class="timeline-content">';
        html += `<div class="timeline-title">${stepTitle}</div>`;
        
        if (stepDetail) {
            const truncated = stepDetail.length > 100 ? stepDetail.substring(0, 100) + '...' : stepDetail;
            html += `<div class="timeline-detail">${truncated}</div>`;
        }
        
        html += '</div></div>';
    });
    
    body.innerHTML = html;
    smartScrollToBottom();
}

// 任务完成处理
async function handleTaskCompleted(result, originalMessage) {
    const doneEl = activeLoadingBubble || document.getElementById('loading');
    if (!doneEl) return;
    
    setProcessingState(false);
    doneEl.removeAttribute('id');
    
    const executionSteps = result.steps || result.execution_steps || [];
    const intermediateSteps = result.intermediate_steps || [];
    const agentUsed = result.agent_used || '';
    
    if (agentUsed) {
        lastUsedAgent = agentUsed.split(',')[0].trim();
    }
    
    const allSteps = [...executionSteps, ...intermediateSteps];
    
    updateExecutionSteps(executionSteps);
    updateReasoning(intermediateSteps);
    const toolsUsed = [...new Set(intermediateSteps.filter(s => s.action).map(s => s.action))];
    updateTools(toolsUsed);
    
    const liveReasoning = document.getElementById('liveReasoning');
    if (liveReasoning && allSteps.length > 0) {
        const finalTimeline = buildReasoningTimeline(allSteps);
        liveReasoning.outerHTML = finalTimeline;
    } else if (liveReasoning) {
        liveReasoning.remove();
    }
    
    const fullContent = result.output || '';
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
    div.innerHTML = `
        <a href="/chat?id=${id}" class="chat-history-link">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
            <span class="chat-history-title">${firstMsg.substring(0, 20)}...</span>
        </a>
        <button class="chat-history-delete" onclick="deleteConversation('${id}', event)" title="删除">
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
