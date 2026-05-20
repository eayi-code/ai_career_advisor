from datetime import datetime
from app import db


class UserProfile(db.Model):
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 基本信息
    education = db.Column(db.String(20), nullable=False, default='bachelor')
    major = db.Column(db.String(100))
    skills = db.Column(db.JSON, default=list)
    work_experience = db.Column(db.Integer, default=0)
    current_job_title = db.Column(db.String(100))
    
    # 求职意向
    target_job_title = db.Column(db.String(100))  # 当前选中的目标岗位
    target_jobs = db.Column(db.JSON, default=list)  # 所有目标岗位列表
    target_industry = db.Column(db.String(100))
    target_salary_min = db.Column(db.Float)
    target_salary_max = db.Column(db.Float)
    location_preference = db.Column(db.String(100))
    job_search_status = db.Column(db.String(20), default='observing')  # observing/employed/resigned/fresh
    work_preference = db.Column(db.String(20), default='flexible')  # remote/onsite/hybrid/flexible
    expected_join_time = db.Column(db.String(20), default='flexible')  # flexible/1month/3months/negotiable
    company_type_preference = db.Column(db.String(50))  # startup/big_company/foreign/flexible
    
    # 项目经历 (JSON数组)
    projects = db.Column(db.JSON, default=list)  # [{"name": "", "role": "", "tech_stack": "", "achievement": ""}]
    
    # 证书资质 (JSON数组)
    certifications = db.Column(db.JSON, default=list)  # ["证书1", "证书2"]
    
    # 副业信息
    available_hours_per_week = db.Column(db.Integer)  # 每周可用小时数
    side_job_income_target = db.Column(db.Float)  # 副业月收入目标
    
    # 其他
    interests = db.Column(db.JSON, default=list)
    career_goals = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
