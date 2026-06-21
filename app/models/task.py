from datetime import datetime
from app import db


class AgentTask(db.Model):
    """智能体任务状态表，用于任务持久化和断线恢复"""
    __tablename__ = 'agent_tasks'
    __table_args__ = (
        db.Index('idx_task_user', 'user_id', 'status'),
        db.Index('idx_task_conversation', 'conversation_id'),
        db.Index('idx_task_status', 'status', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    conversation_id = db.Column(db.String(50), nullable=False, index=True)
    
    # 任务输入
    message = db.Column(db.Text, nullable=False)
    agent_type = db.Column(db.String(50))  # 强制指定的agent类型
    last_agent = db.Column(db.String(50))  # 上次使用的agent
    
    # 任务状态
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, running, completed, failed, aborted
    progress = db.Column(db.JSON, default=list)  # 推理步骤列表
    result = db.Column(db.JSON)  # 最终结果
    error = db.Column(db.Text)  # 错误信息
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # 关联用户
    user = db.relationship('User', backref=db.backref('tasks', lazy='dynamic'))

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'conversation_id': self.conversation_id,
            'message': self.message,
            'agent_type': self.agent_type,
            'status': self.status,
            'progress': self.progress or [],
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def get_active_task(cls, user_id, conversation_id=None):
        """获取用户当前活跃的任务"""
        query = cls.query.filter(
            cls.user_id == user_id,
            cls.status.in_(['pending', 'running'])
        )
        if conversation_id:
            query = query.filter(cls.conversation_id == conversation_id)
        return query.order_by(cls.created_at.desc()).first()

    @classmethod
    def get_pending_tasks(cls, user_id):
        """获取用户所有待处理和进行中的任务"""
        return cls.query.filter(
            cls.user_id == user_id,
            cls.status.in_(['pending', 'running'])
        ).order_by(cls.created_at.desc()).all()
