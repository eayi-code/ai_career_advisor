from datetime import datetime
from app import db


class Job(db.Model):
    __tablename__ = 'jobs'
    __table_args__ = (
        db.Index('idx_title_industry', 'title', 'industry'),
        db.Index('idx_city_salary', 'city', 'salary_avg'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, index=True)
    industry = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text)
    responsibilities = db.Column(db.JSON)
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    salary_avg = db.Column(db.Integer)
    experience_years = db.Column(db.Integer, default=0)
    education_requirement = db.Column(db.String(20))
    city = db.Column(db.String(50), index=True)
    is_hot = db.Column(db.Boolean, default=False)
    growth_potential = db.Column(db.String(20))
    difficulty_level = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    skills = db.relationship('JobSkill', backref='job', lazy='dynamic', cascade='all, delete-orphan')


class JobSkill(db.Model):
    __tablename__ = 'job_skills'
    __table_args__ = (
        db.Index('idx_job_skill', 'job_id', 'skill_name'),
    )

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False, index=True)
    skill_name = db.Column(db.String(50), nullable=False, index=True)
    importance = db.Column(db.String(10), default='required')
