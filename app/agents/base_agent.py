from typing import List, Dict, Any, Optional
from langchain.agents import create_agent
from langchain.tools import BaseTool
from flask import current_app
from langchain_core.callbacks import BaseCallbackHandler
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory


class ClientDisconnectedError(BaseException):
    """Raised when the client disconnects from the SSE stream."""
    pass


class TokenStreamingHandler(BaseCallbackHandler):
    """Callback handler for streaming tokens, filtering out tool calls."""
    def __init__(self, on_token_fn):
        self.on_token_fn = on_token_fn
        
    def on_llm_new_token(self, token: str, chunk: Any = None, **kwargs: Any) -> None:
        if self.on_token_fn:
            if chunk:
                message = getattr(chunk, "message", None)
                if message:
                    # Filter out tool calls
                    if getattr(message, "tool_call_chunks", None):
                        return
            self.on_token_fn(token)


class BaseAgent:
    """智能体基类，实现ReAct推理模式 - 增强版"""

    def __init__(self, agent_name: str, llm=None, on_tool_callback=None, on_token_callback=None):
        self.agent_name = agent_name
        self.llm = llm
        self.tools: List[BaseTool] = []
        self.short_term_memory = ShortTermMemory(window_size=15)  # 增加窗口大小
        self.long_term_memory = LongTermMemory()
        self.agent = None
        self.max_retries = 2
        self.on_tool_callback = on_tool_callback
        self.on_token_callback = on_token_callback
        self._last_output = ""  # 记住上一次输出，用于上下文

    def _get_llm(self):
        if self.llm:
            return self.llm
        from app.agents.custom_llm import MiMoChatOpenAI
        
        callbacks = []
        if self.on_token_callback:
            callbacks.append(TokenStreamingHandler(self.on_token_callback))
            
        return MiMoChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0.7,
            streaming=bool(self.on_token_callback),
            callbacks=callbacks
        )

    def _build_system_prompt(self) -> str:
        """构建系统提示词 - 子类应重写此方法"""
        return f"""你是一个专业的{self.agent_name}。

## 角色定位
你是一位经验丰富的专业人士，擅长为用户提供精准、实用的建议。

## 回复规范
1. **语言风格**：用自然流畅的中文回复，专业但不晦涩
2. **结构清晰**：使用Markdown格式（标题、列表、加粗）组织内容
3. **数据驱动**：基于工具返回的真实数据给出建议
4. **可操作性**：每条建议都要具体、可执行
5. **长度适中**：回复控制在300-800字，重点突出

## 输出格式要求
使用Markdown格式，结构如下：
- **核心结论**：1-2句话总结核心观点
- **详细分析**：分点列出，每点用加粗标题
- **行动建议**：具体可执行的步骤
- **注意事项**：风险提示或补充说明

## 多轮对话规则
1. 记住用户之前的问题和你的回答
2. 如果用户说"修改XX"或"换个说法"，只修改指定部分
3. 如果用户说"详细说说"或"展开讲讲"，对上一个话题深入
4. 支持局部修改：用户可以指定修改某一段或某一点
5. 保持连贯性：新回复要与之前的对话衔接

## 错误处理
- 如果工具调用失败，给出替代建议而非简单报错
- 如果数据不足，说明限制并给出基于经验的建议"""

    def build_agent(self):
        self.agent = create_agent(
            model=self._get_llm(),
            tools=self.tools,
            system_prompt=self._build_system_prompt()
        )
        return self.agent

    def _build_context(self, user_id: int, user_input: str) -> str:
        """构建上下文信息 - 增强版"""
        context_parts = []
        
        # 获取用户档案信息
        from app.models.profile import UserProfile
        from app import db
        
        try:
            db.session.rollback()
        except Exception:
            pass
        
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if profile:
            profile_info = []
            
            # 基本信息
            if profile.current_job_title:
                profile_info.append(f"当前职位: {profile.current_job_title}")
            if profile.work_experience is not None and profile.work_experience > 0:
                profile_info.append(f"工作年限: {profile.work_experience}年")
            if profile.education:
                edu_map = {"bachelor": "本科", "master": "硕士", "phd": "博士", "doctorate": "博士", 
                          "associate": "大专", "high_school": "高中"}
                profile_info.append(f"学历: {edu_map.get(profile.education, profile.education)}")
            if profile.major:
                profile_info.append(f"专业: {profile.major}")
            if profile.skills and len(profile.skills) > 0:
                profile_info.append(f"技能: {', '.join(profile.skills[:10])}")  # 限制长度
            
            # 求职意向
            if profile.target_job_title:
                profile_info.append(f"目标岗位: {profile.target_job_title}")
            if profile.target_jobs and len(profile.target_jobs) > 1:
                jobs_list = ", ".join([j.get("title", "") for j in profile.target_jobs[:5]])
                profile_info.append(f"历史目标岗位: {jobs_list}")
            if profile.target_industry:
                profile_info.append(f"目标行业: {profile.target_industry}")
            if profile.location_preference:
                profile_info.append(f"意向城市: {profile.location_preference}")
            if profile.target_salary_min or profile.target_salary_max:
                salary_min = int(profile.target_salary_min) if profile.target_salary_min else 0
                salary_max = int(profile.target_salary_max) if profile.target_salary_max else 0
                if salary_min > 0 or salary_max > 0:
                    profile_info.append(f"目标薪资: {salary_min}k-{salary_max}k")
            if profile.job_search_status:
                status_map = {"observing": "观望中", "employed": "在职看机会", 
                             "resigned": "已离职", "fresh": "应届生"}
                profile_info.append(f"求职状态: {status_map.get(profile.job_search_status, profile.job_search_status)}")
            if profile.work_preference:
                pref_map = {"remote": "远程", "onsite": "坐班", "hybrid": "混合", "flexible": "不限"}
                profile_info.append(f"工作偏好: {pref_map.get(profile.work_preference, profile.work_preference)}")
            if profile.company_type_preference:
                type_map = {"big_company": "大厂", "startup": "创业公司", "foreign": "外企", "flexible": "不限"}
                profile_info.append(f"公司类型偏好: {type_map.get(profile.company_type_preference, profile.company_type_preference)}")
            
            # 项目经历（只取前3个）
            if profile.projects and len(profile.projects) > 0:
                projects_desc = []
                for p in profile.projects[:3]:
                    desc = p.get("name", "")
                    if p.get("role"):
                        desc += f"（{p['role']}）"
                    if desc:
                        projects_desc.append(desc)
                if projects_desc:
                    profile_info.append(f"项目经历: {'; '.join(projects_desc)}")
            
            # 证书
            if profile.certifications and len(profile.certifications) > 0:
                profile_info.append(f"证书: {', '.join(profile.certifications[:5])}")
            
            # 副业信息
            if profile.available_hours_per_week:
                profile_info.append(f"每周可用时间: {profile.available_hours_per_week}小时")
            if profile.side_job_income_target:
                profile_info.append(f"副业月收入目标: {int(profile.side_job_income_target)}元")
            
            # 职业目标（截取前100字）
            if profile.career_goals:
                goals = profile.career_goals[:100] + "..." if len(profile.career_goals) > 100 else profile.career_goals
                profile_info.append(f"职业目标: {goals}")
            
            if profile_info:
                context_parts.append("【用户档案】\n" + "\n".join(profile_info))

        # 获取长期记忆（限制长度）
        long_term_context = self.long_term_memory.retrieve(user_id, user_input)
        if long_term_context:
            long_term_context = long_term_context[:500] + "..." if len(long_term_context) > 500 else long_term_context
            context_parts.append(f"【相关历史】\n{long_term_context}")

        # 获取短期对话历史（最近5轮）
        history_context = self.short_term_memory.get_context_string(user_id)
        if history_context:
            history_context = history_context[:500] + "..." if len(history_context) > 500 else history_context
            context_parts.append(f"【近期对话】\n{history_context}")
        
        # 添加上一次输出摘要（如果有）
        if self._last_output:
            last_summary = self._last_output[:200] + "..." if len(self._last_output) > 200 else self._last_output
            context_parts.append(f"【上次回复摘要】\n{last_summary}")
        
        return "\n\n".join(context_parts) if context_parts else ""

    def _validate_output(self, output: str) -> Dict[str, Any]:
        """验证输出质量 - 增强版，返回详细信息"""
        if not output:
            return {"ok": False, "score": 0, "issues": ["empty_output"]}
        
        issues = []
        score = 50  # 基础分
        
        # 长度检查
        if len(output) < 20:
            issues.append("too_short")
            score -= 30
        elif len(output) < 50:
            score -= 10
        elif len(output) > 100:
            score += 10
        elif len(output) > 300:
            score += 15
        
        # 错误关键词检查（短回复中的错误关键词扣分更多）
        error_keywords = ["抱歉", "无法", "失败", "错误", "不支持", "暂不支持"]
        error_count = sum(1 for kw in error_keywords if kw in output)
        if error_count > 0:
            if len(output) < 50:
                issues.append("contains_errors")
                score -= 25
            elif len(output) < 100:
                score -= 10
        
        # 格式化检查（Markdown格式加分）
        format_indicators = ["**", "- ", "1. ", "##", "###", "|"]
        format_count = sum(1 for indicator in format_indicators if indicator in output)
        if format_count > 0:
            score += min(format_count * 5, 20)
        
        # 内容相关性检查
        relevance_keywords = ["建议", "推荐", "分析", "总结", "方案", "策略", "路径", "方案"]
        relevance_count = sum(1 for kw in relevance_keywords if kw in output)
        if relevance_count > 0:
            score += min(relevance_count * 5, 15)
        
        # 限制分数范围
        score = max(0, min(100, score))
        
        return {
            "ok": score >= 35,
            "score": score,
            "issues": issues
        }

    def _format_output(self, output: str) -> str:
        """格式化输出 - 确保使用Markdown格式"""
        if not output:
            return output
        
        # 如果输出已经包含Markdown格式，直接返回
        if any(marker in output for marker in ["**", "- ", "1. ", "##", "###"]):
            return output
        
        # 尝试添加基本格式
        lines = output.split("\n")
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue
            
            # 检测是否是标题行（以冒号结尾的短行）
            if line.endswith("：") or line.endswith(":") and len(line) < 30:
                formatted_lines.append(f"**{line}**")
            # 检测是否是列表项（以数字开头）
            elif line[0].isdigit() and len(line) > 2 and line[1] in [".", "、", "）"]:
                formatted_lines.append(line)
            # 检测是否是列表项（以符号开头）
            elif line[0] in ["•", "·", "●", "○", "▪", "▫", "■", "□"]:
                formatted_lines.append(f"- {line[1:].strip()}")
            else:
                formatted_lines.append(line)
        
        return "\n".join(formatted_lines)

    def _get_friendly_error(self, error: str) -> str:
        """获取友好的错误提示"""
        error_str = str(error).lower()
        
        if "timeout" in error_str or "超时" in error_str:
            return "处理超时，请稍后重试。如果问题持续存在，可以尝试简化您的问题。"
        elif "rate_limit" in error_str or "限流" in error_str:
            return "当前请求较多，请稍后重试。"
        elif "connection" in error_str or "连接" in error_str:
            return "网络连接出现问题，请检查网络后重试。"
        elif "authentication" in error_str or "认证" in error_str:
            return "认证失败，请重新登录后重试。"
        else:
            return f"处理过程中遇到问题，请稍后重试。如果问题持续存在，请尝试换个方式描述您的需求。"

    def run(self, user_input: str, user_id: int = None) -> Dict[str, Any]:
        """执行Agent - 增强版，支持流式输出"""
        if not self.agent:
            self.build_agent()

        context = ""
        if user_id:
            context = self._build_context(user_id, user_input)

        full_input = user_input
        if context:
            full_input = f"【背景信息】\n{context}\n\n【用户问题】\n{user_input}"
        
        print(f"[BaseAgent] {self.agent_name} 开始执行，输入长度: {len(full_input)}")

        # 重试机制
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                print(f"[BaseAgent] {self.agent_name} 尝试 {attempt + 1}/{self.max_retries + 1}")
                
                # 发送进度更新
                if self.on_tool_callback:
                    self.on_tool_callback({
                        "type": "tool",
                        "title": f"{self.agent_name}正在思考",
                        "detail": f"第{attempt + 1}次尝试..." if attempt > 0 else "正在分析问题...",
                        "status": "running"
                    })
                
                # 使用stream模式实现真正的流式输出
                output = ""
                steps = []
                
                for chunk in self.agent.stream({
                    "messages": [{"role": "user", "content": full_input}]
                }):
                    if "messages" in chunk:
                        for msg in chunk["messages"]:
                            if hasattr(msg, "type") and msg.type == "ai":
                                content = getattr(msg, "content", "")
                                if content:
                                    output += content
                                    # 发送token到前端
                                    if self.on_token_callback:
                                        self.on_token_callback(content)
                            
                            if hasattr(msg, "type") and msg.type == "tool":
                                tool_step = {
                                    "action": msg.name if hasattr(msg, "name") else "tool",
                                    "output": msg.content[:200] if msg.content else ""
                                }
                                steps.append(tool_step)
                                
                                # 发送工具调用步骤
                                if self.on_tool_callback:
                                    self.on_tool_callback({
                                        "type": "tool",
                                        "title": f"调用工具: {msg.name if hasattr(msg, 'name') else 'tool'}",
                                        "detail": (msg.content[:100] if msg.content else "执行完成") + "...",
                                        "status": "completed"
                                    })
                
                print(f"[BaseAgent] {self.agent_name} 输出长度: {len(output)}")

                # 验证输出质量
                validation = self._validate_output(output)
                if not validation["ok"] and attempt < self.max_retries:
                    print(f"[BaseAgent] {self.agent_name} 输出质量不合格 (分数: {validation['score']})，重试")
                    last_error = f"输出质量不合格: {validation['issues']}"
                    continue

                # 格式化输出
                formatted_output = self._format_output(output)

                # 保存到记忆
                if user_id:
                    self.short_term_memory.add_message(user_id, "user", user_input)
                    if formatted_output:
                        self.short_term_memory.add_message(user_id, "assistant", formatted_output)
                        try:
                            self.long_term_memory.store(user_id, user_input, formatted_output)
                        except Exception as e:
                            print(f"[BaseAgent] 保存长期向量记忆失败 (可能是本地Ollama未启动或ChromaDB不可用): {e}")

                # 记住上一次输出
                self._last_output = formatted_output

                return {
                    "success": True,
                    "output": formatted_output or "处理完成，但未生成回复",
                    "intermediate_steps": steps,
                    "quality_score": validation["score"]
                }
            except ClientDisconnectedError as e:
                raise e
            except Exception as e:
                print(f"[BaseAgent] {self.agent_name} 异常: {str(e)}")
                import traceback
                traceback.print_exc()
                try:
                    from app import db
                    db.session.rollback()
                except Exception:
                    pass
                last_error = str(e)
                if attempt < self.max_retries:
                    continue
                
                # 所有重试都失败，返回友好错误
                friendly_error = self._get_friendly_error(last_error)
                return {"success": False, "error": friendly_error}

    def _register_tools(self):
        pass
