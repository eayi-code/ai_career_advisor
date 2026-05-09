from typing import Dict, Any
from app.agents.career_agent import CareerAgent, SkillAgent, SideJobAgent
from app.memory.long_term import LongTermMemory


class AgentOrchestrator:
    """多智能体编排器"""

    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.memory = LongTermMemory()
        self._initialize_agents()

    def _initialize_agents(self):
        self.agents["career"] = CareerAgent()
        self.agents["skill"] = SkillAgent()
        self.agents["side_job"] = SideJobAgent()

    def _classify_intent(self, user_input: str) -> str:
        intent_keywords = {
            "career": ["职业", "工作", "岗位", "求职", "面试", "offer", "公司"],
            "side_job": ["副业", "兼职", "赚钱", "额外收入", "自由职业"],
            "skill": ["技能", "学习", "提升", "差距", "培训", "课程"]
        }

        user_input_lower = user_input.lower()
        scores = {}
        for agent_name, keywords in intent_keywords.items():
            score = sum(1 for kw in keywords if kw in user_input_lower)
            if score > 0:
                scores[agent_name] = score

        return max(scores, key=scores.get) if scores else "career"

    def process(self, user_input: str, user_id: int = None, force_agent: str = None) -> Dict[str, Any]:
        agent_name = force_agent or self._classify_intent(user_input)

        if agent_name not in self.agents:
            return {"success": False, "error": f"未知的Agent类型: {agent_name}"}

        result = self.agents[agent_name].run(user_input, user_id)
        result["agent_used"] = agent_name
        return result

    def get_agent_status(self) -> Dict[str, Any]:
        return {
            name: {
                "name": agent.agent_name,
                "tools": [t.name for t in agent.tools]
            }
            for name, agent in self.agents.items()
        }
