from datetime import datetime
from app import db


class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    industry = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    responsibilities = db.Column(db.JSON)
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    salary_avg = db.Column(db.Integer)
    experience_years = db.Column(db.Integer, default=0)
    education_requirement = db.Column(db.String(20))
    city = db.Column(db.String(50))
    is_hot = db.Column(db.Boolean, default=False)
    growth_potential = db.Column(db.String(20))
    difficulty_level = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    skills = db.relationship('JobSkill', backref='job', lazy='dynamic', cascade='all, delete-orphan')


class JobSkill(db.Model):
    __tablename__ = 'job_skills'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    skill_name = db.Column(db.String(50), nullable=False)
    importance = db.Column(db.String(10), default='required')
