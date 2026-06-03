"""
用户服务模块
处理用户管理相关的业务逻辑
"""

import os
import base64
from sqlalchemy import func

from app import db
from app.models.user import User
from app.models.history import AnalysisHistory


class UserService:
    """用户服务类"""
    
    @staticmethod
    def update_username(user, new_username):
        """更新用户名"""
        if not new_username:
            return {"success": False, "error": "用户名不能为空"}
        
        if len(new_username) < 2 or len(new_username) > 50:
            return {"success": False, "error": "用户名长度需在2-50个字符之间"}
        
        existing = User.query.filter(
            User.username == new_username, 
            User.id != user.id
        ).first()
        if existing:
            return {"success": False, "error": "用户名已被占用"}
        
        try:
            user.username = new_username
            db.session.commit()
            return {"success": True, "message": "用户名修改成功"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_password(user, old_password, new_password):
        """更新密码"""
        if not old_password or not new_password:
            return {"success": False, "error": "请填写完整"}
        
        if not user.check_password(old_password):
            return {"success": False, "error": "当前密码错误"}
        
        if len(new_password) < 6:
            return {"success": False, "error": "新密码长度至少6位"}
        
        try:
            user.set_password(new_password)
            db.session.commit()
            return {"success": True, "message": "密码修改成功"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_avatar(user, avatar_data):
        """更新头像"""
        if not avatar_data:
            return {"success": False, "error": "请选择头像"}
        
        try:
            if avatar_data.startswith('data:image'):
                header, encoded = avatar_data.split(',', 1)
                image_data = base64.b64decode(encoded)
                
                upload_dir = os.path.join('app', 'static', 'uploads', 'avatars')
                os.makedirs(upload_dir, exist_ok=True)
                
                filename = f"avatar_{user.id}.png"
                filepath = os.path.join(upload_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(image_data)
                
                user.avatar = f"/static/uploads/avatars/{filename}"
                db.session.commit()
                
                return {
                    "success": True, 
                    "message": "头像更新成功", 
                    "avatar_url": user.avatar
                }
            
            return {"success": False, "error": "无效的图片数据"}
            
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_user_stats(user_id):
        """获取用户统计信息"""
        try:
            total_conversations = AnalysisHistory.query.filter_by(user_id=user_id).count()
            
            total_messages = 0
            histories = AnalysisHistory.query.filter_by(user_id=user_id).all()
            for h in histories:
                if h.messages:
                    total_messages += len(h.messages)
            
            agent_stats = db.session.query(
                AnalysisHistory.agent_used,
                func.count(AnalysisHistory.id)
            ).filter_by(user_id=user_id).group_by(
                AnalysisHistory.agent_used
            ).all()
            
            agent_usage = {agent: count for agent, count in agent_stats}
            
            recent_days = db.session.query(
                func.date(AnalysisHistory.created_at).label('date'),
                func.count(AnalysisHistory.id).label('count')
            ).filter_by(user_id=user_id).group_by(
                func.date(AnalysisHistory.created_at)
            ).order_by(
                func.date(AnalysisHistory.created_at).desc()
            ).limit(7).all()
            
            daily_activity = [{"date": str(date), "count": count} for date, count in recent_days]
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "agent_usage": agent_usage,
                "daily_activity": daily_activity
            }
        except Exception as e:
            raise e
