from app.agents.base_agent import BaseAgent
from app.tools.job_tools import get_job_tools
from app.tools.skill_tools import get_skill_tools
from app.tools.market_tools import get_market_tools


class CareerAgent(BaseAgent):
    """职业规划智能体"""

    def __init__(self):
        super().__init__(agent_name="职业规划顾问")
        self.tools = get_job_tools()


class SkillAgent(BaseAgent):
    """技能分析智能体"""

    def __init__(self):
        super().__init__(agent_name="技能发展顾问")
        self.tools = get_skill_tools()


class SideJobAgent(BaseAgent):
    """副业分析智能体"""

    def __init__(self):
        super().__init__(agent_name="副业规划专家")
        self.tools = get_market_tools()
