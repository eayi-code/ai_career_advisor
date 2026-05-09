from datetime import datetime
from app import db


class SideJob(db.Model):
    __tablename__ = 'side_jobs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    income_min = db.Column(db.Integer)
    income_max = db.Column(db.Integer)
    hours_per_week = db.Column(db.Integer)
    startup_cost = db.Column(db.Integer, default=0)
    difficulty_level = db.Column(db.Integer, default=3)
    platforms = db.Column(db.JSON)
    skills_required = db.Column(db.JSON)
    getting_started = db.Column(db.JSON)
    pros = db.Column(db.JSON)
    cons = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
