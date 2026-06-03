"""
API路由模块
只负责路由定义和请求/响应处理，业务逻辑由services层处理
"""

from flask import Blueprint, request, jsonify, send_file, Response, stream_with_context
from flask_login import login_required, current_user

from app.services.chat_service import ChatService
from app.services.history_service import HistoryService
from app.services.user_service import UserService
from app.services.resume_service import ResumeService
from app.services.profile_service import ProfileService

api_bp = Blueprint('api', __name__)


# ==================== 测试接口 ====================

@api_bp.route('/test', methods=['GET'])
def test_route():
    return jsonify({"code": 200, "message": "API is working"})


# ==================== 对话相关接口 ====================

@api_bp.route('/agent/chat/async', methods=['POST'])
@login_required
def agent_chat_async():
    """异步Agent对话（轮询模式，支持实时推理步骤）"""
    data = request.get_json()
    message = data.get('message', '')
    agent_type = data.get('agent_type', 'auto')
    conversation_id = data.get('conversation_id')
    
    if not message:
        return jsonify({"code": 400, "error": "消息不能为空"}), 400
    
    try:
        result = ChatService.process_async_chat(
            message, current_user.id, agent_type, conversation_id
        )
        return jsonify({"code": 200, "data": result})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/agent/task/<task_id>', methods=['GET'])
@login_required
def get_task_status(task_id):
    """查询任务状态（包含实时推理步骤）"""
    result = ChatService.get_task_status(task_id)
    
    if result is None:
        return jsonify({"code": 404, "error": "任务不存在"}), 404
    
    return jsonify({"code": 200, "data": result})


@api_bp.route('/agent/chat', methods=['POST'])
@login_required
def agent_chat():
    """同步Agent对话"""
    data = request.get_json()
    message = data.get('message', '')
    agent_type = data.get('agent_type', 'auto')
    conversation_id = data.get('conversation_id')
    
    if not message:
        return jsonify({"code": 400, "error": "消息不能为空"}), 400
    
    try:
        from app import db
        db.session.rollback()  # 清除可能的失败事务
    except Exception:
        pass
    
    try:
        result = ChatService.process_sync_chat(
            message, current_user.id, agent_type, conversation_id
        )
        return jsonify({"code": 200, "data": result})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/agent/chat/stream', methods=['POST'])
@login_required
def agent_chat_stream():
    """SSE流式响应 - 实时推理步骤"""
    data = request.get_json()
    message = data.get('message', '')
    agent_type = data.get('agent_type', 'auto')
    conversation_id = data.get('conversation_id')
    last_agent = data.get('last_agent')
    
    if not message:
        return jsonify({"code": 400, "error": "消息不能为空"}), 400
    
    try:
        generate_func, task_id = ChatService.process_stream_chat(
            message, current_user.id, agent_type, conversation_id, last_agent
        )
        
        return Response(
            stream_with_context(generate_func()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/agent/tools', methods=['GET'])
@login_required
def agent_tools():
    """获取Agent工具状态"""
    status = ChatService.get_agent_status()
    return jsonify({"code": 200, "data": status})


# ==================== 历史记录接口 ====================

@api_bp.route('/history/<conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    """获取对话详情"""
    result = HistoryService.get_conversation(conversation_id, current_user.id)
    
    if result is None:
        return jsonify({"code": 404, "error": "对话不存在"}), 404
    
    return jsonify({"code": 200, "data": result})


@api_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """获取历史记录列表"""
    try:
        from app import db
        db.session.rollback()
    except Exception:
        pass
    
    histories = HistoryService.get_history_list(current_user.id)
    return jsonify({"code": 200, "data": histories})


@api_bp.route('/history/<conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """删除对话"""
    try:
        count = HistoryService.delete_conversation(conversation_id, current_user.id)
        return jsonify({"code": 200, "message": "已删除", "count": count})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/history/save', methods=['POST'])
@login_required
def save_conversation():
    """保存对话记录（用于异步模式）"""
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    message = data.get('message', '')
    result = data.get('result', {})
    
    if not conversation_id or not message:
        return jsonify({"code": 400, "error": "参数不完整"}), 400
    
    try:
        HistoryService.save_conversation(
            conversation_id, current_user.id, message, result
        )
        return jsonify({"code": 200, "message": "保存成功"})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/export/conversation/<conversation_id>', methods=['GET'])
@login_required
def export_conversation(conversation_id):
    """导出对话"""
    try:
        result = HistoryService.export_conversation(conversation_id, current_user.id)
        
        if result is None:
            return jsonify({"code": 404, "error": "对话不存在"}), 404
        
        return jsonify({"code": 200, "data": result})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


# ==================== 用户管理接口 ====================

@api_bp.route('/user/update-username', methods=['POST'])
@login_required
def update_username():
    """更新用户名"""
    data = request.get_json()
    new_username = data.get('username', '').strip()
    
    result = UserService.update_username(current_user, new_username)
    
    if result['success']:
        return jsonify({"code": 200, "message": result['message']})
    else:
        return jsonify({"code": 400, "error": result['error']}), 400


@api_bp.route('/user/update-password', methods=['POST'])
@login_required
def update_password():
    """更新密码"""
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    result = UserService.update_password(current_user, old_password, new_password)
    
    if result['success']:
        return jsonify({"code": 200, "message": result['message']})
    else:
        return jsonify({"code": 400, "error": result['error']}), 400


@api_bp.route('/user/update-avatar', methods=['POST'])
@login_required
def update_avatar():
    """更新头像"""
    data = request.get_json()
    avatar_data = data.get('avatar', '')
    
    result = UserService.update_avatar(current_user, avatar_data)
    
    if result['success']:
        return jsonify({
            "code": 200, 
            "message": result['message'], 
            "avatar_url": result['avatar_url']
        })
    else:
        return jsonify({"code": 400, "error": result['error']}), 400


@api_bp.route('/user/stats', methods=['GET'])
@login_required
def user_stats():
    """获取用户统计"""
    try:
        stats = UserService.get_user_stats(current_user.id)
        return jsonify({"code": 200, "data": stats})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


# ==================== 简历相关接口 ====================

@api_bp.route('/upload/resume', methods=['POST'])
@login_required
def upload_resume():
    """上传简历文件"""
    if 'file' not in request.files:
        return jsonify({"code": 400, "error": "没有上传文件"}), 400
    
    file = request.files['file']
    result = ResumeService.upload_resume(file)
    
    if result['success']:
        return jsonify({"code": 200, "data": result['data']})
    else:
        return jsonify({"code": 400, "error": result['error']}), 400


@api_bp.route('/download/resume', methods=['POST'])
@login_required
def download_resume():
    """下载简历文件"""
    data = request.get_json()
    content = data.get('content', '')
    filename = data.get('filename', 'resume')
    file_format = data.get('format', 'html')
    
    result = ResumeService.download_resume(content, filename, file_format)
    
    if result['success']:
        return result['file']
    else:
        return jsonify({"code": 400, "error": result['error']}), 400


# ==================== 档案相关接口 ====================

@api_bp.route('/profile/completion', methods=['GET'])
@login_required
def get_profile_completion():
    """获取档案完善度"""
    try:
        result = ProfileService.get_profile_completion(current_user.id)
        return jsonify({"code": 200, "data": result})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/profile/milestones', methods=['GET'])
@login_required
def get_milestones():
    """获取决策里程碑"""
    try:
        milestones = ProfileService.get_milestones(current_user.id)
        return jsonify({"code": 200, "data": milestones})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/profile/next-actions', methods=['GET'])
@login_required
def get_next_actions():
    """获取Next Action动态建议"""
    try:
        actions = ProfileService.get_next_actions(current_user.id)
        return jsonify({"code": 200, "data": actions})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """更新用户档案"""
    data = request.get_json()
    
    if not data:
        return jsonify({"code": 400, "error": "请填写档案信息"}), 400
    
    result = ProfileService.update_profile(current_user.id, data)
    
    if result['success']:
        return jsonify({"code": 200, "message": result['message']})
    else:
        return jsonify({"code": 500, "error": result['error']}), 500
