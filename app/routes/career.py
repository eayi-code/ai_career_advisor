from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.profile import UserProfile
from app.models.history import AnalysisHistory

career_bp = Blueprint('career', __name__)


@career_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    histories = AnalysisHistory.query.filter_by(user_id=current_user.id).order_by(
        AnalysisHistory.updated_at.desc()
    ).limit(10).all()
    
    if request.method == 'POST':
        if not current_user.profile:
            profile = UserProfile(user_id=current_user.id)
            db.session.add(profile)
        else:
            profile = current_user.profile

        profile.education = request.form.get('education', 'bachelor')
        profile.major = request.form.get('major')
        profile.work_experience = int(request.form.get('work_experience', 0))
        profile.current_job_title = request.form.get('current_job_title')
        profile.target_industry = request.form.get('target_industry')
        profile.location_preference = request.form.get('location_preference')
        profile.career_goals = request.form.get('career_goals')

        skills = request.form.get('skills', '')
        profile.skills = [s.strip() for s in skills.split(',') if s.strip()]

        interests = request.form.get('interests', '')
        profile.interests = [s.strip() for s in interests.split(',') if s.strip()]

        db.session.commit()
        flash('档案已更新', 'success')
        return redirect(url_for('career.profile'))

    return render_template('career/profile.html', histories=histories)


@career_bp.route('/chat')
@login_required
def chat():
    conversation_id = request.args.get('id')
    histories = AnalysisHistory.query.filter_by(user_id=current_user.id).order_by(
        AnalysisHistory.updated_at.desc()
    ).all()
    return render_template('career/chat.html', conversation_id=conversation_id, histories=histories)
