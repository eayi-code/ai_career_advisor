from langchain.tools import tool
from typing import List, Optional
from app.models.job import Job, JobSkill


@tool("search_jobs", return_direct=False)
def search_jobs(keywords: List[str], location: str = "全国", salary_min: Optional[int] = None) -> str:
    """搜索职位信息。输入关键词列表、工作地点、最低薪资。"""
    try:
        from app import db
        db.session.rollback()
        
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
            try:
                skills = [s.skill_name for s in job.skills.all()]
            except Exception:
                skills = []
            result += f"{job.title} ({job.industry})\n"
            result += f"  薪资: {job.salary_min//1000 if job.salary_min else 0}k-{job.salary_max//1000 if job.salary_max else 0}k\n"
            result += f"  地点: {job.city}\n"
            result += f"  经验: {job.experience_years}年\n"
            if skills:
                result += f"  技能: {', '.join(skills)}\n"
            result += "\n"

        return result
    except Exception as e:
        return f"搜索职位失败: {str(e)}"


@tool("query_salary", return_direct=False)
def query_salary(job_title: str, experience_years: int = 0) -> str:
    """查询特定职位的薪资水平。输入职位名称和工作年限。"""
    try:
        from app import db
        db.session.rollback()
        
        jobs = Job.query.filter(Job.title.contains(job_title)).all()

        if not jobs:
            return f"暂无 {job_title} 的薪资数据"

        result = f"{job_title} 薪资水平:\n\n"
        for job in jobs:
            result += f"{job.title}:\n"
            result += f"  薪资范围: {job.salary_min//1000 if job.salary_min else 0}k-{job.salary_max//1000 if job.salary_max else 0}k\n"
            result += f"  平均薪资: {job.salary_avg//1000 if job.salary_avg else 0}k\n"
            result += f"  经验要求: {job.experience_years}年\n"
            result += f"  学历要求: {job.education_requirement or '不限'}\n"
            result += f"  城市: {job.city}\n\n"

        return result
    except Exception as e:
        return f"查询薪资失败: {str(e)}"


@tool("compare_jobs", return_direct=False)
def compare_jobs(job_titles: List[str]) -> str:
    """对比多个职位的薪资、前景、要求。输入职位名称列表。"""
    try:
        results = []
        
        for title in job_titles:
            jobs = Job.query.filter(Job.title.contains(title)).all()
            if not jobs:
                results.append(f"【{title}】暂无数据")
                continue
            
            salaries = [j.salary_avg for j in jobs if j.salary_avg]
            avg_salary = sum(salaries) // len(salaries) if salaries else 0
            
            all_skills = set()
            for job in jobs:
                for s in job.skills.all():
                    all_skills.add(s.skill_name)
            
            min_exp = min(j.experience_years for j in jobs) if jobs else 0
            max_exp = max(j.experience_years for j in jobs) if jobs else 0
            
            cities = set(j.city for j in jobs)
            
            results.append({
                "title": title,
                "count": len(jobs),
                "avg_salary": avg_salary,
                "salary_range": f"{min(j.salary_min for j in jobs)//1000}k-{max(j.salary_max for j in jobs)//1000}k",
                "experience": f"{min_exp}-{max_exp}年",
                "skills": list(all_skills)[:8],
                "cities": list(cities)
            })
        
        output = "职位对比分析:\n\n"
        for r in results:
            if isinstance(r, str):
                output += r + "\n\n"
            else:
                output += f"【{r['title']}】\n"
                output += f"  平均薪资: {r['avg_salary']//1000}k\n"
                output += f"  薪资范围: {r['salary_range']}\n"
                output += f"  经验要求: {r['experience']}\n"
                output += f"  核心技能: {', '.join(r['skills'][:5])}\n"
                output += f"  招聘城市: {', '.join(r['cities'])}\n"
                output += f"  职位数量: {r['count']}个\n\n"
        
        if len(results) >= 2 and all(isinstance(r, dict) for r in results):
            best_salary = max(results, key=lambda x: x['avg_salary'])
            output += f"薪资最高: {best_salary['title']} (平均{best_salary['avg_salary']//1000}k)\n"
            
            all_skills = set()
            for r in results:
                all_skills.update(r['skills'])
            output += f"共同技能要求: {', '.join(list(all_skills)[:5])}\n"
        
        return output
    except Exception as e:
        return f"对比职位失败: {str(e)}"


@tool("save_target_job", return_direct=False)
def save_target_job(job_title: str) -> str:
    """保存用户的目标岗位到档案。当用户确定了目标岗位时调用此工具。支持保存多个岗位。"""
    try:
        from flask_login import current_user
        from app.models.profile import UserProfile
        from app import db
        from datetime import datetime
        
        if not current_user.is_authenticated:
            return "用户未登录，无法保存目标岗位"
        
        try:
            db.session.rollback()
            profile = UserProfile.query.filter_by(user_id=current_user.id).first()
            if not profile:
                profile = UserProfile(user_id=current_user.id)
                db.session.add(profile)
            
            # 更新当前选中的目标岗位
            profile.target_job_title = job_title
            
            # 添加到目标岗位列表
            target_jobs = profile.target_jobs or []
            
            # 检查是否已存在
            existing_titles = [j.get("title") for j in target_jobs]
            if job_title not in existing_titles:
                target_jobs.append({
                    "title": job_title,
                    "added_at": datetime.utcnow().isoformat()
                })
                profile.target_jobs = target_jobs
            
            db.session.commit()
            return f"已将目标岗位「{job_title}」保存到您的档案（共{len(target_jobs)}个目标岗位）"
        except Exception as e:
            db.session.rollback()
            # 尝试重新连接
            try:
                db.session.remove()
                profile = UserProfile.query.filter_by(user_id=current_user.id).first()
                if profile:
                    profile.target_job_title = job_title
                    db.session.commit()
                    return f"已将目标岗位「{job_title}」保存到您的档案"
            except:
                pass
            return f"保存目标岗位失败: {str(e)}"
    except Exception as e:
        return f"保存目标岗位失败: {str(e)}"


@tool("update_user_profile", return_direct=False)
def update_user_profile(field: str, value: str) -> str:
    """更新用户档案信息。支持的字段：skills（技能）、work_experience（工作年限）、education（学历）、major（专业）、target_industry（目标行业）、location_preference（意向城市）"""
    try:
        from flask_login import current_user
        from app.models.profile import UserProfile
        from app import db
        
        if not current_user.is_authenticated:
            return "用户未登录，无法更新档案"
        
        db.session.rollback()
        profile = UserProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            profile = UserProfile(user_id=current_user.id)
            db.session.add(profile)
        
        # 根据字段类型更新
        if field == "skills":
            # 技能是列表，需要追加
            current_skills = profile.skills or []
            new_skills = [s.strip() for s in value.split(",")]
            merged_skills = list(set(current_skills + new_skills))
            profile.skills = merged_skills
            db.session.commit()
            return f"已更新技能：{', '.join(merged_skills)}"
        elif field == "work_experience":
            profile.work_experience = int(value)
            db.session.commit()
            return f"已更新工作年限：{value}年"
        elif field == "education":
            profile.education = value
            db.session.commit()
            return f"已更新学历：{value}"
        elif field == "major":
            profile.major = value
            db.session.commit()
            return f"已更新专业：{value}"
        elif field == "target_industry":
            profile.target_industry = value
            db.session.commit()
            return f"已更新目标行业：{value}"
        elif field == "location_preference":
            profile.location_preference = value
            db.session.commit()
            return f"已更新意向城市：{value}"
        elif field == "current_job_title":
            profile.current_job_title = value
            db.session.commit()
            return f"已更新当前职位：{value}"
        else:
            return f"不支持的字段：{field}"
    except Exception as e:
        return f"更新档案失败: {str(e)}"


def get_job_tools():
    return [search_jobs, query_salary, compare_jobs, save_target_job, update_user_profile]
