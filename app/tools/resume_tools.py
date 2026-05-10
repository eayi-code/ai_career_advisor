"""简历工具集 - 解析、优化、ATS评分"""

import json
import os
from typing import Optional
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from flask import current_app


class ParseResumeTool(BaseTool):
    """解析简历文件（PDF/DOCX），提取结构化信息"""
    
    name: str = "parse_resume"
    description: str = """解析简历文件，提取结构化信息。
    输入应该是简历文件的路径或简历文本内容。
    返回JSON格式的结构化简历数据，包含：个人信息、教育背景、工作经验、技能、项目等。"""
    
    def _run(self, resume_text: str) -> str:
        """解析简历文本，提取结构化信息"""
        try:
            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0
            )
            
            prompt = f"""请解析以下简历内容，提取结构化信息，以JSON格式返回。

简历内容：
{resume_text}

请返回以下JSON结构（只返回JSON，不要其他内容）：
{{
    "personal_info": {{
        "name": "姓名",
        "phone": "电话",
        "email": "邮箱",
        "location": "所在地",
        "summary": "个人简介"
    }},
    "education": [
        {{
            "school": "学校名称",
            "degree": "学历",
            "major": "专业",
            "start_date": "开始时间",
            "end_date": "结束时间",
            "gpa": "GPA（如有）"
        }}
    ],
    "experience": [
        {{
            "company": "公司名称",
            "position": "职位",
            "start_date": "开始时间",
            "end_date": "结束时间",
            "description": "工作描述",
            "achievements": ["成就1", "成就2"]
        }}
    ],
    "skills": ["技能1", "技能2"],
    "projects": [
        {{
            "name": "项目名称",
            "description": "项目描述",
            "technologies": ["技术1", "技术2"],
            "achievements": ["成就1"]
        }}
    ],
    "certifications": ["证书1", "证书2"]
}}"""
            
            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            return json.dumps({"error": f"解析失败: {str(e)}"}, ensure_ascii=False)


class AnalyzeJDTool(BaseTool):
    """分析职位描述（JD），提取关键要求"""
    
    name: str = "analyze_jd"
    description: str = """分析职位描述（Job Description），提取关键要求。
    输入应该是职位描述的文本内容。
    返回JSON格式的分析结果，包含：必需技能、优先技能、经验要求、学历要求等。"""
    
    def _run(self, jd_text: str) -> str:
        """分析JD，提取关键要求"""
        try:
            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0
            )
            
            prompt = f"""请分析以下职位描述（JD），提取关键要求。

职位描述：
{jd_text}

请返回以下JSON结构（只返回JSON，不要其他内容）：
{{
    "job_title": "职位名称",
    "company": "公司名称（如有）",
    "required_skills": ["必需技能1", "必需技能2"],
    "preferred_skills": ["优先技能1", "优先技能2"],
    "experience_years": "经验年限要求",
    "education_requirement": "学历要求",
    "key_responsibilities": ["主要职责1", "主要职责2"],
    "keywords": ["ATS关键词1", "关键词2"],
    "salary_range": "薪资范围（如有）",
    "job_type": "工作类型（全职/兼职/远程等）"
}}"""
            
            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            return json.dumps({"error": f"分析失败: {str(e)}"}, ensure_ascii=False)


class OptimizeResumeTool(BaseTool):
    """根据JD优化简历内容"""
    
    name: str = "optimize_resume"
    description: str = """根据目标职位的JD优化简历内容。
    输入应该是JSON格式，包含resume（简历结构化数据）和jd_analysis（JD分析结果）。
    返回优化后的简历建议和改写内容。"""
    
    def _run(self, input_data: str) -> str:
        """根据JD优化简历"""
        try:
            data = json.loads(input_data)
            resume = data.get("resume", {})
            jd_analysis = data.get("jd_analysis", {})
            
            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0.7
            )
            
            prompt = f"""你是一位专业的简历优化顾问。请根据目标职位的要求，优化简历内容。

当前简历信息：
{json.dumps(resume, ensure_ascii=False, indent=2)}

目标职位要求：
{json.dumps(jd_analysis, ensure_ascii=False, indent=2)}

请提供以下优化建议（返回JSON格式）：

1. 缺失技能分析：简历中缺少但JD要求的技能
2. 关键词优化：建议添加的ATS关键词
3. 工作经历改写：用STAR法则改写工作成就，量化结果
4. 技能匹配度评分：0-100分
5. 优化后的个人简介

返回格式：
{{
    "missing_skills": ["缺失技能1", "缺失技能2"],
    "keywords_to_add": ["关键词1", "关键词2"],
    "experience_rewrites": [
        {{
            "original": "原始内容",
            "optimized": "优化后内容（STAR法则，量化结果）"
        }}
    ],
    "skill_match_score": 75,
    "optimized_summary": "优化后的个人简介",
    "general_tips": ["建议1", "建议2"]
}}"""
            
            response = llm.invoke(prompt)
            return response.content
            
        except json.JSONDecodeError:
            return json.dumps({"error": "输入格式错误，请提供JSON格式数据"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"优化失败: {str(e)}"}, ensure_ascii=False)


class ATSScoreTool(BaseTool):
    """计算简历的ATS（Applicant Tracking System）匹配分数"""
    
    name: str = "ats_score"
    description: str = """计算简历相对于目标职位的ATS匹配分数。
    输入应该是JSON格式，包含resume_text（简历文本）和jd_text（职位描述文本）。
    返回ATS评分和详细分析。"""
    
    def _run(self, input_data: str) -> str:
        """计算ATS分数"""
        try:
            data = json.loads(input_data)
            resume_text = data.get("resume_text", "")
            jd_text = data.get("jd_text", "")
            
            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0
            )
            
            prompt = f"""你是一位ATS（简历筛选系统）专家。请分析简历与职位描述的匹配度。

简历内容：
{resume_text}

职位描述：
{jd_text}

请进行以下分析并返回JSON格式：

1. 关键词匹配：JD中的关键词在简历中出现的比例
2. 技能匹配：必需技能和优先技能的覆盖程度
3. 经验匹配：工作经验是否符合要求
4. 学历匹配：学历是否符合要求
5. 格式评分：简历格式是否ATS友好
6. 总体评分：0-100分
7. 改进建议

返回格式：
{{
    "overall_score": 72,
    "keyword_match": {{
        "score": 65,
        "matched": ["匹配的关键词1", "关键词2"],
        "missing": ["缺失的关键词1", "关键词2"]
    }},
    "skill_match": {{
        "score": 70,
        "matched_skills": ["匹配的技能1"],
        "missing_skills": ["缺失的技能1"]
    }},
    "experience_match": {{
        "score": 80,
        "assessment": "评估说明"
    }},
    "education_match": {{
        "score": 90,
        "assessment": "评估说明"
    }},
    "format_score": 85,
    "improvement_suggestions": ["建议1", "建议2", "建议3"]
}}"""
            
            response = llm.invoke(prompt)
            return response.content
            
        except json.JSONDecodeError:
            return json.dumps({"error": "输入格式错误，请提供JSON格式数据"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"评分失败: {str(e)}"}, ensure_ascii=False)


class GenerateResumeTool(BaseTool):
    """根据用户信息生成完整简历"""
    
    name: str = "generate_resume"
    description: str = """根据用户提供的个人信息生成一份完整的简历。
    输入应该是用户的个人信息文本，包含教育背景、工作经验、技能等。
    返回生成的简历文本。"""
    
    def _run(self, user_info: str) -> str:
        """根据用户信息生成简历"""
        try:
            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0.7
            )
            
            prompt = f"""你是一位专业的简历撰写顾问。请根据用户提供的信息，生成一份专业、ATS友好的简历。

用户提供的信息：
{user_info}

请生成一份完整的简历，包含以下部分：

1. 个人信息（姓名、联系方式、所在地）
2. 个人简介/职业概述（3-4句话，突出核心优势）
3. 工作经验（使用STAR法则，量化成就）
4. 教育背景
5. 技能（分门别类：技术技能、软技能、工具等）
6. 项目经历（如有）
7. 证书/资质（如有）

要求：
- 使用专业的语言风格
- 工作成就要量化（数字、百分比、金额等）
- 使用行为动词开头（如：负责、主导、优化、提升等）
- 格式清晰，便于ATS解析
- 针对求职者的目标岗位进行优化

请直接输出简历文本，使用清晰的格式。"""
            
            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            return json.dumps({"error": f"生成失败: {str(e)}"}, ensure_ascii=False)


def get_resume_tools():
    """获取所有简历相关工具"""
    return [
        ParseResumeTool(),
        AnalyzeJDTool(),
        OptimizeResumeTool(),
        ATSScoreTool(),
        GenerateResumeTool()
    ]
