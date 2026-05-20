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

        # 基本信息
        profile.education = request.form.get('education', 'bachelor')
        profile.major = request.form.get('major')
        profile.work_experience = int(request.form.get('work_experience', 0))
        profile.current_job_title = request.form.get('current_job_title')
        
        skills = request.form.get('skills', '')
        profile.skills = [s.strip() for s in skills.split(',') if s.strip()]
        
        # 求职意向
        profile.target_job_title = request.form.get('target_job_title')
        profile.target_industry = request.form.get('target_industry')
        profile.location_preference = request.form.get('location_preference')
        profile.job_search_status = request.form.get('job_search_status', 'observing')
        profile.work_preference = request.form.get('work_preference', 'flexible')
        profile.expected_join_time = request.form.get('expected_join_time', 'flexible')
        profile.company_type_preference = request.form.get('company_type_preference', 'flexible')
        
        # 目标薪资
        target_salary_min = request.form.get('target_salary_min')
        target_salary_max = request.form.get('target_salary_max')
        if target_salary_min:
            profile.target_salary_min = float(target_salary_min)
        else:
            profile.target_salary_min = None
        if target_salary_max:
            profile.target_salary_max = float(target_salary_max)
        else:
            profile.target_salary_max = None
        
        # 目标岗位列表
        target_job_title = request.form.get('target_job_title')
        if target_job_title:
            from datetime import datetime
            target_jobs = profile.target_jobs or []
            existing_titles = [j.get("title") for j in target_jobs]
            if target_job_title not in existing_titles:
                target_jobs.append({
                    "title": target_job_title,
                    "added_at": datetime.utcnow().isoformat()
                })
                profile.target_jobs = target_jobs
        
        # 项目经历
        project_names = request.form.getlist('project_name[]')
        project_roles = request.form.getlist('project_role[]')
        project_techs = request.form.getlist('project_tech[]')
        project_achievements = request.form.getlist('project_achievement[]')
        
        projects = []
        for i in range(len(project_names)):
            if project_names[i].strip():  # 只保存有名称的项目
                projects.append({
                    "name": project_names[i],
                    "role": project_roles[i] if i < len(project_roles) else "",
                    "tech_stack": project_techs[i] if i < len(project_techs) else "",
                    "achievement": project_achievements[i] if i < len(project_achievements) else ""
                })
        profile.projects = projects
        
        # 证书资质
        certifications = request.form.get('certifications', '')
        profile.certifications = [s.strip() for s in certifications.split(',') if s.strip()]
        
        # 副业信息
        available_hours = request.form.get('available_hours_per_week')
        income_target = request.form.get('side_job_income_target')
        profile.available_hours_per_week = int(available_hours) if available_hours else None
        profile.side_job_income_target = float(income_target) if income_target else None
        
        # 职业目标
        profile.career_goals = request.form.get('career_goals')

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
