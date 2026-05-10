from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import uuid
import os
import base64
from werkzeug.utils import secure_filename
from sqlalchemy.orm.attributes import flag_modified
from app import db
from app.models.user import User
from app.models.history import AnalysisHistory
from app.agents.orchestrator import AgentOrchestrator

api_bp = Blueprint('api', __name__)
orchestrator = AgentOrchestrator()


@api_bp.route('/test', methods=['GET'])
def test_route():
    from flask_login import current_user
    return jsonify({
        "code": 200, 
        "message": "API is working",
        "logged_in": current_user.is_authenticated,
        "user_id": current_user.id if current_user.is_authenticated else None
    })


@api_bp.route('/agent/chat', methods=['POST'])
@login_required
def agent_chat():
    data = request.get_json()
    message = data.get('message', '')
    agent_type = data.get('agent_type', 'auto')
    conversation_id = data.get('conversation_id')

    if not message:
        return jsonify({"code": 400, "error": "消息不能为空"}), 400

    if not conversation_id:
        conversation_id = str(uuid.uuid4())[:8]

    force_agent = agent_type if agent_type != 'auto' else None
    result = orchestrator.process(message, current_user.id, force_agent)

    if result["success"]:
        history = AnalysisHistory.query.filter_by(
            conversation_id=conversation_id,
            user_id=current_user.id
        ).first()

        if not history:
            title = message[:30] + ('...' if len(message) > 30 else '')
            history = AnalysisHistory(
                user_id=current_user.id,
                conversation_id=conversation_id,
                title=title,
                analysis_type=agent_type,
                agent_used=result.get("agent_used", "unknown"),
                input_data={"message": message},
                result_data={"output": result["output"]},
                reasoning_steps=result.get("intermediate_steps", []),
                tools_used=[s["action"] for s in result.get("intermediate_steps", [])],
                messages=[]
            )
            db.session.add(history)
        else:
            history.input_data = {"message": message}
            history.result_data = {"output": result["output"]}
            history.reasoning_steps = result.get("intermediate_steps", [])
            existing_tools = history.tools_used or []
            new_tools = [s["action"] for s in result.get("intermediate_steps", [])]
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
            "content": result["output"],
            "agent": result.get("agent_used"),
            "steps": result.get("intermediate_steps", []),
            "timestamp": datetime.utcnow().isoformat()
        })
        history.messages = messages
        history.updated_at = datetime.utcnow()
        
        # 标记JSON字段为已修改，确保SQLAlchemy检测到变化
        flag_modified(history, 'messages')
        flag_modified(history, 'tools_used')

        db.session.commit()

        return jsonify({
            "code": 200,
            "data": {
                "conversation_id": conversation_id,
                "response": result["output"],
                "agent_used": result.get("agent_used"),
                "reasoning_steps": result.get("intermediate_steps", []),
                "tools_used": list(set(s["action"] for s in result.get("intermediate_steps", [])))
            }
        })
    else:
        return jsonify({"code": 500, "error": result.get("error", "处理失败")}), 500


@api_bp.route('/history/<conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    # 获取该conversation_id的最新记录
    history = AnalysisHistory.query.filter_by(
        conversation_id=conversation_id,
        user_id=current_user.id
    ).order_by(AnalysisHistory.updated_at.desc()).first()

    if not history:
        return jsonify({"code": 404, "error": "对话不存在"}), 404

    return jsonify({
        "code": 200,
        "data": {
            "conversation_id": history.conversation_id,
            "title": history.title,
            "agent_used": history.agent_used,
            "messages": history.messages or [],
            "created_at": history.created_at.isoformat(),
            "updated_at": history.updated_at.isoformat() if history.updated_at else None
        }
    })


@api_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    # 获取每个conversation_id的最新记录
    from sqlalchemy import func
    
    # 先获取每个conversation_id的最大updated_at
    subquery = db.session.query(
        AnalysisHistory.conversation_id,
        func.max(AnalysisHistory.updated_at).label('max_updated')
    ).filter_by(user_id=current_user.id).group_by(
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
        AnalysisHistory.user_id == current_user.id
    ).order_by(
        AnalysisHistory.updated_at.desc()
    ).limit(50).all()

    return jsonify({
        "code": 200,
        "data": [{
            "conversation_id": h.conversation_id,
            "title": h.title,
            "agent_used": h.agent_used,
            "message_count": len(h.messages) if h.messages else 0,
            "last_message": h.messages[-1]["content"][:50] if h.messages else "",
            "created_at": h.created_at.isoformat(),
            "updated_at": h.updated_at.isoformat() if h.updated_at else None
        } for h in histories]
    })


@api_bp.route('/history/<conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    try:
        # 删除该conversation_id的所有记录
        count = AnalysisHistory.query.filter_by(
            conversation_id=conversation_id,
            user_id=current_user.id
        ).delete()
        db.session.commit()
        return jsonify({"code": 200, "message": "已删除", "count": count})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/agent/tools', methods=['GET'])
@login_required
def agent_tools():
    status = orchestrator.get_agent_status()
    return jsonify({"code": 200, "data": status})


@api_bp.route('/user/update-username', methods=['POST'])
@login_required
def update_username():
    data = request.get_json()
    new_username = data.get('username', '').strip()
    
    if not new_username:
        return jsonify({"code": 400, "error": "用户名不能为空"}), 400
    
    if len(new_username) < 2 or len(new_username) > 50:
        return jsonify({"code": 400, "error": "用户名长度需在2-50个字符之间"}), 400
    
    existing = User.query.filter(User.username == new_username, User.id != current_user.id).first()
    if existing:
        return jsonify({"code": 400, "error": "用户名已被占用"}), 400
    
    try:
        current_user.username = new_username
        db.session.commit()
        return jsonify({"code": 200, "message": "用户名修改成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/user/update-password', methods=['POST'])
@login_required
def update_password():
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    if not old_password or not new_password:
        return jsonify({"code": 400, "error": "请填写完整"}), 400
    
    if not current_user.check_password(old_password):
        return jsonify({"code": 400, "error": "当前密码错误"}), 400
    
    if len(new_password) < 6:
        return jsonify({"code": 400, "error": "新密码长度至少6位"}), 400
    
    try:
        current_user.set_password(new_password)
        db.session.commit()
        return jsonify({"code": 200, "message": "密码修改成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/user/update-avatar', methods=['POST'])
@login_required
def update_avatar():
    data = request.get_json()
    avatar_data = data.get('avatar', '')
    
    if not avatar_data:
        return jsonify({"code": 400, "error": "请选择头像"}), 400
    
    try:
        if avatar_data.startswith('data:image'):
            header, encoded = avatar_data.split(',', 1)
            image_data = base64.b64decode(encoded)
            
            upload_dir = os.path.join('app', 'static', 'uploads', 'avatars')
            os.makedirs(upload_dir, exist_ok=True)
            
            filename = f"avatar_{current_user.id}.png"
            filepath = os.path.join(upload_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            current_user.avatar = f"/static/uploads/avatars/{filename}"
            db.session.commit()
            
            return jsonify({"code": 200, "message": "头像更新成功", "avatar_url": current_user.avatar})
        
        return jsonify({"code": 400, "error": "无效的图片数据"}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/user/stats', methods=['GET'])
@login_required
def user_stats():
    try:
        from sqlalchemy import func
        
        total_conversations = AnalysisHistory.query.filter_by(user_id=current_user.id).count()
        
        total_messages = 0
        histories = AnalysisHistory.query.filter_by(user_id=current_user.id).all()
        for h in histories:
            if h.messages:
                total_messages += len(h.messages)
        
        agent_stats = db.session.query(
            AnalysisHistory.agent_used,
            func.count(AnalysisHistory.id)
        ).filter_by(user_id=current_user.id).group_by(
            AnalysisHistory.agent_used
        ).all()
        
        agent_usage = {agent: count for agent, count in agent_stats}
        
        recent_days = db.session.query(
            func.date(AnalysisHistory.created_at).label('date'),
            func.count(AnalysisHistory.id).label('count')
        ).filter_by(user_id=current_user.id).group_by(
            func.date(AnalysisHistory.created_at)
        ).order_by(
            func.date(AnalysisHistory.created_at).desc()
        ).limit(7).all()
        
        daily_activity = [{"date": str(date), "count": count} for date, count in recent_days]
        
        return jsonify({
            "code": 200,
            "data": {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "agent_usage": agent_usage,
                "daily_activity": daily_activity
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/export/conversation/<conversation_id>', methods=['GET'])
@login_required
def export_conversation(conversation_id):
    try:
        history = AnalysisHistory.query.filter_by(
            conversation_id=conversation_id,
            user_id=current_user.id
        ).first()
        
        if not history:
            return jsonify({"code": 404, "error": "对话不存在"}), 404
        
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
        
        return jsonify({
            "code": 200,
            "data": {
                "title": history.title or '新对话',
                "content": text_content
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500
