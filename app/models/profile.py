from datetime import datetime
from app import db


class UserProfile(db.Model):
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    education = db.Column(db.String(20), nullable=False, default='bachelor')
    major = db.Column(db.String(100))
    skills = db.Column(db.JSON, default=list)
    work_experience = db.Column(db.Integer, default=0)
    current_job_title = db.Column(db.String(100))
    target_industry = db.Column(db.String(100))
    target_salary_min = db.Column(db.Float)
    target_salary_max = db.Column(db.Float)
    location_preference = db.Column(db.String(100))
    interests = db.Column(db.JSON, default=list)
    career_goals = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
