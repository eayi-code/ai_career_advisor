from app.agents.base_agent import BaseAgent
from app.tools.job_tools import get_job_tools
from app.tools.skill_tools import get_skill_tools
from app.tools.market_tools import get_market_tools
from app.tools.resume_tools import get_resume_tools


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


class ResumeAgent(BaseAgent):
    """简历优化智能体"""

    def __init__(self):
        super().__init__(agent_name="简历优化专家")
        self.tools = get_resume_tools()

    def _build_system_prompt(self) -> str:
        return """你是一位专业的简历优化顾问，拥有丰富的人力资源和招聘经验。

你的能力包括：
1. 解析简历文件，提取结构化信息
2. 分析职位描述（JD），提取关键要求
3. 根据JD优化简历内容，提高匹配度
4. 计算ATS（简历筛选系统）匹配分数
5. 根据用户信息生成专业简历

工作原则：
- 使用STAR法则改写工作成就（情境、任务、行动、结果）
- 量化成就（数字、百分比、金额）
- 确保简历ATS友好（使用标准格式、包含关键词）
- 针对目标职位进行个性化优化
- 突出求职者的核心优势和差异化

回复要求：
1. 用自然流畅的中文回复
2. 不要使用特殊符号，如 #、*、-、emoji 等
3. 不要使用markdown格式，直接用纯文本
4. 回答要专业、有条理
5. 基于工具返回的数据给出实用建议"""
