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
    """计算简历的ATS匹配分数（多维度）"""
    
    name: str = "ats_score"
    description: str = """计算简历相对于目标职位的ATS匹配分数。
    输入应该是JSON格式，包含resume_text（简历文本）和jd_text（职位描述文本）。
    返回多维度ATS评分：关键词匹配、技能匹配、成就量化、格式规范、可读性。"""
    
    def _run(self, input_data: str) -> str:
        """计算ATS分数（多维度）"""
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
            
            prompt = f"""你是一位ATS（简历筛选系统）专家。请对简历进行多维度评分分析。

简历内容：
{resume_text}

职位描述：
{jd_text}

请进行以下5个维度的分析并返回JSON格式：

1. keyword_score（关键词匹配度）：JD中的关键词在简历中出现的比例
2. skill_score（技能匹配度）：必需技能和优先技能的覆盖程度
3. quantification_score（成就量化度）：工作成就是否有数字、百分比、金额等量化指标
4. format_score（格式规范度）：简历格式是否ATS友好（标准节标题、无表格图片等）
5. readability_score（可读性）：语言是否清晰、专业、有条理

返回格式：
{{
    "overall_score": 72,
    "keyword_score": {{
        "score": 65,
        "matched": ["匹配的关键词1", "关键词2"],
        "missing": ["缺失的关键词1", "关键词2"],
        "tip": "建议添加这些关键词以提高匹配度"
    }},
    "skill_score": {{
        "score": 70,
        "matched_skills": ["匹配的技能1"],
        "missing_skills": ["缺失的技能1"],
        "tip": "建议补充这些技能"
    }},
    "quantification_score": {{
        "score": 50,
        "quantified_items": ["已有量化描述1"],
        "unquantified_items": ["缺少量化的描述1"],
        "tip": "建议用数字量化这些成就"
    }},
    "format_score": {{
        "score": 85,
        "issues": ["问题1"],
        "tip": "格式改进建议"
    }},
    "readability_score": {{
        "score": 80,
        "tip": "可读性改进建议"
    }},
    "priority_actions": ["优先改进1", "优先改进2", "优先改进3"]
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
    description: str = """根据用户提供的个人信息生成一份完整的HTML简历。
    输入应该是用户的个人信息文本，包含教育背景、工作经验、技能等。
    返回HTML+Tailwind CSS格式的简历代码。"""
    
    def _run(self, user_info: str) -> str:
        """根据用户信息生成HTML简历"""
        try:
            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0.7
            )
            
            prompt = f"""你是一位拥有10年经验的资深UI/UX架构师和前端开发工程师。请根据用户提供的信息，生成一份美观、现代、专业的HTML简历。

用户提供的信息：
{user_info}

任务要求：
1. 从用户信息中提取：姓名、职位、经验年限、电话、邮箱、GitHub/LinkedIn、个人简介、工作经验、项目经历、教育背景、技能、荣誉证书
2. 使用提取的信息填充HTML简历模板
3. 工作成就必须使用STAR法则改写，并包含量化数据（数字、百分比、金额）
4. 使用行为动词开头（主导、优化、提升、搭建、推动等）

技术栈约束（必须遵守）：
- 使用纯HTML5 + Tailwind CSS（通过CDN引入）
- 严禁使用Markdown语法（如**加粗**、- 列表等）
- 采用响应式布局，注重模块间的留白
- 配色必须符合专业职场调性（深蓝/灰色系）
- 使用SVG图标（内联）替代emoji

HTML简历模板结构（请严格按照此结构生成）：
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>简历</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        primary: '#1e40af',
                        secondary: '#3b82f6',
                        accent: '#60a5fa',
                        muted: '#6b7280',
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="bg-gray-100">
    <div class="max-w-[800px] mx-auto my-8 bg-white shadow-lg rounded-lg overflow-hidden">
        <header class="bg-primary text-white px-8 py-6">
            <h1 class="text-3xl font-bold tracking-wide">用户姓名</h1>
            <p class="text-accent mt-1 text-lg">职位 | 经验年限</p>
            <div class="flex flex-wrap gap-4 mt-3 text-sm text-blue-100">
                <span class="flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">...</svg>
                    电话
                </span>
                <span class="flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">...</svg>
                    邮箱
                </span>
            </div>
        </header>
        <div class="px-8 py-6">
            <section class="mb-6">
                <h2 class="text-lg font-semibold text-primary border-b-2 border-primary pb-1 mb-3">个人简介</h2>
                <p class="text-gray-700 leading-relaxed">用户简介内容</p>
            </section>
            <section class="mb-6">
                <h2 class="text-lg font-semibold text-primary border-b-2 border-primary pb-1 mb-3">工作经验</h2>
                <div class="mb-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h3 class="font-semibold text-gray-900">职位</h3>
                            <p class="text-secondary font-medium">公司</p>
                        </div>
                        <span class="text-sm text-muted bg-gray-100 px-2 py-1 rounded">时间</span>
                    </div>
                    <ul class="mt-2 space-y-2 text-gray-700">
                        <li class="flex items-start gap-2">
                            <span class="text-secondary mt-1">▸</span>
                            <span>STAR法则改写的工作成就，包含量化数据</span>
                        </li>
                    </ul>
                </div>
            </section>
            <section class="mb-6">
                <h2 class="text-lg font-semibold text-primary border-b-2 border-primary pb-1 mb-3">项目经历</h2>
                <div class="mb-4">
                    <div class="flex justify-between items-start">
                        <h3 class="font-semibold text-gray-900">项目名称 - 角色</h3>
                        <span class="text-sm text-muted bg-blue-50 text-primary px-2 py-1 rounded">技术栈</span>
                    </div>
                    <ul class="mt-2 space-y-2 text-gray-700">
                        <li class="flex items-start gap-2">
                            <span class="text-secondary mt-1">▸</span>
                            <span>项目成果描述</span>
                        </li>
                    </ul>
                </div>
            </section>
            <section class="mb-6">
                <h2 class="text-lg font-semibold text-primary border-b-2 border-primary pb-1 mb-3">教育背景</h2>
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="font-semibold text-gray-900">学校</h3>
                        <p class="text-gray-600">专业 · 学历</p>
                    </div>
                    <span class="text-sm text-muted bg-gray-100 px-2 py-1 rounded">时间</span>
                </div>
            </section>
            <section>
                <h2 class="text-lg font-semibold text-primary border-b-2 border-primary pb-1 mb-3">技能清单</h2>
                <div class="flex flex-wrap gap-2">
                    <span class="bg-blue-100 text-primary px-2 py-1 rounded text-sm font-medium">技能1</span>
                    <span class="bg-blue-100 text-primary px-2 py-1 rounded text-sm font-medium">技能2</span>
                </div>
            </section>
        </div>
    </div>
</body>
</html>
```

重要提醒：
1. 必须使用用户提供的真实信息，不要编造
2. 工作成就必须用STAR法则改写，包含量化数据
3. 技能标签要分类展示（核心技术、框架、工具等）
4. 只输出完整的HTML代码，不要输出其他内容"""
            
            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            return json.dumps({"error": f"生成失败: {str(e)}"}, ensure_ascii=False)


class StarRewriteTool(BaseTool):
    """用STAR法则改写工作经历"""
    
    name: str = "star_rewrite"
    description: str = """将工作经历描述改写为STAR法则格式（情境、任务、行动、结果）。
    输入可以是单条工作描述文本，也可以是JSON格式包含description和job_title。
    返回改写后的STAR格式描述。"""
    
    def _run(self, input_data: str) -> str:
        """STAR法则改写"""
        try:
            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0.7
            )
            
            prompt = f"""你是一位简历改写专家。请将以下工作经历描述改写为STAR法则格式。

原始描述：
{input_data}

STAR法则要求：
- S（Situation/情境）：当时的背景是什么
- T（Task/任务）：需要完成什么任务
- A（Action/行动）：采取了什么行动
- R（Result/结果）：取得了什么成果（必须量化）

改写规则：
1. 使用行为动词开头（主导、优化、提升、搭建、推动等）
2. 必须包含量化数据（数字、百分比、金额、时间）
3. 突出个人贡献和影响力
4. 语言简洁专业，避免冗余

请返回改写后的描述，格式为一段话，不要分点列出STAR。

示例：
原始：负责用户增长工作
改写：在用户增长停滞的背景下（S），主导用户增长策略优化（T），通过A/B测试重构注册流程并搭建用户推荐体系（A），3个月内新用户增长35%，获客成本降低20%（R）"""

            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            return json.dumps({"error": f"改写失败: {str(e)}"}, ensure_ascii=False)


def get_resume_tools():
    """获取所有简历相关工具"""
    return [
        ParseResumeTool(),
        AnalyzeJDTool(),
        OptimizeResumeTool(),
        ATSScoreTool(),
        GenerateResumeTool(),
        StarRewriteTool()
    ]
