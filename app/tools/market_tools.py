from langchain.tools import tool
from typing import List
from app.models.side_job import SideJob


@tool("search_side_jobs", return_direct=False)
def search_side_jobs(skills: List[str], hours_per_week: int, investment: int = 0) -> str:
    """搜索适合的副业机会。输入技能列表、每周可用时间、启动资金。"""
    query = SideJob.query.filter(
        SideJob.hours_per_week <= hours_per_week,
        SideJob.startup_cost <= investment
    )

    side_jobs = query.all()

    if not side_jobs:
        return "根据您的条件，建议先提升技能或增加可用时间"

    matched = []
    for job in side_jobs:
        required = job.skills_required or []
        if any(s.lower() in [r.lower() for r in required] for s in skills):
            matched.append(job)

    if not matched:
        matched = side_jobs[:5]

    output = f"找到 {len(matched)} 个适合的副业:\n\n"
    for job in matched:
        output += f"{job.title}\n"
        output += f"  预计收入: {job.income_min}-{job.income_max}元/月\n"
        output += f"  时间投入: 每周{job.hours_per_week}小时\n"
        output += f"  启动成本: {job.startup_cost}元\n"
        output += f"  难度等级: {'★' * job.difficulty_level}\n"
        output += f"  平台: {', '.join(job.platforms or [])}\n\n"

    return output


@tool("calculate_side_job_roi", return_direct=False)
def calculate_side_job_roi(monthly_income: int, hours_per_week: int, startup_cost: int = 0) -> str:
    """计算副业投资回报率。输入预计月收入、每周时间、启动成本。"""
    hourly_rate = monthly_income / (hours_per_week * 4)
    yearly_income = monthly_income * 12

    result = f"副业ROI分析:\n\n"
    result += f"时薪: {hourly_rate:.1f}元/小时\n"
    result += f"年收入: {yearly_income}元\n"

    if startup_cost > 0:
        months_to_break_even = startup_cost / monthly_income
        result += f"回本周期: {months_to_break_even:.1f}个月\n"
        result += f"投入产出比: 1:{yearly_income / startup_cost:.1f}\n"
    else:
        result += "无需启动资金，纯收益\n"

    return result


def get_market_tools():
    return [search_side_jobs, calculate_side_job_roi]
