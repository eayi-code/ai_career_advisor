// CareerAI Service Worker
// 版本号
const CACHE_VERSION = 'v1.0.0';
const CACHE_NAME = `careerai-${CACHE_VERSION}`;

// 需要缓存的资源
const STATIC_ASSETS = [
    '/',
    '/static/css/base.css',
    '/static/css/components.css',
    '/static/css/chat.css',
    '/static/css/profile.css',
    '/static/css/resume.css',
    '/static/css/modal.css',
    '/static/js/main.js',
    '/static/js/modal.js',
    '/static/js/chat.js',
    '/static/js/profile.js',
    '/static/manifest.json'
];

// 安装事件 - 预缓存静态资源
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Pre-caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[Service Worker] Installation complete');
                return self.skipWaiting();
            })
    );
});

// 激活事件 - 清理旧缓存
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...');
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => name !== CACHE_NAME)
                        .map((name) => {
                            console.log(`[Service Worker] Deleting old cache: ${name}`);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[Service Worker] Activation complete');
                return self.clients.claim();
            })
    );
});

// 获取事件 - 网络优先策略
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // 跳过非GET请求
    if (request.method !== 'GET') {
        return;
    }

    // 跳过API请求（需要实时数据）
    if (url.pathname.startsWith('/api/')) {
        return;
    }

    // 跳过SSE流式请求
    if (url.pathname.includes('/stream')) {
        return;
    }

    // 网络优先策略
    event.respondWith(
        fetch(request)
            .then((response) => {
                // 如果响应成功，缓存并返回
                if (response && response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME)
                        .then((cache) => {
                            cache.put(request, responseClone);
                        });
                }
                return response;
            })
            .catch(() => {
                // 网络失败，尝试从缓存获取
                return caches.match(request)
                    .then((cachedResponse) => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        // 如果是页面请求，返回离线页面
                        if (request.headers.get('accept').includes('text/html')) {
                            return caches.match('/');
                        }
                        return new Response('Network error', { status: 503 });
                    });
            })
    );
});

// 推送通知事件（可选）
self.addEventListener('push', (event) => {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/icon-72x72.png',
            vibrate: [100, 50, 100],
            data: {
                url: data.url || '/'
            }
        };
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

// 通知点击事件
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});
