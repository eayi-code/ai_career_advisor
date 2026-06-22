from flask import Blueprint, render_template, jsonify, abort, request, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.history import AnalysisHistory
from app.models.task import AgentTask
from app.ratelimit import limiter, RATE_LIMITS
from functools import wraps
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """
    管理员权限验证装饰器。
    若非管理员访问：
    - API 请求（以 /admin/api/ 开头）返回 403 JSON 响应。
    - 页面请求返回 403 页面错误。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            if request.path.startswith('/admin/api/'):
                return jsonify({
                    'error': 'Forbidden',
                    'message': '需要管理员权限，您无权访问此接口。'
                }), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """渲染管理员控制台主页"""
    return render_template('dashboard/dashboard.html')


@admin_bp.route('/api/stats')
@login_required
@admin_required
@limiter.limit(RATE_LIMITS["admin_api"])
def get_stats():
    """获取看板数据和用户列表统计信息"""
    try:
        # 1. KPI 核心指标统计
        total_users = User.query.count()
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        users_today = User.query.filter(User.created_at >= today_start).count()

        total_analyses = AnalysisHistory.query.count()
        analyses_today = AnalysisHistory.query.filter(AnalysisHistory.created_at >= today_start).count()

        active_tasks = AgentTask.query.filter(AgentTask.status.in_(['pending', 'running'])).count()
        failed_tasks = AgentTask.query.filter(AgentTask.status == 'failed').count()

        # 2. 7日趋势数据统计（双折线图）
        dates = []
        user_growth = []
        analysis_volume = []

        for i in range(6, -1, -1):
            day_date = datetime.utcnow().date() - timedelta(days=i)
            day_start = datetime.combine(day_date, datetime.min.time())
            day_end = datetime.combine(day_date, datetime.max.time())

            dates.append(day_date.strftime('%m-%d'))

            u_count = User.query.filter(
                User.created_at >= day_start,
                User.created_at <= day_end
            ).count()
            user_growth.append(u_count)

            a_count = AnalysisHistory.query.filter(
                AnalysisHistory.created_at >= day_start,
                AnalysisHistory.created_at <= day_end
            ).count()
            analysis_volume.append(a_count)

        # 3. 智能体分配占比统计（环形图）
        agent_counts = db.session.query(
            AnalysisHistory.agent_used,
            db.func.count(AnalysisHistory.id)
        ).group_by(AnalysisHistory.agent_used).all()

        agent_mapping = {
            'career_planner': '职业规划顾问',
            'resume_advisor': '简历修改顾问',
            'side_job_advisor': '副业分析师',
            'skill_advisor': '技能分析师'
        }

        agent_distribution = {}
        for agent, count in agent_counts:
            if not agent:
                continue
            friendly_name = agent_mapping.get(agent, agent)
            agent_distribution[friendly_name] = agent_distribution.get(friendly_name, 0) + count

        # 4. 最近活跃用户列表
        recent_users_query = User.query.order_by(User.created_at.desc(), User.id.desc()).limit(15).all()
        recent_users = []
        for u in recent_users_query:
            recent_users.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'created_at': u.created_at.strftime('%Y-%m-%d %H:%M:%S') if u.created_at else '',
                'is_active': u.is_active,
                'is_admin': u.is_admin
            })

        # 5. 最近分析日志列表
        recent_analyses_query = db.session.query(
            AnalysisHistory.id,
            AnalysisHistory.title,
            AnalysisHistory.agent_used,
            AnalysisHistory.analysis_type,
            AnalysisHistory.created_at,
            User.username
        ).join(
            User,
            AnalysisHistory.user_id == User.id
        ).order_by(AnalysisHistory.created_at.desc(), AnalysisHistory.id.desc()).limit(15).all()

        recent_analyses = []
        for a in recent_analyses_query:
            friendly_agent = agent_mapping.get(a.agent_used, a.agent_used)
            recent_analyses.append({
                'id': a.id,
                'title': a.title,
                'agent_used': friendly_agent,
                'analysis_type': a.analysis_type,
                'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S') if a.created_at else '',
                'username': a.username
            })

        return jsonify({
            'success': True,
            'kpis': {
                'total_users': total_users,
                'users_today': users_today,
                'total_analyses': total_analyses,
                'analyses_today': analyses_today,
                'active_tasks': active_tasks,
                'failed_tasks': failed_tasks
            },
            'trends': {
                'labels': dates,
                'user_growth': user_growth,
                'analysis_volume': analysis_volume
            },
            'agent_distribution': agent_distribution,
            'recent_users': recent_users,
            'recent_analyses': recent_analyses
        })
    except Exception as e:
        # 生产环境不暴露内部错误详情
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': '服务器内部错误，请稍后重试'
        }), 500


@admin_bp.route('/api/users/<int:user_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
@limiter.limit(RATE_LIMITS["admin_api"])
def toggle_user_status(user_id):
    """启用或拉黑特定用户账号"""
    user = User.query.get_or_404(user_id)

    # 安全保护：管理员无法禁用自身账号，防锁死
    if user.id == current_user.id:
        return jsonify({
            'success': False,
            'message': '操作失败：不能停用您自己的管理员账号！'
        }), 400

    user.is_active = not user.is_active
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"用户 {user.username} 已成功{'启用' if user.is_active else '禁用拉黑'}。",
        'is_active': user.is_active
    })


@admin_bp.route('/api/users/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
@limiter.limit(RATE_LIMITS["admin_api"])
def toggle_user_admin(user_id):
    """提升用户为管理员或降级为普通用户"""
    user = User.query.get_or_404(user_id)

    # 安全保护：管理员无法降级自身，防锁死
    if user.id == current_user.id:
        return jsonify({
            'success': False,
            'message': '操作失败：不能取消您自己的管理员身份！'
        }), 400

    user.is_admin = not user.is_admin
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"已将用户 {user.username} {'设置为管理员' if user.is_admin else '降级为普通用户'}。",
        'is_admin': user.is_admin
    })
