"""
历史记录服务模块
处理对话历史相关的业务逻辑
"""

from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm.attributes import flag_modified

from app import db
from app.models.history import AnalysisHistory


class HistoryService:
    """历史记录服务类"""
    
    @staticmethod
    def get_conversation(conversation_id, user_id):
        """获取对话详情"""
        history = AnalysisHistory.query.filter_by(
            conversation_id=conversation_id,
            user_id=user_id
        ).order_by(AnalysisHistory.updated_at.desc()).first()
        
        if not history:
            return None
        
        return {
            "conversation_id": history.conversation_id,
            "title": history.title,
            "agent_used": history.agent_used,
            "messages": history.messages or [],
            "created_at": history.created_at.isoformat(),
            "updated_at": history.updated_at.isoformat() if history.updated_at else None
        }
    
    @staticmethod
    def get_history_list(user_id, limit=50):
        """获取历史记录列表"""
        # 先获取每个conversation_id的最大updated_at
        subquery = db.session.query(
            AnalysisHistory.conversation_id,
            func.max(AnalysisHistory.updated_at).label('max_updated')
        ).filter_by(user_id=user_id).group_by(
            AnalysisHistory.conversation_id
        ).subquery()
        
        # 获取完整的记录
        histories = db.session.query(AnalysisHistory).join(
            subquery,
            db.and_(
                AnalysisHistory.conversation_id == subquery.c.conversation_id,
                AnalysisHistory.updated_at == subquery.c.max_updated
            )
        ).filter(
            AnalysisHistory.user_id == user_id
        ).order_by(
            AnalysisHistory.updated_at.desc()
        ).limit(limit).all()
        
        return [{
            "conversation_id": h.conversation_id,
            "title": h.title,
            "agent_used": h.agent_used,
            "message_count": len(h.messages) if h.messages else 0,
            "last_message": h.messages[-1]["content"][:50] if h.messages else "",
            "created_at": h.created_at.isoformat(),
            "updated_at": h.updated_at.isoformat() if h.updated_at else None
        } for h in histories]
    
    @staticmethod
    def delete_conversation(conversation_id, user_id):
        """删除对话"""
        try:
            count = AnalysisHistory.query.filter_by(
                conversation_id=conversation_id,
                user_id=user_id
            ).delete()
            db.session.commit()
            return count
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def save_conversation(conversation_id, user_id, message, result, agent_type='auto'):
        """保存对话记录"""
        try:
            history = AnalysisHistory.query.filter_by(
                conversation_id=conversation_id,
                user_id=user_id
            ).first()
            
            if not history:
                title = message[:30] + ('...' if len(message) > 30 else '')
                history = AnalysisHistory(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    title=title,
                    analysis_type=agent_type,
                    agent_used=result.get("agent_used", "unknown"),
                    input_data={"message": message},
                    result_data={"output": result.get("output", "")},
                    reasoning_steps=result.get("intermediate_steps", []),
                    tools_used=[s.get("action", "") for s in result.get("intermediate_steps", [])],
                    messages=[]
                )
                db.session.add(history)
            else:
                history.input_data = {"message": message}
                history.result_data = {"output": result.get("output", "")}
                history.reasoning_steps = result.get("intermediate_steps", [])
                existing_tools = history.tools_used or []
                new_tools = [s.get("action", "") for s in result.get("intermediate_steps", [])]
                history.tools_used = list(set(existing_tools + new_tools))
                history.agent_used = result.get("agent_used", history.agent_used)
            
            messages = history.messages or []
            messages.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            })
            messages.append({
                "role": "assistant",
                "content": result.get("output", ""),
                "agent": result.get("agent_used"),
                "steps": result.get("intermediate_steps", []),
                "execution_steps": result.get("steps", []),
                "timestamp": datetime.utcnow().isoformat()
            })
            history.messages = messages
            history.updated_at = datetime.utcnow()
            
            # 标记JSON字段为已修改
            flag_modified(history, 'messages')
            flag_modified(history, 'tools_used')
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            raise e
    
    @staticmethod
    def export_conversation(conversation_id, user_id):
        """导出对话内容"""
        try:
            history = AnalysisHistory.query.filter_by(
                conversation_id=conversation_id,
                user_id=user_id
            ).first()
            
            if not history:
                return None
            
            messages = history.messages or []
            
            text_content = f"对话标题: {history.title or '新对话'}\n"
            text_content += f"创建时间: {history.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            text_content += f"使用Agent: {history.agent_used}\n"
            text_content += "=" * 50 + "\n\n"
            
            for msg in messages:
                role = "用户" if msg.get("role") == "user" else "AI助手"
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M:%S')
                    except:
                        time_str = ""
                else:
                    time_str = ""
                
                text_content += f"[{time_str}] {role}:\n{content}\n\n"
            
            return {
                "title": history.title or '新对话',
                "content": text_content
            }
        except Exception as e:
            raise e
