import pytest
from app import create_app, db
from app.models.user import User
from app.models.history import AnalysisHistory
from app.models.task import AgentTask


@pytest.fixture
def app():
    """配置测试应用实例并初始化内存 SQLite 数据库"""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {},
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """测试客户端"""
    return app.test_client()


@pytest.fixture
def seed_users(app):
    """播种用于测试的默认用户和分析历史数据"""
    with app.app_context():
        # 1. 正常普通用户
        user = User(
            username="normal_user", 
            email="normal@career.ai", 
            is_admin=False, 
            is_active=True
        )
        user.set_password("password123")
        db.session.add(user)
        
        # 2. 管理员用户
        admin = User(
            username="admin_user", 
            email="admin@career.ai", 
            is_admin=True, 
            is_active=True
        )
        admin.set_password("password123")
        db.session.add(admin)
        
        # 3. 禁用拉黑用户
        inactive = User(
            username="inactive_user", 
            email="inactive@career.ai", 
            is_admin=False, 
            is_active=False
        )
        inactive.set_password("password123")
        db.session.add(inactive)
        
        db.session.commit()
        
        # 4. 新增一条分析历史
        history = AnalysisHistory(
            user_id=user.id,
            conversation_id="conv-123",
            title="测试职业分析",
            analysis_type="career",
            agent_used="career_planner"
        )
        db.session.add(history)
        db.session.commit()
        
        return {
            "normal_id": user.id,
            "admin_id": admin.id,
            "inactive_id": inactive.id
        }


def test_unauthenticated_access(client):
    """测试未登录用户被正确阻止访问"""
    # 尝试访问管理员后台页面 -> 应该 302 重定向至登录页面
    response = client.get('/admin/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']
    
    # 尝试访问 API -> 应该重定向（login_required 控制）
    response = client.get('/admin/api/stats')
    assert response.status_code == 302


def test_normal_user_access(client, seed_users):
    """测试普通用户访问管理员后台被拦截 (403)"""
    # 1. 登录普通用户
    login_response = client.post('/login', data={
        "username": "normal_user",
        "password": "password123"
    })
    assert login_response.status_code == 302
    assert '/chat' in login_response.headers['Location']
    
    # 2. 强行访问管理员后台页面 -> 应该返回 403 Forbidden
    response = client.get('/admin/dashboard')
    assert response.status_code == 403
    
    # 3. 强行访问统计 API -> 应该返回 403 错误信息
    response = client.get('/admin/api/stats')
    assert response.status_code == 403
    data = response.get_json()
    assert data['error'] == 'Forbidden'
    assert '需要管理员权限' in data['message']


def test_admin_user_access(client, seed_users):
    """测试管理员登录分流及统计 API 数据聚合"""
    # 1. 登录管理员账号
    login_response = client.post('/login', data={
        "username": "admin_user",
        "password": "password123"
    })
    assert login_response.status_code == 302
    # 应该被分流重定向到管理员后台
    assert '/admin/dashboard' in login_response.headers['Location']
    
    # 2. 访问管理员后台页面 -> 应返回 200 OK
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    
    # 3. 请求看板数据 API -> 验证数据结构和数量
    response = client.get('/admin/api/stats')
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['success'] is True
    assert data['kpis']['total_users'] == 3
    assert data['kpis']['total_analyses'] == 1
    assert len(data['recent_users']) == 3
    assert data['recent_users'][0]['username'] == 'inactive_user'  # 最晚注册排最前
    assert data['recent_analyses'][0]['username'] == 'normal_user'


def test_user_management_apis(client, seed_users):
    """测试用户状态管理接口与防管理员自锁死保护"""
    # 1. 以管理员身份登录
    client.post('/login', data={
        "username": "admin_user",
        "password": "password123"
    })
    
    normal_id = seed_users['normal_id']
    admin_id = seed_users['admin_id']
    
    # 2. 禁用普通用户
    response = client.post(f'/admin/api/users/{normal_id}/toggle_status')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['is_active'] is False  # 状态应变为 False
    
    # 3. 尝试禁用管理员自身 -> 应当失败并返回 400 Bad Request
    response = client.post(f'/admin/api/users/{admin_id}/toggle_status')
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert '不能停用您自己的管理员账号' in data['message']
    
    # 4. 提升普通用户为管理员
    response = client.post(f'/admin/api/users/{normal_id}/toggle_admin')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['is_admin'] is True
    
    # 5. 尝试取消管理员自身的管理员身份 -> 应当被防御并返回 400
    response = client.post(f'/admin/api/users/{admin_id}/toggle_admin')
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert '不能取消您自己的管理员身份' in data['message']
