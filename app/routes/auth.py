from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.ratelimit import limiter, RATE_LIMITS
import re
import time

auth_bp = Blueprint('auth', __name__)

# 登录失败锁定配置
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 分钟（秒）


def _get_login_attempts(username):
    """获取当前用户名的登录失败次数和最后失败时间"""
    attempts = session.get('login_attempts', {})
    return attempts.get(username, {'count': 0, 'last_attempt': 0})


def _record_login_failure(username):
    """记录一次登录失败"""
    attempts = session.get('login_attempts', {})
    entry = attempts.get(username, {'count': 0, 'last_attempt': 0})
    entry['count'] = entry['count'] + 1
    entry['last_attempt'] = time.time()
    attempts[username] = entry
    session['login_attempts'] = attempts


def _clear_login_attempts(username):
    """清除指定用户名的登录失败记录"""
    attempts = session.get('login_attempts', {})
    attempts.pop(username, None)
    session['login_attempts'] = attempts


def _is_locked_out(username):
    """检查指定用户名是否处于锁定状态"""
    entry = _get_login_attempts(username)
    if entry['count'] >= MAX_LOGIN_ATTEMPTS:
        elapsed = time.time() - entry['last_attempt']
        if elapsed < LOCKOUT_DURATION:
            return True, int(LOCKOUT_DURATION - elapsed)
        else:
            # 锁定时间已过，自动清除
            _clear_login_attempts(username)
    return False, 0


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('career.chat'))
    return render_template('index.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit(RATE_LIMITS["auth_register"], methods=['POST'])
def register():
    if current_user.is_authenticated:
        if getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('career.chat'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # 输入验证
        if not username or len(username) < 3 or len(username) > 50:
            flash('用户名长度需要在3-50个字符之间', 'danger')
            return render_template('auth/register.html')

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash('用户名只能包含字母、数字和下划线', 'danger')
            return render_template('auth/register.html')

        if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('请输入有效的邮箱地址', 'danger')
            return render_template('auth/register.html')

        if not password or len(password) < 6:
            flash('密码长度至少6个字符', 'danger')
            return render_template('auth/register.html')

        # 统一错误消息，防止用户名/邮箱枚举
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash('该用户名或邮箱已被注册', 'danger')
            return render_template('auth/register.html')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit(RATE_LIMITS["auth_login"], methods=['POST'])
def login():
    if current_user.is_authenticated:
        if getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('career.chat'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # 检查账号锁定
        locked, remaining = _is_locked_out(username)
        if locked:
            flash(f'登录失败次数过多，请在 {remaining} 秒后重试', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # 登录成功，清除失败记录
            _clear_login_attempts(username)
            login_user(user)
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('career.chat'))

        # 登录失败，记录并统一错误消息
        _record_login_failure(username)
        entry = _get_login_attempts(username)
        remaining_attempts = MAX_LOGIN_ATTEMPTS - entry['count']

        if remaining_attempts > 0:
            flash(f'用户名或密码错误（还剩 {remaining_attempts} 次机会）', 'danger')
        else:
            flash(f'登录失败次数过多，账号已锁定 {LOCKOUT_DURATION // 60} 分钟', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('auth.index'))
