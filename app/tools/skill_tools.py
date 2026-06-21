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


@tool("skill_priority", return_direct=False)
def skill_priority(target_position: str, current_skills: List[str] = []) -> str:
    """按优先级排序需要学习的技能。输入目标职位和当前技能列表。"""
    from app.models.job import Job
    
    jobs = Job.query.filter(Job.title.contains(target_position)).all()
    if not jobs:
        return f"暂无 {target_position} 的技能数据"
    
    skill_count = {}
    skill_obj_map = {}
    for job in jobs:
        for js in job.skills.all():
            name = js.skill_name
            skill_count[name] = skill_count.get(name, 0) + 1
            if name not in skill_obj_map:
                skill_obj = Skill.query.filter(Skill.name == name).first()
                skill_obj_map[name] = skill_obj
    
    current_lower = [s.lower() for s in current_skills]
    missing_skills = {k: v for k, v in skill_count.items() if k.lower() not in current_lower}
    
    sorted_skills = sorted(missing_skills.items(), key=lambda x: x[1], reverse=True)
    
    output = f"【{target_position}】技能学习优先级:\n\n"
    output += "排序依据: 市场需求频率 × 学习难度\n\n"
    
    for i, (skill_name, count) in enumerate(sorted_skills[:10], 1):
        skill_obj = skill_obj_map.get(skill_name)
        months = skill_obj.learning_months if skill_obj else 2
        difficulty = skill_obj.difficulty_level if skill_obj else 3
        demand_ratio = count / len(jobs) * 100
        
        priority_score = demand_ratio / max(difficulty, 1)
        
        priority_label = "高" if priority_score > 30 else "中" if priority_score > 15 else "低"
        
        output += f"{i}. {skill_name}\n"
        output += f"   需求频率: {count}/{len(jobs)}个职位要求 ({demand_ratio:.0f}%)\n"
        output += f"   学习难度: {'★' * difficulty}\n"
        output += f"   学习时间: {months}个月\n"
        output += f"   优先级: {priority_label}\n\n"
    
    if sorted_skills:
        top3 = [s[0] for s in sorted_skills[:3]]
        output += f"建议优先学习: {', '.join(top3)}\n"
        output += "这3个技能覆盖了最多职位的要求\n"
    
    return output


@tool("generate_learning_plan", return_direct=False)
def generate_learning_plan(skill: str, current_level: str = "beginner", target_level: str = "intermediate", hours_per_week: int = 10) -> str:
    """生成学习计划。输入技能、当前水平、目标水平、每周学习时间。"""
    try:
        from langchain_openai import ChatOpenAI
        from flask import current_app
        
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0.7
        )
        
        prompt = f"""请为以下技能生成详细的学习计划：

技能：{skill}
当前水平：{current_level}
目标水平：{target_level}
每周学习时间：{hours_per_week}小时

请提供：
1. 学习路径规划（分阶段）
2. 每个阶段的学习内容
3. 推荐的学习资源（书籍、课程、网站）
4. 实践项目建议
5. 学习进度检查点
6. 常见问题及解决方案

请用Markdown格式输出，确保计划可执行。"""

        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"生成学习计划失败: {str(e)}"


@tool("skill_market_value", return_direct=False)
def skill_market_value(skill: str, city: str = "全国") -> str:
    """查询技能的市场价值。输入技能名称和城市。"""
    try:
        from app.models.job import Job, JobSkill
        from app import db
        
        db.session.rollback()
        
        # 查找包含该技能的职位
        jobs_with_skill = []
        all_jobs = Job.query.all()
        
        for job in all_jobs:
            skills = [s.skill_name.lower() for s in job.skills.all()]
            if skill.lower() in skills:
                jobs_with_skill.append(job)
        
        if not jobs_with_skill:
            return f"暂无{skill}相关的职位数据"
        
        # 统计薪资
        salaries = [j.salary_avg for j in jobs_with_skill if j.salary_avg]
        avg_salary = sum(salaries) // len(salaries) if salaries else 0
        min_salary = min(salaries) if salaries else 0
        max_salary = max(salaries) if salaries else 0
        
        # 统计城市分布
        cities = {}
        for job in jobs_with_skill:
            cities[job.city] = cities.get(job.city, 0) + 1
        
        sorted_cities = sorted(cities.items(), key=lambda x: x[1], reverse=True)[:5]
        
        output = f"【{skill}】市场价值分析:\n\n"
        output += f"数据样本: {len(jobs_with_skill)}个职位\n\n"
        
        output += "薪资水平:\n"
        output += f"  - 平均薪资: {avg_salary//1000}K\n"
        output += f"  - 最低薪资: {min_salary//1000}K\n"
        output += f"  - 最高薪资: {max_salary//1000}K\n\n"
        
        output += "热门城市:\n"
        for city, count in sorted_cities:
            output += f"  - {city}: {count}个职位\n"
        
        return output
    except Exception as e:
        return f"查询技能市场价值失败: {str(e)}"


def get_skill_tools():
    return [analyze_skill_gap, recommend_learning_path, skill_priority, generate_learning_plan, skill_market_value]
