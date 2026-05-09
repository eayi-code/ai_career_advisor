from datetime import datetime
from app import db


class SkillCategory(db.Model):
    __tablename__ = 'skill_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200))


class Skill(db.Model):
    __tablename__ = 'skills'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey('skill_categories.id'))
    description = db.Column(db.Text)
    difficulty_level = db.Column(db.Integer, default=3)
    market_demand = db.Column(db.String(20))
    learning_months = db.Column(db.Integer)

    category = db.relationship('SkillCategory', backref='skills')
    resources = db.relationship('LearningResource', backref='skill', lazy='dynamic', cascade='all, delete-orphan')


class LearningResource(db.Model):
    __tablename__ = 'learning_resources'

    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20))
    url = db.Column(db.String(500))
    description = db.Column(db.Text)
    difficulty = db.Column(db.String(20))
    duration = db.Column(db.String(50))
