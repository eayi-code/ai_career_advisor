/**
 * 自定义弹窗组件
 */

class Modal {
    constructor() {
        this.createModal();
    }

    createModal() {
        const modalHTML = `
            <div id="customModal" class="modal-overlay" style="display: none;">
                <div class="modal-container">
                    <div class="modal-header">
                        <h3 id="modalTitle"></h3>
                        <button class="modal-close" onclick="modal.hide()">&times;</button>
                    </div>
                    <div class="modal-body" id="modalBody"></div>
                    <div class="modal-footer" id="modalFooter"></div>
                </div>
            </div>
            <div id="confirmToast" style="
                display: none;
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) scale(0.9);
                z-index: 10001;
                background: white;
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.2);
                min-width: 300px;
                max-width: 400px;
                text-align: center;
                opacity: 0;
                transition: all 0.2s ease;
            ">
                <div id="confirmIcon" style="margin-bottom: 12px;"></div>
                <p id="confirmMessage" style="font-size: 15px; color: #1d1d1f; margin-bottom: 20px; line-height: 1.5;"></p>
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button id="confirmCancelBtn" style="
                        padding: 8px 20px;
                        background: #f5f5f7;
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        cursor: pointer;
                        color: #1d1d1f;
                    ">取消</button>
                    <button id="confirmOkBtn" style="
                        padding: 8px 20px;
                        background: #0066cc;
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        cursor: pointer;
                        color: white;
                    ">确认</button>
                </div>
            </div>
            <div id="confirmOverlay" style="
                display: none;
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.3);
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.2s ease;
            "></div>
            <div id="toastContainer" class="toast-container"></div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    show({ title, content, type = 'alert', onConfirm, onCancel }) {
        const modal = document.getElementById('customModal');
        const titleEl = document.getElementById('modalTitle');
        const bodyEl = document.getElementById('modalBody');
        const footerEl = document.getElementById('modalFooter');

        titleEl.textContent = title;
        bodyEl.innerHTML = `<p>${content}</p>`;

        let buttons = '';
        if (type === 'confirm') {
            buttons = `
                <button class="btn btn-secondary" onclick="modal.hide(); modal._onCancel()">取消</button>
                <button class="btn btn-primary" onclick="modal.hide(); modal._onConfirm()">确认</button>
            `;
        } else {
            buttons = `<button class="btn btn-primary" onclick="modal.hide()">确定</button>`;
        }
        footerEl.innerHTML = buttons;

        this._onConfirm = onConfirm || (() => {});
        this._onCancel = onCancel || (() => {});

        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('active'), 10);
    }

    hide() {
        const modal = document.getElementById('customModal');
        modal.classList.remove('active');
        setTimeout(() => modal.style.display = 'none', 200);
    }

    alert(title, content) {
        return new Promise(resolve => {
            this.show({
                title,
                content,
                type: 'alert',
                onConfirm: resolve
            });
        });
    }

    confirm(message) {
        return new Promise(resolve => {
            const overlay = document.getElementById('confirmOverlay');
            const toast = document.getElementById('confirmToast');
            const msgEl = document.getElementById('confirmMessage');
            const okBtn = document.getElementById('confirmOkBtn');
            const cancelBtn = document.getElementById('confirmCancelBtn');

            msgEl.textContent = message;
            overlay.style.display = 'block';
            toast.style.display = 'block';

            setTimeout(() => {
                overlay.style.opacity = '1';
                toast.style.opacity = '1';
                toast.style.transform = 'translate(-50%, -50%) scale(1)';
            }, 10);

            const cleanup = () => {
                overlay.style.opacity = '0';
                toast.style.opacity = '0';
                toast.style.transform = 'translate(-50%, -50%) scale(0.9)';
                setTimeout(() => {
                    overlay.style.display = 'none';
                    toast.style.display = 'none';
                }, 200);
            };

            okBtn.onclick = () => {
                cleanup();
                resolve(true);
            };

            cancelBtn.onclick = () => {
                cleanup();
                resolve(false);
            };

            overlay.onclick = () => {
                cleanup();
                resolve(false);
            };
        });
    }

    toast(message, type = 'success', duration = 3000) {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
            <span class="toast-message">${message}</span>
        `;
        container.appendChild(toast);

        setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

const modal = new Modal();
