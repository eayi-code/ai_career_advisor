from typing import List, Dict, Any
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from flask import current_app
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory


class BaseAgent:
    """智能体基类，实现ReAct推理模式"""

    def __init__(self, agent_name: str, llm=None):
        self.agent_name = agent_name
        self.llm = llm
        self.tools: List[BaseTool] = []
        self.short_term_memory = ShortTermMemory(window_size=10)
        self.long_term_memory = LongTermMemory()
        self.agent = None

    def _get_llm(self):
        if self.llm:
            return self.llm
        return ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0.7
        )

    def _build_system_prompt(self) -> str:
        return f"""你是一个专业的{self.agent_name}。

回复要求:
1. 用自然流畅的中文回复，像朋友对话一样
2. 不要使用任何特殊符号，如 #、*、-、emoji、> 等
3. 不要使用markdown格式，直接用纯文本
4. 回答要简洁有条理，分段落但不用符号标记
5. 基于工具返回的数据给出实用建议
6. 如果没有数据就直接说明"""

    def build_agent(self):
        self.agent = create_agent(
            model=self._get_llm(),
            tools=self.tools,
            system_prompt=self._build_system_prompt()
        )
        return self.agent

    def run(self, user_input: str, user_id: int = None) -> Dict[str, Any]:
        if not self.agent:
            self.build_agent()

        context = ""
        if user_id:
            context = self.long_term_memory.retrieve(user_id, user_input)
            history_context = self.short_term_memory.get_context_string(user_id)
            if history_context:
                context = f"对话历史:\n{history_context}\n\n{context}"

        full_input = user_input
        if context:
            full_input = f"相关背景信息:\n{context}\n\n用户问题: {user_input}"

        try:
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
                        steps.append({
                            "action": msg.name if hasattr(msg, "name") else "tool",
                            "output": msg.content[:200] if msg.content else ""
                        })

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
            return {"success": False, "error": str(e)}

    def _register_tools(self):
        pass
