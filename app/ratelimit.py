"""API限流配置"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 创建限流器实例
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://"
)

# 限流规则配置
RATE_LIMITS = {
    # 认证相关 - 严格限流
    "auth_login": "5 per minute",
    "auth_register": "3 per minute",
    
    # 对话相关 - 中等限流
    "chat_send": "20 per minute",
    "chat_stream": "20 per minute",
    
    # 文件上传 - 严格限流
    "file_upload": "10 per minute",
    
    # 普通API - 宽松限流
    "api_default": "60 per minute",
    
    # 任务状态轮询 - 宽松限流（允许频繁轮询）
    "task_status": "120 per minute",
    
    # 历史记录 - 宽松限流
    "history_list": "30 per minute",
    "history_get": "60 per minute",

    # 管理端 - 中等限流
    "admin_api": "60 per minute",
}
