from typing import Dict, Any
from app.agents.career_agent import CareerAgent, SkillAgent, SideJobAgent, ResumeAgent
from app.memory.long_term import LongTermMemory
from langchain_openai import ChatOpenAI
from flask import current_app


class AgentOrchestrator:
    """多智能体编排器 - 混合意图识别"""

    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.memory = LongTermMemory()
        self._initialize_agents()

    def _initialize_agents(self):
        self.agents["career"] = CareerAgent()
        self.agents["skill"] = SkillAgent()
        self.agents["side_job"] = SideJobAgent()
        self.agents["resume"] = ResumeAgent()

    def _classify_intent_keywords(self, user_input: str) -> tuple[str, float]:
        """关键词匹配，返回 (意图, 置信度)"""
        intent_keywords = {
            "career": {
                "high": ["职业", "工作", "岗位", "求职", "面试", "offer", "公司", "就业", "全职"],
                "medium": ["转行", "找工作", "招聘", "入职", "投递", "应聘"],
                "low": ["发展", "前景", "规划", "方向"]
            },
            "side_job": {
                "high": ["副业", "兼职", "赚钱", "额外收入", "自由职业", "接单"],
                "medium": ["外快", "第二职业", "斜杠", "远程工作", "居家办公"],
                "low": ["被动收入", "投资", "理财"]
            },
            "skill": {
                "high": ["技能", "学习", "提升", "差距", "培训", "课程", "学什么"],
                "medium": ["能力", "技术栈", "知识", "入门", "进阶", "教程"],
                "low": ["成长", "进步", "精通"]
            },
            "resume": {
                "high": ["简历", "resume", "CV", "履历", "求职信", "cover letter"],
                "medium": ["优化简历", "修改简历", "简历模板", "ATS", "简历评分", "简历解析"],
                "low": ["写简历", "改简历", "简历建议"]
            }
        }

        user_input_lower = user_input.lower()
        scores = {}
        
        for agent_name, keywords in intent_keywords.items():
            score = 0
            for kw in keywords["high"]:
                if kw in user_input_lower:
                    score += 3
            for kw in keywords["medium"]:
                if kw in user_input_lower:
                    score += 2
            for kw in keywords["low"]:
                if kw in user_input_lower:
                    score += 1
            scores[agent_name] = score

        total_score = sum(scores.values())
        if total_score == 0:
            return "career", 0.0
        
        best_agent = max(scores, key=scores.get)
        confidence = scores[best_agent] / total_score if total_score > 0 else 0
        
        return best_agent, confidence

    def _classify_intent_llm(self, user_input: str) -> str:
        """LLM分类，用于关键词不确定时"""
        try:
            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0
            )
            
            prompt = f"""请判断以下用户问题属于哪个类别，只返回类别名称，不要返回其他内容。

类别：
- career: 职业规划、求职、工作岗位、公司、面试、薪资等
- skill: 技能学习、能力提升、培训课程、技能差距等
- side_job: 副业、兼职、额外收入、自由职业等
- resume: 简历优化、简历生成、简历解析、ATS评分、JD分析等

用户问题：{user_input}

类别："""
            
            response = llm.invoke(prompt)
            result = response.content.strip().lower()
            
            if result in ["career", "skill", "side_job", "resume"]:
                return result
            return "career"
            
        except Exception as e:
            print(f"LLM分类失败: {e}")
            return "career"

    def _classify_intent(self, user_input: str) -> str:
        """混合意图识别：关键词优先，低置信度时用LLM"""
        agent_name, confidence = self._classify_intent_keywords(user_input)
        
        # 置信度阈值：0.6以上直接使用
        if confidence >= 0.6:
            return agent_name
        
        # 置信度低，调用LLM分类
        return self._classify_intent_llm(user_input)

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
