import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# 修复 SSL 证书路径：系统级 SSL_CERT_FILE 可能指向不存在的文件（
# 例如 Windows 上 miniconda 遗留路径），导致 langchain_openai/httpx 创建
# SSL 上下文时报 FileNotFoundError，AI 调用全部失败。
# 自动检测：若系统变量指向的文件不存在，用 certifi 提供的正确证书覆盖，
# 跨平台兼容（Windows/Linux/Mac），不影响 Docker 部署。
_ssl_cert = os.environ.get('SSL_CERT_FILE', '')
if _ssl_cert and not os.path.isfile(_ssl_cert):
    try:
        import certifi
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ.setdefault('REQUESTS_CA_BUNDLE', certifi.where())
    except ImportError:
        pass


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:password@localhost/career_advisor')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 数据库连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20,
    }

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

    VISION_API_KEY = os.getenv('VISION_API_KEY') or os.getenv('OPENAI_API_KEY')
    VISION_BASE_URL = os.getenv('VISION_BASE_URL') or os.getenv('OPENAI_BASE_URL')
    VISION_MODEL = os.getenv('VISION_MODEL') or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

    CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', './chroma_data')
    
    # 安全配置
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # 业务配置
    MAX_MESSAGE_LENGTH = 10000  # 最大消息长度
    
    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5分钟
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')
