from langchain.tools import tool
from typing import List, Optional
from app.models.job import Job, JobSkill


@tool("search_jobs", return_direct=False)
def search_jobs(keywords: List[str], location: str = "全国", salary_min: Optional[int] = None) -> str:
    """搜索职位信息。输入关键词列表、工作地点、最低薪资。"""
    query = Job.query

    if location and location != "全国":
        query = query.filter(Job.city == location)

    if salary_min:
        query = query.filter(Job.salary_min >= salary_min)

    if keywords:
        keyword_filters = []
        for kw in keywords:
            keyword_filters.append(Job.title.contains(kw))
            keyword_filters.append(Job.industry.contains(kw))
            keyword_filters.append(Job.description.contains(kw))
        from sqlalchemy import or_
        query = query.filter(or_(*keyword_filters))

    jobs = query.limit(10).all()

    if not jobs:
        return "未找到匹配的职位，建议扩大搜索范围或尝试其他关键词"

    result = f"找到 {len(jobs)} 个匹配职位:\n\n"
    for job in jobs:
        skills = [s.skill_name for s in job.skills.limit(5).all()]
        result += f"{job.title} ({job.industry})\n"
        result += f"  薪资: {job.salary_min//1000}k-{job.salary_max//1000}k\n"
        result += f"  地点: {job.city}\n"
        result += f"  经验: {job.experience_years}年\n"
        result += f"  技能: {', '.join(skills)}\n\n"

    return result


@tool("query_salary", return_direct=False)
def query_salary(job_title: str, experience_years: int = 0) -> str:
    """查询特定职位的薪资水平。输入职位名称和工作年限。"""
    jobs = Job.query.filter(Job.title.contains(job_title)).all()

    if not jobs:
        return f"暂无 {job_title} 的薪资数据"

    result = f"{job_title} 薪资水平:\n\n"
    for job in jobs:
        result += f"{job.title}:\n"
        result += f"  薪资范围: {job.salary_min//1000}k-{job.salary_max//1000}k\n"
        result += f"  平均薪资: {job.salary_avg//1000}k\n"
        result += f"  经验要求: {job.experience_years}年\n"
        result += f"  学历要求: {job.education_requirement}\n"
        result += f"  城市: {job.city}\n\n"

    return result


def get_job_tools():
    return [search_jobs, query_salary]
