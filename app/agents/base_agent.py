from typing import List, Dict, Any
from langchain.agents import create_agent
from langchain.tools import BaseTool
from flask import current_app
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory


class BaseAgent:
    """智能体基类，实现ReAct推理模式"""

    def __init__(self, agent_name: str, llm=None, on_tool_callback=None):
        self.agent_name = agent_name
        self.llm = llm
        self.tools: List[BaseTool] = []
        self.short_term_memory = ShortTermMemory(window_size=10)
        self.long_term_memory = LongTermMemory()
        self.agent = None
        self.max_retries = 2
        self.on_tool_callback = on_tool_callback  # 工具调用回调函数

    def _get_llm(self):
        if self.llm:
            return self.llm
        from app.agents.custom_llm import MiMoChatOpenAI
        return MiMoChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0.7
        )

    def _build_system_prompt(self) -> str:
        return f"""你是一个专业的{self.agent_name}。

回复要求:
1. 用自然流畅的中文回复，像朋友对话一样
2. 回答要简洁有条理，分段落但不用符号标记
3. 基于工具返回的数据给出实用建议
4. 如果没有数据就直接说明

多轮对话规则:
1. 记住用户之前的问题和你的回答
2. 如果用户说"修改XX"或"换个说法"，只修改指定部分，其他保持不变
3. 如果用户说"详细说说"或"展开讲讲"，对上一个话题进行深入
4. 如果用户追问，基于之前的回答进行补充，不要重复
5. 支持局部修改：用户可以指定修改某一段或某一点"""

    def build_agent(self):
        self.agent = create_agent(
            model=self._get_llm(),
            tools=self.tools,
            system_prompt=self._build_system_prompt()
        )
        return self.agent

    def _build_context(self, user_id: int, user_input: str) -> str:
        """构建上下文信息"""
        context = ""
        
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
            if profile.work_experience:
                profile_info.append(f"工作年限: {profile.work_experience}年")
            if profile.education:
                edu_map = {"bachelor": "本科", "master": "硕士", "doctorate": "博士", "associate": "大专", "high_school": "高中"}
                profile_info.append(f"学历: {edu_map.get(profile.education, profile.education)}")
            if profile.major:
                profile_info.append(f"专业: {profile.major}")
            if profile.skills:
                profile_info.append(f"技能: {', '.join(profile.skills)}")
            
            # 求职意向
            if profile.target_job_title:
                profile_info.append(f"当前选中目标岗位: {profile.target_job_title}")
            if profile.target_jobs and len(profile.target_jobs) > 1:
                jobs_list = ", ".join([j.get("title", "") for j in profile.target_jobs])
                profile_info.append(f"所有目标岗位: {jobs_list}")
            if profile.target_industry:
                profile_info.append(f"目标行业: {profile.target_industry}")
            if profile.location_preference:
                profile_info.append(f"意向城市: {profile.location_preference}")
            if profile.target_salary_min or profile.target_salary_max:
                salary_info = f"目标薪资: {profile.target_salary_min or 0}k-{profile.target_salary_max or 0}k"
                profile_info.append(salary_info)
            if profile.job_search_status:
                status_map = {"observing": "观望中", "employed": "在职看机会", "resigned": "已离职", "fresh": "应届生"}
                profile_info.append(f"求职状态: {status_map.get(profile.job_search_status, profile.job_search_status)}")
            if profile.work_preference:
                pref_map = {"remote": "远程", "onsite": "坐班", "hybrid": "混合", "flexible": "不限"}
                profile_info.append(f"工作偏好: {pref_map.get(profile.work_preference, profile.work_preference)}")
            if profile.company_type_preference:
                type_map = {"big_company": "大厂", "startup": "创业公司", "foreign": "外企", "flexible": "不限"}
                profile_info.append(f"公司类型偏好: {type_map.get(profile.company_type_preference, profile.company_type_preference)}")
            
            # 项目经历
            if profile.projects:
                projects_desc = []
                for p in profile.projects:
                    desc = p.get("name", "")
                    if p.get("role"):
                        desc += f"（{p['role']}）"
                    if desc:
                        projects_desc.append(desc)
                if projects_desc:
                    profile_info.append(f"项目经历: {'; '.join(projects_desc)}")
            
            # 证书
            if profile.certifications:
                profile_info.append(f"证书: {', '.join(profile.certifications)}")
            
            # 副业信息
            if profile.available_hours_per_week:
                profile_info.append(f"每周可用时间: {profile.available_hours_per_week}小时")
            if profile.side_job_income_target:
                profile_info.append(f"副业月收入目标: {profile.side_job_income_target}元")
            
            # 职业目标
            if profile.career_goals:
                profile_info.append(f"职业目标: {profile.career_goals}")
            
            if profile_info:
                context = "用户档案:\n" + "\n".join(profile_info)

        # 获取长期记忆
        long_term_context = self.long_term_memory.retrieve(user_id, user_input)
        if long_term_context:
            context = f"{context}\n\n相关历史记录:\n{long_term_context}" if context else f"相关历史记录:\n{long_term_context}"

        # 获取短期对话历史
        history_context = self.short_term_memory.get_context_string(user_id)
        if history_context:
            context = f"{context}\n\n近期对话:\n{history_context}" if context else f"近期对话:\n{history_context}"
        
        return context

    def _validate_output(self, output: str) -> bool:
        """验证输出质量"""
        if not output or len(output) < 10:
            return False
        # 检查是否包含错误关键词
        error_keywords = ["抱歉", "无法", "失败", "错误"]
        if any(kw in output for kw in error_keywords) and len(output) < 50:
            return False
        return True

    def run(self, user_input: str, user_id: int = None) -> Dict[str, Any]:
        if not self.agent:
            self.build_agent()

        context = ""
        if user_id:
            context = self._build_context(user_id, user_input)

        full_input = user_input
        if context:
            full_input = f"背景信息:\n{context}\n\n用户问题: {user_input}"
        
        print(f"[BaseAgent] {self.agent_name} 开始执行，输入长度: {len(full_input)}")

        # 重试机制
        for attempt in range(self.max_retries + 1):
            try:
                print(f"[BaseAgent] {self.agent_name} 尝试 {attempt + 1}/{self.max_retries + 1}")
                
                # 发送进度更新
                if self.on_tool_callback:
                    self.on_tool_callback({
                        "type": "tool",
                        "title": f"{self.agent_name}正在执行",
                        "detail": "正在调用工具...",
                        "status": "running"
                    })
                
                result = self.agent.invoke({
                    "messages": [{"role": "user", "content": full_input}]
                })

                output = ""
                steps = []
                if "messages" in result:
                    for msg in result["messages"]:
                        if hasattr(msg, "type") and msg.type == "ai":
                            if msg.content:
                                output = msg.content
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
                                    "title": f"工具调用: {msg.name if hasattr(msg, 'name') else 'tool'}",
                                    "detail": (msg.content[:100] if msg.content else "执行完成") + "...",
                                    "status": "completed"
                                })
                
                if not output and "messages" in result:
                    for msg in reversed(result["messages"]):
                        if hasattr(msg, "type") and msg.type == "ai":
                            content = getattr(msg, "content", "")
                            if content:
                                output = content
                                break
                
                print(f"[BaseAgent] {self.agent_name} 输出长度: {len(output)}")

                # 验证输出质量
                if not self._validate_output(output) and attempt < self.max_retries:
                    print(f"[BaseAgent] {self.agent_name} 输出质量不合格，重试")
                    continue

                if user_id:
                    self.short_term_memory.add_message(user_id, "user", user_input)
                    if output:
                        self.short_term_memory.add_message(user_id, "assistant", output)
                        self.long_term_memory.store(user_id, user_input, output)

                return {
                    "success": True,
                    "output": output or "处理完成，但未生成回复",
                    "intermediate_steps": steps
                }
            except Exception as e:
                print(f"[BaseAgent] {self.agent_name} 异常: {str(e)}")
                import traceback
                traceback.print_exc()
                if attempt < self.max_retries:
                    continue
                return {"success": False, "error": str(e)}

    def _register_tools(self):
        pass
