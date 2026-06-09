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
from app.agents.orchestrator import AgentOrchestrator
from app.agents.base_agent import ClientDisconnectedError


class ChatService:
    """对话服务类"""
    
    # 模块级任务存储
    _task_store = {}
    _sse_task_queues = {}
    _aborted_tasks = set()
    
    @classmethod
    def abort_task(cls, task_id):
        cls._aborted_tasks.add(task_id)
        if task_id in cls._sse_task_queues:
            try:
                cls._sse_task_queues[task_id].put({
                    'type': 'error',
                    'error': '用户中止了操作'
                })
            except Exception:
                pass
    

    
    @classmethod
    def get_task_store(cls):
        return cls._task_store
    
    @classmethod
    def get_sse_task_queues(cls):
        return cls._sse_task_queues
    
    @staticmethod
    def run_orchestrator_with_steps(message, user_id, force_agent, task_id):
        """执行orchestrator并实时更新步骤"""
        task_store = ChatService._task_store
        
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
        
        time.sleep(0.5)
        
        # 确定使用哪个Agent
        agent_name = force_agent or "career"
        agent_names = {
            "career": "职业规划顾问",
            "skill": "技能发展顾问",
            "side_job": "副业规划专家",
            "resume": "简历优化专家",
            "interview": "面试教练"
        }
        
        # 更新为分析完成
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
            
            all_steps = []
            if execution_steps:
                all_steps.extend(execution_steps)
            if intermediate_steps:
                all_steps.extend(intermediate_steps)
            
            if not all_steps:
                for step in simulated_steps:
                    step["status"] = "completed"
                all_steps = simulated_steps
            
            task_store[task_id]['steps'] = all_steps
            task_store[task_id]['progress'] = f'已完成 {len(all_steps)} 个步骤'
        
        return result
    
    @staticmethod
    def process_async_chat(message, user_id, agent_type, conversation_id):
        """处理异步对话请求"""
        task_store = ChatService._task_store
        
        if not conversation_id:
            conversation_id = str(uuid.uuid4())[:8]
        
        force_agent = agent_type if agent_type != 'auto' else None
        task_id = str(uuid.uuid4())[:12]
        
        # 获取Flask应用对象
        app = current_app._get_current_object()
        
        # 存储任务状态
        task_store[task_id] = {
            'status': 'pending',
            'progress': '正在准备...',
            'steps': [],
            'result': None,
            'error': None,
            'conversation_id': conversation_id
        }
        
        # 后台执行Agent
        def run_agent():
            with app.app_context():
                try:
                    task_store[task_id]['status'] = 'running'
                    task_store[task_id]['progress'] = '正在分析您的问题...'
                    
                    result = ChatService.run_orchestrator_with_steps(
                        message, user_id, force_agent, task_id
                    )
                    
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
        
        return {
            "task_id": task_id,
            "conversation_id": conversation_id,
            "status": "pending"
        }
    
    @staticmethod
    def get_task_status(task_id):
        """获取任务状态"""
        task_store = ChatService._task_store
        
        if task_id not in task_store:
            return None
        
        task = task_store[task_id]
        
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
                    s["action"] for s in result.get("intermediate_steps", [])
                )),
                "execution_steps": result.get("steps", []),
                "is_composite": result.get("is_composite", False)
            }
        else:
            raise Exception(result.get("error", "处理失败"))
    
    @staticmethod
    def process_stream_chat(message, user_id, agent_type, conversation_id, last_agent):
        """处理流式对话请求，返回生成器和任务ID"""
        task_queues = ChatService._sse_task_queues
        
        if not conversation_id:
            conversation_id = str(uuid.uuid4())[:8]
        
        force_agent = agent_type if agent_type != 'auto' else None
        task_id = str(uuid.uuid4())[:12]
        
        # 创建任务队列
        task_queue = queue.Queue()
        task_queues[task_id] = task_queue
        
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

        # 1. 立即将用户发送的消息保存到数据库中，防止丢失
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
        
        def on_step_callback(step_data):
            """步骤更新回调函数"""
            if task_id in ChatService._aborted_tasks:
                raise ClientDisconnectedError("Client disconnected")
            try:
                task_queue.put({
                    'type': 'step',
                    'data': step_data
                })
            except Exception:
                pass
        
        def on_token_callback(token):
            """流式Token回调函数"""
            if task_id in ChatService._aborted_tasks:
                raise ClientDisconnectedError("Client disconnected")
            if task_id in ChatService._sse_task_queues:
                task_queue.put({
                    'type': 'content',
                    'data': {'content': token}
                })
        
        def generate():
            """SSE生成器"""
            try:
                yield f"event: start\ndata: {json.dumps({'task_id': task_id, 'conversation_id': conversation_id})}\n\n"
                
                while True:
                    try:
                        event = task_queue.get(timeout=300)  # 增加到300秒
                        event_type = event.get('type')
                        
                        if event_type == 'step':
                            yield f"event: step\ndata: {json.dumps(event['data'])}\n\n"
                        elif event_type == 'content':
                            yield f"event: content\ndata: {json.dumps(event['data'])}\n\n"
                        elif event_type == 'progress':
                            yield f"event: progress\ndata: {json.dumps({'message': event['message']})}\n\n"
                        elif event_type == 'done':
                            yield f"event: done\ndata: {json.dumps(event['result'])}\n\n"
                            break
                        elif event_type == 'error':
                            yield f"event: error\ndata: {json.dumps({'error': event['error']})}\n\n"
                            break
                            
                    except queue.Empty:
                        yield f"event: error\ndata: {json.dumps({'error': '请求超时，请稍后重试'})}\n\n"
                        break
                        
            finally:
                if task_id in task_queues:
                    del task_queues[task_id]
                # 任务运行结束或断开后，从 _aborted_tasks 中移除，释放内存
                ChatService._aborted_tasks.discard(task_id)
        
        def run_agent():
            """后台执行Agent"""
            with app.app_context():
                try:
                    if task_id in ChatService._sse_task_queues:
                        task_queue.put({'type': 'progress', 'message': '正在分析意图...'})
                    
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
                    
                    # 如果是被用户显式终止了，才退出
                    if task_id in ChatService._aborted_tasks:
                        print(f"[SSE] Task explicitly aborted: {task_id}")
                        return
 
                    # 发送完成事件
                    if task_id in ChatService._sse_task_queues:
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
 
                    # 保存助手生成的回复到数据库中
                    if result.get("success"):
                        try:
                            history = AnalysisHistory.query.filter_by(
                                conversation_id=conversation_id,
                                user_id=user_id
                            ).first()
                            
                            if history:
                                messages = history.messages or []
                                # 防止在极罕见情况下重复添加 assistant 回复
                                if not messages or messages[-1].get("role") != "assistant":
                                    messages.append({
                                        "role": "assistant",
                                        "content": result.get("output", ""),
                                        "agent": result.get("agent_used"),
                                        "steps": result.get("intermediate_steps", []),
                                        "execution_steps": result.get("steps", []),
                                        "timestamp": datetime.utcnow().isoformat()
                                    })
                                    history.messages = messages
                                    history.result_data = {"output": result.get("output", "")}
                                    history.reasoning_steps = result.get("intermediate_steps", [])
                                    existing_tools = history.tools_used or []
                                    new_tools = [s.get("action", "") for s in result.get("intermediate_steps", [])]
                                    history.tools_used = list(set(existing_tools + new_tools))
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
                    return
                except Exception as e:
                    if task_id in ChatService._aborted_tasks:
                        print(f"[SSE] Background task aborted during exception: {task_id}")
                        return
                        
                    import traceback
                    traceback.print_exc()
                    if task_id in ChatService._sse_task_queues:
                        try:
                            task_queue.put({
                                'type': 'error',
                                'error': str(e)
                            })
                        except Exception:
                            pass
        
        # 启动后台线程
        thread = threading.Thread(target=run_agent)
        thread.start()
        
        return generate, task_id
    
    @staticmethod
    def get_agent_status():
        """获取Agent状态"""
        orchestrator = AgentOrchestrator()
        return orchestrator.get_agent_status()
