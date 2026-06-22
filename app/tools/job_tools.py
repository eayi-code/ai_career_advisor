from langchain.tools import tool
from typing import List, Optional, Dict, Any
from app.models.job import Job, JobSkill
import json


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


@tool("fetch_job_from_url", return_direct=False)
def fetch_job_from_url(url: str) -> str:
    """从职位链接抓取职位信息。输入职位页面的URL地址。"""
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse
        import ipaddress
        import socket

        # ── SSRF 防护：验证目标地址不是内网 ──
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return "抓取失败：仅支持 http 和 https 协议"

        hostname = parsed.hostname
        if not hostname:
            return "抓取失败：无效的URL地址"

        # 解析主机名对应的IP地址
        try:
            resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for family, _, _, _, sockaddr in resolved_ips:
                ip = ipaddress.ip_address(sockaddr[0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return "抓取失败：不允许访问内部网络地址"
        except (socket.gaierror, ValueError):
            return "抓取失败：无法解析目标地址"

        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        # 发送请求（禁止重定向到内网）
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
        response.encoding = response.apparent_encoding

        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # 移除script和style标签
        for script in soup(["script", "style"]):
            script.decompose()

        # 获取文本内容
        text = soup.get_text()

        # 清理文本
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        # 限制长度
        if len(text) > 5000:
            text = text[:5000] + "..."

        return f"页面内容:\n{text}"

    except requests.exceptions.Timeout:
        return "抓取失败：请求超时，请检查网络连接或稍后重试"
    except requests.exceptions.RequestException as e:
        return f"抓取失败：网络错误 - {str(e)}"
    except Exception as e:
        return f"抓取失败：{str(e)}"


@tool("parse_job_text", return_direct=False)
def parse_job_text(text: str, platform: str = "其他") -> str:
    """解析职位文本，提取结构化信息。输入职位描述文本和来源平台（Boss直聘/58同城/其他）。"""
    try:
        from langchain_openai import ChatOpenAI
        from flask import current_app
        
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0
        )
        
        prompt = f"""请从以下职位文本中提取结构化信息。

来源平台：{platform}

职位文本：
{text}

请提取以下信息并返回JSON格式：
{{
    "job_title": "职位名称",
    "company_name": "公司名称",
    "location": "工作地点",
    "salary_min": "最低薪资（数字，单位K）",
    "salary_max": "最高薪资（数字，单位K）",
    "experience_years": "经验要求（数字，单位年）",
    "education": "学历要求（本科/硕士/博士/大专/不限）",
    "skills": ["技能要求1", "技能要求2"],
    "job_description": "工作描述（一句话总结）",
    "benefits": ["福利1", "福利2"],
    "contact_info": "联系方式（如有）"
}}

注意：
1. 如果某个字段无法提取，使用null
2. 薪资请转换为K为单位（如1万-1.5万转换为10K-15K）
3. 经验请转换为年（如3-5年转换为3）
4. 只返回JSON，不要其他内容"""

        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        return f"解析职位文本失败: {str(e)}"


@tool("verify_job", return_direct=False)
def verify_job(job_info: str) -> str:
    """判断职位信息的真假。输入JSON格式的职位信息。"""
    try:
        from langchain_openai import ChatOpenAI
        from flask import current_app
        
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0
        )
        
        prompt = f"""请分析以下职位信息，判断其真假。

职位信息：
{job_info}

请从以下维度分析：

1. **薪资合理性**：
   - 普通岗位月薪是否超过5万？
   - 是否存在"高薪诚聘"、"月入过万"等模糊描述？
   - 薪资与经验要求是否匹配？

2. **职位描述**：
   - 是否有具体的工作内容？
   - 是否存在"轻松赚钱"、"无需经验"等异常描述？
   - 要求是否合理？

3. **公司信息**：
   - 公司名称是否完整？
   - 是否有明确的工作地点？
   - 联系方式是否正常（只留微信/QQ可能是假）？

4. **其他特征**：
   - 是否要求缴纳费用？
   - 是否存在"先培训后上岗"？
   - 是否有异常的福利承诺？

请返回以下格式：
{{
    "is_real": true/false,
    "confidence": 0.0-1.0,
    "risk_level": "低/中/高",
    "analysis": {{
        "salary": "薪资分析",
        "description": "描述分析",
        "company": "公司分析",
        "other": "其他分析"
    }},
    "reasons": ["判断理由1", "判断理由2"],
    "warnings": ["风险提示1", "风险提示2"]
}}

只返回JSON，不要其他内容。"""

        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        return f"验证职位失败: {str(e)}"


@tool("analyze_job_from_text", return_direct=False)
def analyze_job_from_text(text: str, platform: str = "其他") -> str:
    """分析职位信息（一站式）。输入职位文本和来源平台，自动提取信息并判断真假。返回Markdown格式的分析结果。"""
    try:
        from langchain_openai import ChatOpenAI
        from flask import current_app
        
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0
        )
        
        prompt = f"""请分析以下职位信息，提取关键信息并判断真假。

来源平台：{platform}

职位文本：
{text}

请完成以下任务：

1. 提取职位信息（职位名称、公司、地点、薪资、经验、学历、技能、描述）
2. 判断职位真假（分析薪资合理性、描述真实性、公司信息完整性）
3. 给出风险提示

请返回Markdown格式：

## 职位分析结果

| 项目 | 内容 |
|------|------|
| 职位名称 | ... |
| 公司名称 | ... |
| 工作地点 | ... |
| 薪资范围 | ... |
| 经验要求 | ... |
| 学历要求 | ... |
| 技能要求 | ... |

### 真伪判断

**判断结果**：真实职位 ✓ / 疑似虚假 ✗

**判断理由**：
- ...
- ...

**风险提示**：
- ...
- ...

请用中文回复。"""

        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        return f"分析职位失败: {str(e)}"


@tool("get_job_market_trends", return_direct=False)
def get_job_market_trends(industry: str = "互联网", city: str = "全国") -> str:
    """获取职位市场趋势。输入行业和城市。"""
    try:
        from app import db
        db.session.rollback()
        
        query = Job.query
        if industry and industry != "全部":
            query = query.filter(Job.industry.contains(industry))
        if city and city != "全国":
            query = query.filter(Job.city == city)
        
        jobs = query.all()
        if not jobs:
            return f"暂无{industry}行业的职位数据"
        
        # 统计热门职位
        job_titles = {}
        for job in jobs:
            job_titles[job.title] = job_titles.get(job.title, 0) + 1
        
        sorted_titles = sorted(job_titles.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 统计薪资分布
        salaries = [j.salary_avg for j in jobs if j.salary_avg]
        avg_salary = sum(salaries) // len(salaries) if salaries else 0
        
        # 统计城市分布
        cities = {}
        for job in jobs:
            cities[job.city] = cities.get(job.city, 0) + 1
        
        sorted_cities = sorted(cities.items(), key=lambda x: x[1], reverse=True)[:5]
        
        output = f"【{industry}行业】市场趋势分析:\n\n"
        output += f"数据样本: {len(jobs)}个职位\n\n"
        
        output += "热门职位TOP10:\n"
        for i, (title, count) in enumerate(sorted_titles, 1):
            jobs_with_title = [j for j in jobs if j.title == title]
            avg = sum(j.salary_avg for j in jobs_with_title if j.salary_avg) // len(jobs_with_title) if jobs_with_title else 0
            output += f"{i}. {title} ({count}个职位, 平均薪资{avg//1000}K)\n"
        
        output += f"\n整体薪资水平: 平均{avg_salary//1000}K\n"
        
        output += "\n热门城市:\n"
        for city, count in sorted_cities:
            output += f"  - {city}: {count}个职位\n"
        
        return output
    except Exception as e:
        return f"获取市场趋势失败: {str(e)}"


@tool("recommend_career_path", return_direct=False)
def recommend_career_path(current_position: str, target_position: str, years_experience: int = 0) -> str:
    """推荐职业发展路径。输入当前职位、目标职位、工作年限。"""
    try:
        from langchain_openai import ChatOpenAI
        from flask import current_app
        
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0.7
        )
        
        prompt = f"""你是一位资深职业规划顾问。请为以下用户推荐职业发展路径。

当前职位: {current_position}
目标职位: {target_position}
工作年限: {years_experience}年

请提供：
1. 可行的职业发展路径（短期1-2年、中期3-5年、长期5年以上）
2. 每个阶段需要掌握的关键技能
3. 建议的学习资源和实践项目
4. 可能的薪资增长预期
5. 需要注意的风险和挑战

请用自然流畅的中文回复，使用Markdown格式。"""

        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"生成职业路径失败: {str(e)}"


def get_job_tools():
    return [
        search_jobs, query_salary, compare_jobs, save_target_job, update_user_profile,
        fetch_job_from_url, parse_job_text, verify_job, analyze_job_from_text,
        get_job_market_trends, recommend_career_path
    ]
