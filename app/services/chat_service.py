"""
对话服务模块
处理Agent对话相关的业务逻辑
"""

import uuid
import queue
import threading
import time
import json
from datetime import datetime
from flask import current_app
from sqlalchemy.orm.attributes import flag_modified

from app import db
from app.models.history import AnalysisHistory
from app.models.task import AgentTask
from app.agents.orchestrator import AgentOrchestrator
from app.agents.base_agent import ClientDisconnectedError


class ChatService:
    """对话服务类"""
    
    # 模块级任务存储（带线程锁保护）
    _task_store = {}
    _sse_task_queues = {}
    _aborted_tasks = set()
    _store_lock = threading.Lock()
    
    # Agent状态缓存（避免每次请求都初始化5个Agent）
    _agent_status_cache = None
    _agent_status_cache_time = 0
    
    # ==================== 线程安全的存储操作 ====================
    
    @classmethod
    def _set_task(cls, task_id, data):
        with cls._store_lock:
            cls._task_store[task_id] = data
    
    @classmethod
    def _get_task(cls, task_id):
        with cls._store_lock:
            return cls._task_store.get(task_id)
    
    @classmethod
    def _pop_task(cls, task_id):
        with cls._store_lock:
            return cls._task_store.pop(task_id, None)
    
    @classmethod
    def _cleanup_stale_tasks(cls):
        """清理超过10分钟的已完成/失败任务，防止内存泄漏"""
        now = time.time()
        with cls._store_lock:
            stale_ids = [
                tid for tid, task in cls._task_store.items()
                if task.get('status') in ('completed', 'failed')
                and now - task.get('completed_at', 0) > 600  # 10分钟
            ]
            for tid in stale_ids:
                cls._task_store.pop(tid, None)
    
    # ==================== 任务中止 ====================
    
    @classmethod
    def abort_task(cls, task_id):
        cls._aborted_tasks.add(task_id)
        with cls._store_lock:
            task_queue = cls._sse_task_queues.get(task_id)
        if task_queue:
            try:
                task_queue.put({
                    'type': 'error',
                    'error': '用户中止了操作'
                })
            except Exception:
                pass
    
    # ==================== Agent状态（带缓存） ====================
    
    @classmethod
    def get_agent_status(cls):
        """获取Agent状态（带5分钟TTL缓存，避免重复初始化）"""
        now = time.time()
        if cls._agent_status_cache and now - cls._agent_status_cache_time < 300:
            return cls._agent_status_cache
        
        orch = AgentOrchestrator()
        status = orch.get_agent_status()
        cls._agent_status_cache = status
        cls._agent_status_cache_time = now
        return status
    
    # ==================== 异步对话（轮询模式） ====================
    
    @classmethod
    def process_async_chat(cls, message, user_id, agent_type, conversation_id):
        """处理异步对话请求（使用队列获取真实步骤，不再模拟）"""
        if not conversation_id:
            conversation_id = str(uuid.uuid4())[:8]
        
        force_agent = agent_type if agent_type != 'auto' else None
        task_id = str(uuid.uuid4())[:12]
        
        # 获取Flask应用对象
        app = current_app._get_current_object()
        
        # 存储任务状态
        cls._set_task(task_id, {
            'status': 'pending',
            'progress': '正在准备...',
            'steps': [],
            'result': None,
            'error': None,
            'conversation_id': conversation_id,
            'created_at': time.time(),
            'completed_at': 0
        })
        
        # 步骤队列（用于收集真实步骤）
        step_queue = queue.Queue()
        
        def on_step_callback(step_data):
            """步骤更新回调"""
            if task_id in cls._aborted_tasks:
                raise ClientDisconnectedError("Client disconnected")
            try:
                step_queue.put(step_data)
            except Exception:
                pass
        
        def run_agent():
            """后台执行Agent"""
            with app.app_context():
                try:
                    task = cls._get_task(task_id)
                    if task:
                        task['status'] = 'running'
                        task['progress'] = '正在分析您的问题...'
                    
                    orch = AgentOrchestrator(on_step_callback=on_step_callback)
                    result = orch.process(message, user_id, force_agent)
                    
                    # 收集队列中剩余的步骤
                    all_steps = []
                    while not step_queue.empty():
                        try:
                            all_steps.append(step_queue.get_nowait())
                        except queue.Empty:
                            break
                    
                    task = cls._get_task(task_id)
                    if task:
                        task['status'] = 'completed'
                        task['result'] = result
                        task['progress'] = '处理完成'
                        task['steps'] = all_steps or result.get('steps', [])
                        task['completed_at'] = time.time()
                    
                except ClientDisconnectedError:
                    task = cls._get_task(task_id)
                    if task:
                        task['status'] = 'failed'
                        task['error'] = '用户中止了操作'
                        task['completed_at'] = time.time()
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    task = cls._get_task(task_id)
                    if task:
                        task['status'] = 'failed'
                        task['error'] = str(e)
                        task['completed_at'] = time.time()
                
                finally:
                    # 延迟清理：30秒后删除任务数据（给前端足够时间轮询结果）
                    def delayed_cleanup():
                        time.sleep(30)
                        cls._pop_task(task_id)
                        cls._aborted_tasks.discard(task_id)
                    threading.Thread(target=delayed_cleanup, daemon=True).start()
        
        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()
        
        return {
            "task_id": task_id,
            "conversation_id": conversation_id,
            "status": "pending"
        }
    
    @classmethod
    def get_task_status(cls, task_id):
        """获取任务状态"""
        # 每次查询时顺便清理过期任务
        cls._cleanup_stale_tasks()
        
        task = cls._get_task(task_id)
        if task is None:
            return None
        
        response = {
            "task_id": task_id,
            "status": task['status'],
            "progress": task['progress'],
            "steps": task.get('steps', [])
        }
        
        if task['status'] == 'completed' and task['result']:
            result = task['result']
            response['result'] = {
                "output": result.get("output", ""),
                "agent_used": result.get("agent_used"),
                "reasoning_steps": result.get("intermediate_steps", []),
                "intermediate_steps": result.get("intermediate_steps", []),
                "tools_used": list(set(
                    s.get("action", "") for s in result.get("intermediate_steps", []) if isinstance(s, dict) and s.get("action")
                )),
                "execution_steps": result.get("steps", []),
                "steps": result.get("steps", []),
                "is_composite": result.get("is_composite", False)
            }
        elif task['status'] == 'failed':
            response['error'] = task.get('error', '未知错误')
        
        return response
    
    # ==================== 同步对话 ====================
    
    @staticmethod
    def process_sync_chat(message, user_id, agent_type, conversation_id):
        """处理同步对话请求"""
        if not conversation_id:
            conversation_id = str(uuid.uuid4())[:8]
        
        force_agent = agent_type if agent_type != 'auto' else None
        
        orchestrator = AgentOrchestrator()
        result = orchestrator.process(message, user_id, force_agent)
        
        if result["success"]:
            try:
                db.session.rollback()
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
                        tools_used=[s["action"] for s in result.get("intermediate_steps", []) if isinstance(s, dict) and s.get("action")],
                        messages=[]
                    )
                    db.session.add(history)
                else:
                    history.input_data = {"message": message}
                    history.result_data = {"output": result.get("output", "")}
                    history.reasoning_steps = result.get("intermediate_steps", [])
                    existing_tools = history.tools_used or []
                    new_tools = [s["action"] for s in result.get("intermediate_steps", []) if isinstance(s, dict) and s.get("action")]
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
                
                flag_modified(history, 'messages')
                flag_modified(history, 'tools_used')
                
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"保存历史记录失败: {e}")
            
            return {
                "conversation_id": conversation_id,
                "response": result.get("output", ""),
                "agent_used": result.get("agent_used"),
                "reasoning_steps": result.get("intermediate_steps", []),
                "tools_used": list(set(
                    s["action"] for s in result.get("intermediate_steps", []) if isinstance(s, dict) and s.get("action")
                )),
                "execution_steps": result.get("steps", []),
                "is_composite": result.get("is_composite", False)
            }
        else:
            raise Exception(result.get("error", "处理失败"))
    
    # ==================== SSE流式对话 ====================
    
    @classmethod
    def process_stream_chat(cls, message, user_id, agent_type, conversation_id, last_agent):
        """处理流式对话请求，返回生成器和任务ID"""
        if not conversation_id:
            conversation_id = str(uuid.uuid4())[:8]
        
        force_agent = agent_type if agent_type != 'auto' else None
        task_id = str(uuid.uuid4())[:12]
        
        # 创建任务队列
        task_queue = queue.Queue()
        with cls._store_lock:
            cls._sse_task_queues[task_id] = task_queue
        
        # 持久化任务到数据库
        try:
            db.session.rollback()
            agent_task = AgentTask(
                task_id=task_id,
                user_id=user_id,
                conversation_id=conversation_id,
                message=message,
                agent_type=force_agent,
                last_agent=last_agent,
                status='running',
                started_at=datetime.utcnow()
            )
            db.session.add(agent_task)
            db.session.commit()
            print(f"[SSE] 任务已持久化到数据库: {task_id}")
        except Exception as e:
            db.session.rollback()
            print(f"[SSE] 任务持久化失败: {e}")
        
        # 获取Flask应用对象
        app = current_app._get_current_object()
        
        # 获取对话历史
        conversation_history = []
        try:
            db.session.rollback()
            histories = AnalysisHistory.query.filter_by(
                conversation_id=conversation_id,
                user_id=user_id
            ).order_by(AnalysisHistory.updated_at.desc()).first()
            if histories and histories.messages:
                conversation_history = histories.messages[-10:]
        except Exception as e:
            print(f"获取对话历史失败: {e}")

        # 立即将用户消息保存到数据库，防止丢失
        try:
            db.session.rollback()
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
                    agent_used=last_agent or "unknown",
                    input_data={"message": message},
                    result_data={"output": ""},
                    reasoning_steps=[],
                    tools_used=[],
                    messages=[]
                )
                db.session.add(history)
            
            messages = history.messages or []
            messages.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            })
            history.messages = messages
            history.updated_at = datetime.utcnow()
            flag_modified(history, 'messages')
            db.session.commit()
            print(f"[SSE] 用户消息已提前保存: {conversation_id}")
        except Exception as e:
            db.session.rollback()
            print(f"[SSE] 提前保存用户消息失败: {e}")
        
        # 内存中收集步骤，定期批量写入数据库
        _pending_steps = []
        _step_lock = threading.Lock()
        
        def _flush_steps_to_db():
            """将待处理的步骤批量写入数据库"""
            try:
                with _step_lock:
                    if not _pending_steps:
                        return
                    steps_to_write = list(_pending_steps)
                    _pending_steps.clear()
                
                db.session.rollback()
                task = AgentTask.query.filter_by(task_id=task_id).first()
                if task:
                    progress = task.progress or []
                    progress.extend(steps_to_write)
                    task.progress = progress
                    db.session.commit()
            except Exception:
                db.session.rollback()
        
        def on_step_callback(step_data):
            """步骤更新回调函数（非阻塞）"""
            if task_id in cls._aborted_tasks:
                raise ClientDisconnectedError("Client disconnected")
            try:
                # 动态获取当前活动队列（可能已被 restore 替换）
                with cls._store_lock:
                    current_queue = cls._sse_task_queues.get(task_id)
                if current_queue:
                    current_queue.put({
                        'type': 'step',
                        'data': step_data
                    })
                # 收集到内存，后续批量写入
                with _step_lock:
                    _pending_steps.append(step_data)
            except Exception:
                pass
        
        def on_token_callback(token):
            """流式Token回调函数"""
            if task_id in cls._aborted_tasks:
                raise ClientDisconnectedError("Client disconnected")
            with cls._store_lock:
                current_queue = cls._sse_task_queues.get(task_id)
                if current_queue:
                    current_queue.put({
                        'type': 'content',
                        'data': {'content': token}
                    })
        
        @staticmethod
        def _safe_json_dumps(data):
            """安全的JSON序列化，处理不可序列化的对象"""
            try:
                return json.dumps(data, ensure_ascii=False, default=str)
            except Exception:
                # 最终兜底：只保留基本字段
                try:
                    safe = {
                        k: v for k, v in data.items()
                        if isinstance(v, (str, int, float, bool, type(None)))
                    }
                    return json.dumps(safe, ensure_ascii=False, default=str)
                except Exception:
                    return json.dumps({"error": "结果序列化失败"})

        def generate():
            """SSE生成器"""
            try:
                yield f"event: start\ndata: {json.dumps({'task_id': task_id, 'conversation_id': conversation_id})}\n\n"

                while True:
                    try:
                        event = task_queue.get(timeout=300)
                        event_type = event.get('type')

                        if event_type == 'step':
                            yield f"event: step\ndata: {ChatService._safe_json_dumps(event['data'])}\n\n"
                        elif event_type == 'content':
                            yield f"event: content\ndata: {ChatService._safe_json_dumps(event['data'])}\n\n"
                        elif event_type == 'progress':
                            yield f"event: progress\ndata: {json.dumps({'message': event['message']})}\n\n"
                        elif event_type == 'done':
                            # 构建精简的完成数据，避免序列化失败
                            result = event.get('result', {})
                            done_data = {
                                'success': result.get('success', False),
                                'output': result.get('output', ''),
                                'agent_used': result.get('agent_used', ''),
                                'intermediate_steps': result.get('intermediate_steps', []),
                                'steps': result.get('steps', []),
                                'is_composite': result.get('is_composite', False),
                                'score': result.get('score', 0),
                            }
                            yield f"event: done\ndata: {ChatService._safe_json_dumps(done_data)}\n\n"
                            break
                        elif event_type == 'error':
                            yield f"event: error\ndata: {json.dumps({'error': str(event.get('error', '未知错误'))})}\n\n"
                            break

                    except queue.Empty:
                        yield f"event: error\ndata: {json.dumps({'error': '请求超时，请稍后重试'})}\n\n"
                        break

            finally:
                with cls._store_lock:
                    cls._sse_task_queues.pop(task_id, None)
                cls._aborted_tasks.discard(task_id)
        
        def run_agent():
            """后台执行Agent"""
            with app.app_context():
                try:
                    with cls._store_lock:
                        current_queue = cls._sse_task_queues.get(task_id)
                    if current_queue:
                        current_queue.put({'type': 'progress', 'message': '正在分析意图...'})
                    
                    orch = AgentOrchestrator(
                        on_step_callback=on_step_callback,
                        on_token_callback=on_token_callback
                    )
                    
                    result = orch.process(
                        message, 
                        user_id, 
                        force_agent,
                        last_agent=last_agent,
                        conversation_history=conversation_history
                    )
                    
                    # 如果被用户显式终止
                    if task_id in cls._aborted_tasks:
                        print(f"[SSE] Task explicitly aborted: {task_id}")
                        _flush_steps_to_db()  # 保存已收集的步骤
                        # 更新数据库状态为已中止
                        try:
                            db.session.rollback()
                            task = AgentTask.query.filter_by(task_id=task_id).first()
                            if task:
                                task.status = 'aborted'
                                task.completed_at = datetime.utcnow()
                                db.session.commit()
                        except Exception:
                            db.session.rollback()
                        return
 
                    # 发送完成事件（动态获取当前活动队列，可能已被 restore 替换）
                    with cls._store_lock:
                        current_queue = cls._sse_task_queues.get(task_id)
                    if current_queue:
                        if result.get("success"):
                            current_queue.put({
                                'type': 'done',
                                'result': result
                            })
                        else:
                            current_queue.put({
                                'type': 'error',
                                'error': result.get('error', '执行失败')
                            })
                    
                    # 刷新剩余步骤到数据库
                    _flush_steps_to_db()
                    
                    # 更新任务状态为已完成
                    try:
                        db.session.rollback()
                        task = AgentTask.query.filter_by(task_id=task_id).first()
                        if task:
                            task.status = 'completed' if result.get("success") else 'failed'
                            task.result = result
                            task.completed_at = datetime.utcnow()
                            if not result.get("success"):
                                task.error = result.get('error', '执行失败')
                            db.session.commit()
                            print(f"[SSE] 任务状态已更新: {task_id} -> {task.status}")
                    except Exception as e:
                        db.session.rollback()
                        print(f"[SSE] 更新任务状态失败: {e}")
 
                    # 保存助手回复到数据库
                    if result.get("success"):
                        try:
                            db.session.rollback()
                            history = AnalysisHistory.query.filter_by(
                                conversation_id=conversation_id,
                                user_id=user_id
                            ).first()
                            
                            if history:
                                messages = history.messages or []
                                if not messages or messages[-1].get("role") != "assistant":
                                    execution_steps = result.get("steps", [])
                                    intermediate_steps = result.get("intermediate_steps", [])
                                    all_steps = execution_steps + intermediate_steps
                                    tools_used = list(set([
                                        s.get("action", "") or s.get("title", "").replace("调用工具: ", "")
                                        for s in all_steps
                                        if isinstance(s, dict) and (s.get("type") == "tool" or s.get("action"))
                                    ]))
                                    
                                    messages.append({
                                        "role": "assistant",
                                        "content": result.get("output", ""),
                                        "agent": result.get("agent_used"),
                                        "steps": intermediate_steps,
                                        "execution_steps": execution_steps,
                                        "tools_used": tools_used,
                                        "timestamp": datetime.utcnow().isoformat()
                                    })
                                    history.messages = messages
                                    history.result_data = {"output": result.get("output", "")}
                                    history.reasoning_steps = intermediate_steps
                                    history.tools_used = tools_used
                                    history.agent_used = result.get("agent_used", history.agent_used)
                                    history.updated_at = datetime.utcnow()
                                    
                                    flag_modified(history, 'messages')
                                    flag_modified(history, 'tools_used')
                                    db.session.commit()
                                    print(f"[SSE] 助手回复已成功后台保存: {conversation_id}")
                        except Exception as e:
                            db.session.rollback()
                            print(f"[SSE] 后台保存助手回复失败: {e}")
                        
                except ClientDisconnectedError:
                    print(f"[SSE] Task explicitly aborted via ClientDisconnectedError: {task_id}")
                    _flush_steps_to_db()  # 保存已收集的步骤
                    # 更新数据库状态为已中止
                    try:
                        db.session.rollback()
                        task = AgentTask.query.filter_by(task_id=task_id).first()
                        if task:
                            task.status = 'aborted'
                            task.completed_at = datetime.utcnow()
                            db.session.commit()
                    except Exception:
                        db.session.rollback()
                    return
                except Exception as e:
                    if task_id in cls._aborted_tasks:
                        print(f"[SSE] Background task aborted during exception: {task_id}")
                        _flush_steps_to_db()  # 保存已收集的步骤
                        # 更新数据库状态为已中止
                        try:
                            db.session.rollback()
                            task = AgentTask.query.filter_by(task_id=task_id).first()
                            if task:
                                task.status = 'aborted'
                                task.completed_at = datetime.utcnow()
                                db.session.commit()
                        except Exception:
                            db.session.rollback()
                        return
                        
                    import traceback
                    traceback.print_exc()
                    
                    # 更新数据库状态为失败
                    try:
                        db.session.rollback()
                        task = AgentTask.query.filter_by(task_id=task_id).first()
                        if task:
                            task.status = 'failed'
                            task.error = str(e)
                            task.completed_at = datetime.utcnow()
                            db.session.commit()
                    except Exception:
                        db.session.rollback()
                    
                    with cls._store_lock:
                        current_queue = cls._sse_task_queues.get(task_id)
                    if current_queue:
                        try:
                            current_queue.put({
                                'type': 'error',
                                'error': str(e)
                            })
                        except Exception:
                            pass
        
        # 启动后台线程
        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()
        
        return generate, task_id

    @classmethod
    def get_task_status(cls, task_id, user_id=None):
        """获取任务状态"""
        try:
            db.session.rollback()
            query = AgentTask.query.filter_by(task_id=task_id)
            if user_id:
                query = query.filter_by(user_id=user_id)
            task = query.first()
            if task:
                return task.to_dict()
        except Exception as e:
            db.session.rollback()
            print(f"[Task] 获取任务状态失败: {e}")
        return None

    @classmethod
    def get_active_task(cls, user_id, conversation_id=None):
        """获取用户当前活跃的任务"""
        try:
            db.session.rollback()
            task = AgentTask.get_active_task(user_id, conversation_id)
            if task:
                return task.to_dict()
        except Exception as e:
            db.session.rollback()
            print(f"[Task] 获取活跃任务失败: {e}")
        return None

    @classmethod
    def get_pending_tasks(cls, user_id):
        """获取用户所有待处理和进行中的任务"""
        try:
            db.session.rollback()
            tasks = AgentTask.get_pending_tasks(user_id)
            return [t.to_dict() for t in tasks]
        except Exception as e:
            db.session.rollback()
            print(f"[Task] 获取待处理任务失败: {e}")
        return []

    @classmethod
    def restore_task_stream(cls, task_id, user_id):
        """恢复已完成的任务流（用于断线重连）"""
        try:
            db.session.rollback()
            task = AgentTask.query.filter_by(task_id=task_id, user_id=user_id).first()
            if not task:
                return None, "任务不存在"
            
            if task.status == 'completed':
                # 任务已完成，直接返回结果
                def generate():
                    yield f"event: start\ndata: {json.dumps({'task_id': task_id, 'conversation_id': task.conversation_id})}\n\n"
                    # 发送进度步骤
                    if task.progress:
                        for step in task.progress:
                            yield f"event: step\ndata: {json.dumps(step)}\n\n"
                    # 发送完成结果（确保result格式正确）
                    result_data = task.result or {}
                    # 如果result为空，尝试从对话历史中获取最后一条助手消息
                    if not result_data.get('output'):
                        try:
                            history = AnalysisHistory.query.filter_by(
                                conversation_id=task.conversation_id,
                                user_id=user_id
                            ).first()
                            if history and history.messages:
                                last_assistant = next(
                                    (msg for msg in reversed(history.messages) if msg.get('role') == 'assistant'),
                                    None
                                )
                                if last_assistant:
                                    result_data = {
                                        'output': last_assistant.get('content', ''),
                                        'agent_used': last_assistant.get('agent', ''),
                                        'steps': last_assistant.get('execution_steps', []),
                                        'intermediate_steps': last_assistant.get('steps', []),
                                        'success': True
                                    }
                        except Exception as e:
                            print(f"[Task] 从对话历史获取结果失败: {e}")
                    yield f"event: done\ndata: {ChatService._safe_json_dumps(result_data)}\n\n"
                return generate, task_id
            
            elif task.status in ['pending', 'running']:
                # 任务仍在进行中，创建新的队列让前端可以接收后续事件
                task_queue = queue.Queue()
                with cls._store_lock:
                    cls._sse_task_queues[task_id] = task_queue
                
                def generate():
                    try:
                        yield f"event: start\ndata: {json.dumps({'task_id': task_id, 'conversation_id': task.conversation_id})}\n\n"
                        # 发送已有的进度
                        if task.progress:
                            for step in task.progress:
                                yield f"event: step\ndata: {ChatService._safe_json_dumps(step)}\n\n"

                        # 等待新事件
                        while True:
                            try:
                                event = task_queue.get(timeout=300)
                                event_type = event.get('type')

                                if event_type == 'step':
                                    yield f"event: step\ndata: {ChatService._safe_json_dumps(event['data'])}\n\n"
                                elif event_type == 'content':
                                    yield f"event: content\ndata: {ChatService._safe_json_dumps(event['data'])}\n\n"
                                elif event_type == 'progress':
                                    yield f"event: progress\ndata: {json.dumps({'message': event['message']})}\n\n"
                                elif event_type == 'done':
                                    result = event.get('result', {})
                                    done_data = {
                                        'success': result.get('success', False),
                                        'output': result.get('output', ''),
                                        'agent_used': result.get('agent_used', ''),
                                        'intermediate_steps': result.get('intermediate_steps', []),
                                        'steps': result.get('steps', []),
                                        'is_composite': result.get('is_composite', False),
                                        'score': result.get('score', 0),
                                    }
                                    yield f"event: done\ndata: {ChatService._safe_json_dumps(done_data)}\n\n"
                                    break
                                elif event_type == 'error':
                                    yield f"event: error\ndata: {json.dumps({'error': str(event.get('error', '未知错误'))})}\n\n"
                                    break
                                    
                            except queue.Empty:
                                yield f"event: error\ndata: {json.dumps({'error': '请求超时，请稍后重试'})}\n\n"
                                break
                    finally:
                        with cls._store_lock:
                            cls._sse_task_queues.pop(task_id, None)
                
                return generate, task_id
            
            elif task.status == 'failed':
                # 任务失败，返回错误信息
                def generate():
                    yield f"event: start\ndata: {json.dumps({'task_id': task_id, 'conversation_id': task.conversation_id})}\n\n"
                    yield f"event: error\ndata: {json.dumps({'error': task.error or '任务执行失败'})}\n\n"
                return generate, task_id
            
            elif task.status == 'aborted':
                # 任务已中止
                def generate():
                    yield f"event: start\ndata: {json.dumps({'task_id': task_id, 'conversation_id': task.conversation_id})}\n\n"
                    yield f"event: error\ndata: {json.dumps({'error': '任务已被中止'})}\n\n"
                return generate, task_id
            
            return None, "未知任务状态"
            
        except Exception as e:
            db.session.rollback()
            print(f"[Task] 恢复任务失败: {e}")
            return None, str(e)
