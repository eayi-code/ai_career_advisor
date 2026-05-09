from datetime import datetime
from app import db


class AnalysisHistory(db.Model):
    __tablename__ = 'analysis_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    conversation_id = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), default='新对话')
    analysis_type = db.Column(db.String(50), nullable=False)
    agent_used = db.Column(db.String(50), nullable=False)
    input_data = db.Column(db.JSON)
    result_data = db.Column(db.JSON)
    reasoning_steps = db.Column(db.JSON)
    tools_used = db.Column(db.JSON)
    messages = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
