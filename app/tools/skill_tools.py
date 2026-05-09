from langchain.tools import tool
from typing import List
from app.models.skill import Skill, LearningResource


@tool("analyze_skill_gap", return_direct=False)
def analyze_skill_gap(current_skills: List[str], target_position: str) -> str:
    """分析当前技能与目标职位的差距。输入当前技能列表和目标职位。"""
    from app.models.job import Job, JobSkill

    jobs = Job.query.filter(Job.title.contains(target_position)).all()
    if not jobs:
        return f"暂无 {target_position} 的技能要求数据"

    all_required = set()
    for job in jobs:
        for js in job.skills.all():
            all_required.add(js.skill_name)

    current_lower = [s.lower() for s in current_skills]
    missing = [s for s in all_required if s.lower() not in current_lower]
    matched = [s for s in all_required if s.lower() in current_lower]

    output = f"【{target_position}】技能差距分析:\n\n"

    if matched:
        output += "已掌握的技能:\n"
        for s in matched:
            output += f"  - {s}\n"
        output += "\n"

    if missing:
        output += "需要学习的技能:\n"
        for s in missing:
            skill_obj = Skill.query.filter(Skill.name == s).first()
            if skill_obj:
                months = skill_obj.learning_months or 2
                output += f"  - {s} (预计学习时间: {months}个月)\n"
            else:
                output += f"  - {s}\n"

    gap_score = len(missing) / max(len(all_required), 1) * 100
    output += f"\n技能匹配度: {100 - gap_score:.0f}%"

    return output


@tool("recommend_learning_path", return_direct=False)
def recommend_learning_path(skill: str, current_level: str = "beginner") -> str:
    """推荐学习路径。输入技能名称和当前水平(beginner/intermediate)。"""
    skill_obj = Skill.query.filter(Skill.name.contains(skill)).first()

    if not skill_obj:
        return f"暂无 {skill} 的学习路径推荐"

    resources = skill_obj.resources.all()

    output = f"【{skill_obj.name}】学习路径:\n\n"
    output += f"难度等级: {'★' * skill_obj.difficulty_level}\n"
    output += f"市场需求: {skill_obj.market_demand}\n"
    output += f"预计学习时间: {skill_obj.learning_months}个月\n\n"

    if resources:
        output += "推荐学习资源:\n\n"
        for i, res in enumerate(resources, 1):
            output += f"{i}. {res.title}\n"
            output += f"   类型: {res.type}\n"
            output += f"   难度: {res.difficulty}\n"
            output += f"   时长: {res.duration}\n\n"

    return output


def get_skill_tools():
    return [analyze_skill_gap, recommend_learning_path]
