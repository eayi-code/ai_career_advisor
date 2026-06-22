from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cache = Cache()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    migrate.init_app(app, db)
    cache.init_app(app)

    # CSRF 全局保护
    csrf.init_app(app)

    # 配置日志
    from app.logging_config import setup_logging
    setup_logging(app)

    # 配置限流
    from app.ratelimit import limiter
    limiter.init_app(app)

    # 安全响应头（每个请求自动附加）
    @app.after_request
    def set_security_headers(response):
        for header, value in app.config.get('SECURITY_HEADERS', {}).items():
            response.headers.setdefault(header, value)
        return response

    from app.routes.auth import auth_bp
    from app.routes.career import career_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp

    # API 端点豁免 CSRF（使用 @login_required + 限流保护）
    csrf.exempt(api_bp)

    app.register_blueprint(auth_bp)
    app.register_blueprint(career_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp)

    return app
