from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.ratelimit import limiter, RATE_LIMITS
import re

auth_bp = Blueprint('auth', __name__)


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

        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('邮箱已注册', 'danger')
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
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('career.chat'))

        flash('用户名或密码错误', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('auth.index'))
