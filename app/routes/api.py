from flask import Blueprint, request, jsonify, send_file, Response, stream_with_context, current_app
from flask_login import login_required, current_user
from datetime import datetime
import uuid
import os
import io
import base64
import json
import queue
import threading
from werkzeug.utils import secure_filename
from sqlalchemy.orm.attributes import flag_modified
from app import db
from app.models.user import User
from app.models.history import AnalysisHistory
from app.agents.orchestrator import AgentOrchestrator

api_bp = Blueprint('api', __name__)
orchestrator = AgentOrchestrator()

# 任务存储（使用模块级变量）
task_store = {}

# SSE任务队列存储
sse_task_queues = {}


@api_bp.route('/test', methods=['GET'])
def test_route():
    return jsonify({"code": 200, "message": "API is working"})


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

    if not conversation_id:
        conversation_id = str(uuid.uuid4())[:8]

    force_agent = agent_type if agent_type != 'auto' else None

    # 生成任务ID
    task_id = str(uuid.uuid4())[:12]
    user_id = current_user.id
    
    # 获取Flask应用对象（用于在线程中访问数据库）
    from flask import current_app
    app = current_app._get_current_object()
    
    # 存储任务状态
    task_store[task_id] = {
        'status': 'pending',
        'progress': '正在准备...',
        'steps': [],  # 实时推理步骤
        'result': None,
        'error': None,
        'conversation_id': conversation_id
    }
    
    # 后台执行Agent
    import threading
    def run_agent():
        with app.app_context():
            try:
                task_store[task_id]['status'] = 'running'
                task_store[task_id]['progress'] = '正在分析您的问题...'
                
                # 使用自定义orchestrator，支持实时步骤更新
                result = _run_orchestrator_with_steps(message, user_id, force_agent, task_id)
                
                task_store[task_id]['status'] = 'completed'
                task_store[task_id]['result'] = result
                task_store[task_id]['progress'] = '处理完成'
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                task_store[task_id]['status'] = 'failed'
                task_store[task_id]['error'] = str(e)
    
    thread = threading.Thread(target=run_agent)
    thread.start()
    
    return jsonify({
        "code": 200,
        "data": {
            "task_id": task_id,
            "conversation_id": conversation_id,
            "status": "pending"
        }
    })


def _run_orchestrator_with_steps(message, user_id, force_agent, task_id):
    """执行orchestrator并实时更新步骤（模拟实时进度）"""
    import time
    from app.agents.orchestrator import AgentOrchestrator
    
    # 模拟步骤进度
    simulated_steps = [
        {
            "type": "intent_analysis",
            "title": "正在分析您的意图",
            "detail": "识别问题类型和关键词",
            "status": "running"
        }
    ]
    task_store[task_id]['steps'] = simulated_steps
    task_store[task_id]['progress'] = '正在分析意图...'
    
    time.sleep(0.5)  # 模拟分析时间
    
    # 确定使用哪个Agent
    agent_name = force_agent or "career"
    agent_names = {
        "career": "职业规划顾问",
        "skill": "技能发展顾问",
        "side_job": "副业规划专家",
        "resume": "简历优化专家",
        "interview": "面试教练"
    }
    
    # 更新为分析完成，准备调用Agent
    simulated_steps[0]["status"] = "completed"
    simulated_steps[0]["detail"] = f"识别为{agent_names.get(agent_name, agent_name)}任务"
    simulated_steps.append({
        "type": "agent_call",
        "title": f"调用{agent_names.get(agent_name, agent_name)}",
        "detail": "正在准备执行任务",
        "status": "running"
    })
    task_store[task_id]['steps'] = simulated_steps
    task_store[task_id]['progress'] = f'正在调用{agent_names.get(agent_name, agent_name)}...'
    
    time.sleep(0.3)
    
    # 更新Agent调用状态
    simulated_steps[1]["detail"] = "正在搜索职位数据..."
    simulated_steps.append({
        "type": "tool",
        "title": "执行工具调用",
        "detail": "search_jobs - 搜索相关职位",
        "status": "running"
    })
    task_store[task_id]['steps'] = simulated_steps
    task_store[task_id]['progress'] = '正在搜索数据...'
    
    # 执行实际的orchestrator
    orch = AgentOrchestrator()
    result = orch.process(message, user_id, force_agent)
    
    # 执行完成后，用真实步骤替换模拟步骤
    if result.get("success"):
        execution_steps = result.get("steps", [])
        intermediate_steps = result.get("intermediate_steps", [])
        
        # 合并所有步骤
        all_steps = []
        if execution_steps:
            all_steps.extend(execution_steps)
        if intermediate_steps:
            all_steps.extend(intermediate_steps)
        
        # 如果没有步骤，使用模拟步骤但标记为完成
        if not all_steps:
            for step in simulated_steps:
                step["status"] = "completed"
            all_steps = simulated_steps
        
        task_store[task_id]['steps'] = all_steps
        task_store[task_id]['progress'] = f'已完成 {len(all_steps)} 个步骤'
    
    return result


@api_bp.route('/agent/task/<task_id>', methods=['GET'])
@login_required
def get_task_status(task_id):
    """查询任务状态（包含实时推理步骤）"""
    if task_id not in task_store:
        return jsonify({"code": 404, "error": "任务不存在"}), 404
    
    task = task_store[task_id]
    
    response = {
        "task_id": task_id,
        "status": task['status'],
        "progress": task['progress'],
        "steps": task.get('steps', [])  # 返回实时步骤
    }
    
    if task['status'] == 'completed' and task['result']:
        response['result'] = task['result']
        # 任务完成后清理
        # del task_store[task_id]  # 暂时不清理，方便调试
    elif task['status'] == 'failed' and task['error']:
        response['error'] = task['error']
    
    return jsonify({"code": 200, "data": response})


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
    
    try:
        result = orchestrator.process(message, current_user.id, force_agent)
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "error": f"Agent执行失败: {str(e)}"}), 500

    if result["success"]:
        try:
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
                    result_data={"output": result.get("output", "")},
                    reasoning_steps=result.get("intermediate_steps", []),
                    tools_used=[s["action"] for s in result.get("intermediate_steps", [])],
                    messages=[]
                )
                db.session.add(history)
            else:
                history.input_data = {"message": message}
                history.result_data = {"output": result.get("output", "")}
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
                "content": result.get("output", ""),
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
        except Exception as e:
            db.session.rollback()
            print(f"保存历史记录失败: {e}")
            # 不影响返回结果，继续执行

        return jsonify({
            "code": 200,
            "data": {
                "conversation_id": conversation_id,
                "response": result.get("output", ""),
                "agent_used": result.get("agent_used"),
                "reasoning_steps": result.get("intermediate_steps", []),
                "tools_used": list(set(s["action"] for s in result.get("intermediate_steps", []))),
                "execution_steps": result.get("steps", []),
                "is_composite": result.get("is_composite", False)
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
                analysis_type='auto',
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
        return jsonify({"code": 200, "message": "保存成功"})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"code": 500, "error": str(e)}), 500


@api_bp.route('/agent/chat/stream', methods=['POST'])
@login_required
def agent_chat_stream():
    """SSE流式响应 - 实时推理步骤"""
    data = request.get_json()
    message = data.get('message', '')
    agent_type = data.get('agent_type', 'auto')
    conversation_id = data.get('conversation_id')

    if not message:
        return jsonify({"code": 400, "error": "消息不能为空"}), 400

    if not conversation_id:
        conversation_id = str(uuid.uuid4())[:8]

    force_agent = agent_type if agent_type != 'auto' else None
    user_id = current_user.id
    task_id = str(uuid.uuid4())[:12]
    
    # 创建任务队列
    task_queue = queue.Queue()
    sse_task_queues[task_id] = task_queue
    
    # 获取Flask应用对象
    app = current_app._get_current_object()
    
    def on_step_callback(step_data):
        """步骤更新回调函数（在后台线程中被调用）"""
        task_queue.put({
            'type': 'step',
            'data': step_data
        })
    
    def generate():
        """SSE生成器"""
        try:
            # 发送开始事件
            yield f"event: start\ndata: {json.dumps({'task_id': task_id, 'conversation_id': conversation_id})}\n\n"
            
            # 等待任务完成
            while True:
                try:
                    event = task_queue.get(timeout=60)  # 60秒超时
                    event_type = event.get('type')
                    
                    if event_type == 'step':
                        # 发送步骤更新
                        yield f"event: step\ndata: {json.dumps(event['data'])}\n\n"
                    
                    elif event_type == 'progress':
                        # 发送进度更新
                        yield f"event: progress\ndata: {json.dumps({'message': event['message']})}\n\n"
                    
                    elif event_type == 'done':
                        # 发送完成事件
                        yield f"event: done\ndata: {json.dumps(event['result'])}\n\n"
                        break
                    
                    elif event_type == 'error':
                        # 发送错误事件
                        yield f"event: error\ndata: {json.dumps({'error': event['error']})}\n\n"
                        break
                        
                except queue.Empty:
                    # 超时
                    yield f"event: error\ndata: {json.dumps({'error': '请求超时'})}\n\n"
                    break
                    
        finally:
            # 清理队列
            if task_id in sse_task_queues:
                del sse_task_queues[task_id]
    
    def run_agent():
        """后台执行Agent"""
        with app.app_context():
            try:
                # 发送进度
                task_queue.put({'type': 'progress', 'message': '正在分析意图...'})
                
                # 创建带回调的orchestrator
                from app.agents.orchestrator import AgentOrchestrator
                orch = AgentOrchestrator(on_step_callback=on_step_callback)
                
                # 执行orchestrator
                result = orch.process(message, user_id, force_agent)
                
                # 保存对话记录
                if result.get("success"):
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
                        
                        flag_modified(history, 'messages')
                        flag_modified(history, 'tools_used')
                        
                        db.session.commit()
                        print(f"[SSE] 对话已保存: {conversation_id}")
                    except Exception as e:
                        db.session.rollback()
                        print(f"[SSE] 保存对话失败: {e}")
                
                # 发送完成事件
                if result.get("success"):
                    task_queue.put({
                        'type': 'done',
                        'result': result
                    })
                else:
                    task_queue.put({
                        'type': 'error',
                        'error': result.get('error', '执行失败')
                    })
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                task_queue.put({
                    'type': 'error',
                    'error': str(e)
                })
    
    # 启动后台线程
    thread = threading.Thread(target=run_agent)
    thread.start()
    
    # 返回SSE响应
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


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


@api_bp.route('/upload/resume', methods=['POST'])
@login_required
def upload_resume():
    """上传简历文件，解析并返回文本内容"""
    if 'file' not in request.files:
        return jsonify({"code": 400, "error": "没有上传文件"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"code": 400, "error": "未选择文件"}), 400
    
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({"code": 400, "error": "不支持的文件格式，请上传PDF、DOCX或TXT文件"}), 400
    
    try:
        text_content = ""
        
        if ext == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file.read()))
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
        
        elif ext in ('.docx', '.doc'):
            from docx import Document
            doc = Document(io.BytesIO(file.read()))
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        
        elif ext == '.txt':
            text_content = file.read().decode('utf-8')
        
        if not text_content.strip():
            return jsonify({"code": 400, "error": "文件内容为空或无法解析"}), 400
        
        return jsonify({
            "code": 200,
            "data": {
                "filename": file.filename,
                "content": text_content.strip(),
                "file_type": ext
            }
        })
    
    except Exception as e:
        return jsonify({"code": 500, "error": f"文件解析失败: {str(e)}"}), 500


@api_bp.route('/download/resume', methods=['POST'])
@login_required
def download_resume():
    """将简历内容转换为文件下载（支持HTML和DOCX格式）"""
    data = request.get_json()
    content = data.get('content', '')
    filename = data.get('filename', 'resume')
    file_format = data.get('format', 'docx')
    
    if not content:
        return jsonify({"code": 400, "error": "内容不能为空"}), 400
    
    try:
        # 检测是否为HTML格式
        is_html = content.strip().startswith('<!DOCTYPE html>') or content.strip().startswith('<html')
        
        if file_format == 'html' or (file_format == 'docx' and is_html):
            # 如果请求HTML格式，或者内容是HTML但请求DOCX（先尝试HTML导出）
            if file_format == 'html':
                # 直接导出HTML文件
                buffer = io.BytesIO(content.encode('utf-8'))
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=f'{filename}.html',
                    mimetype='text/html'
                )
            else:
                # HTML内容转DOCX：提取文本内容
                from docx import Document
                from docx.shared import Pt, Inches, RGBColor
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                
                doc = Document()
                
                style = doc.styles['Normal']
                style.font.name = 'Arial'
                style.font.size = Pt(11)
                
                # 简单提取HTML中的文本内容
                import re
                # 移除script和style标签
                text_content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
                text_content = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL)
                # 移除HTML标签，保留文本
                text_content = re.sub(r'<[^>]+>', '\n', text_content)
                # 清理多余空白
                text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
                text_content = text_content.strip()
                
                # 按行处理
                lines = text_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # 简单格式化
                    if len(line) < 50 and line.isupper():
                        doc.add_heading(line, level=1)
                    elif line.endswith('：') or line.endswith(':'):
                        p = doc.add_paragraph()
                        run = p.add_run(line)
                        run.bold = True
                    else:
                        doc.add_paragraph(line)
                
                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=f'{filename}.docx',
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
        
        elif file_format == 'docx':
            # Markdown格式转DOCX
            from docx import Document
            from docx.shared import Pt, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            
            doc = Document()
            
            style = doc.styles['Normal']
            style.font.name = 'Arial'
            style.font.size = Pt(11)
            
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    doc.add_paragraph('')
                    continue
                
                if line.startswith('# '):
                    p = doc.add_heading(line[2:].strip(), level=1)
                elif line.startswith('## '):
                    p = doc.add_heading(line[3:].strip(), level=2)
                elif line.startswith('### '):
                    p = doc.add_heading(line[4:].strip(), level=3)
                elif line.startswith('- ') or line.startswith('* '):
                    doc.add_paragraph(line[2:].strip(), style='List Bullet')
                elif line.startswith('**') and line.endswith('**'):
                    p = doc.add_paragraph()
                    run = p.add_run(line[2:-2].strip())
                    run.bold = True
                else:
                    p = doc.add_paragraph(line)
                    if '**' in line:
                        parts = line.split('**')
                        p.clear()
                        for i, part in enumerate(parts):
                            run = p.add_run(part)
                            if i % 2 == 1:
                                run.bold = True
            
            buffer = io.BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f'{filename}.docx',
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        
        else:
            return jsonify({"code": 400, "error": "暂只支持DOCX和HTML格式"}), 400
    
    except Exception as e:
        return jsonify({"code": 500, "error": f"生成文件失败: {str(e)}"}), 500
