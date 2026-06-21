"""面试准备工具集 - 面试题生成、自我介绍优化、薪资谈判"""

from langchain.tools import tool
from typing import List
from langchain_openai import ChatOpenAI
from flask import current_app


@tool("generate_interview_questions", return_direct=False)
def generate_interview_questions(job_title: str, skills: List[str] = []) -> str:
    """根据职位和技能生成面试题。输入职位名称和技能列表。"""
    try:
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0.7
        )

        skills_str = "、".join(skills) if skills else "通用"
        prompt = f"""你是一位资深面试官。请为"{job_title}"职位生成10道常见面试题。

候选人技能：{skills_str}

请生成以下类型的面试题：
1. 技术题（3道）：考察专业技能
2. 项目经验题（2道）：考察实际项目能力
3. 行为面试题（2道）：考察软技能和团队协作
4. 场景题（2道）：考察解决问题能力
5. 开放题（1道）：考察思维深度

返回格式：
每道题包含：
- 题目
- 考察点
- 参考答案要点

请用自然流畅的中文回复。"""

        response = llm.invoke(prompt)
        return response.content

    except Exception as e:
        return f"生成面试题失败: {str(e)}"


@tool("optimize_self_intro", return_direct=False)
def optimize_self_intro(user_info: str, job_title: str) -> str:
    """优化自我介绍。输入用户背景和目标职位。"""
    try:
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0.7
        )

        prompt = f"""你是一位职业教练。请帮助优化面试自我介绍。

用户背景：
{user_info}

目标职位：{job_title}

请按照以下结构优化自我介绍：
1. 开场白（10秒）：姓名+教育背景+工作年限
2. 核心优势（30秒）：2-3个与职位匹配的核心能力
3. 项目亮点（30秒）：1-2个代表性项目成果
4. 求职动机（10秒）：为什么选择这个职位
5. 结束语（10秒）：表达期待

要求：
- 总时长控制在90秒左右
- 突出与目标职位的匹配度
- 使用STAR法则描述项目成果
- 语言简洁有力，避免冗余

请提供优化后的自我介绍全文。"""

        response = llm.invoke(prompt)
        return response.content

    except Exception as e:
        return f"优化自我介绍失败: {str(e)}"


@tool("salary_negotiation_tips", return_direct=False)
def salary_negotiation_tips(current_salary: int, target_salary: int, job_title: str) -> str:
    """提供薪资谈判建议。输入当前薪资、目标薪资和职位名称。"""
    try:
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0.7
        )

        prompt = f"""你是一位HR专家和职业教练。请提供薪资谈判建议。

当前薪资：{current_salary}元/月
目标薪资：{target_salary}元/月
职位：{job_title}

涨幅：{((target_salary - current_salary) / current_salary * 100):.1f}%

请提供以下内容：
1. 薪资谈判时机判断
2. 谈判前的准备工作
3. 谈判话术模板
4. 常见谈判策略
5. 应对HR压价的方法
6. 其他可谈判的福利（股票、期权、奖金等）

要求：
- 基于中国职场实际情况
- 话术要自然得体
- 提供多个方案供选择"""

        response = llm.invoke(prompt)
        return response.content

    except Exception as e:
        return f"生成薪资谈判建议失败: {str(e)}"


@tool("analyze_job_description", return_direct=False)
def analyze_job_description(jd_text: str) -> str:
    """深度分析职位描述。输入JD文本，返回详细分析。"""
    try:
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0
        )

        prompt = f"""请深度分析以下职位描述（JD）：

{jd_text}

请从以下维度进行分析：

1. 岗位概述
   - 职位级别（初级/中级/高级）
   - 工作性质（全职/兼职/远程）
   - 团队规模推测

2. 核心要求
   - 必备技能（硬性要求）
   - 加分技能（优先考虑）
   - 经验要求解读
   - 学历要求解读

3. 薪资分析
   - 预估薪资范围
   - 薪资构成分析（底薪+奖金+股票）

4. 面试准备建议
   - 重点准备方向
   - 可能的面试问题
   - 需要准备的项目案例

5. 匹配度评估
   - 适合什么样的候选人
   - 不适合什么样的候选人

请返回JSON格式的分析结果。"""

        response = llm.invoke(prompt)
        return response.content

    except Exception as e:
        return f"分析JD失败: {str(e)}"


@tool("mock_interview", return_direct=False)
def mock_interview(job_title: str, question: str, user_answer: str = "") -> str:
    """模拟面试对话。输入职位、面试问题、用户回答（可选）。"""
    try:
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0.7
        )

        if user_answer:
            prompt = f"""你是一位资深面试官，正在进行{job_title}职位的面试。

面试问题：{question}
候选人回答：{user_answer}

请对候选人的回答进行评价：
1. 回答的优点
2. 回答的不足
3. 改进建议
4. 参考答案要点
5. 追问建议（如果需要深入考察）

请用专业但友好的语气回复。"""
        else:
            prompt = f"""你是一位资深面试官，正在进行{job_title}职位的面试。

面试问题：{question}

请提供：
1. 这个问题的考察点
2. 回答框架建议
3. 参考答案要点
4. 常见错误
5. 加分回答技巧

请用专业但友好的语气回复。"""

        response = llm.invoke(prompt)
        return response.content

    except Exception as e:
        return f"模拟面试失败: {str(e)}"


@tool("interview_checklist", return_direct=False)
def interview_checklist(job_title: str, interview_type: str = "技术面") -> str:
    """生成面试清单。输入职位和面试类型（技术面/HR面/终面）。"""
    try:
        llm = ChatOpenAI(
            model=current_app.config['OPENAI_MODEL'],
            api_key=current_app.config['OPENAI_API_KEY'],
            base_url=current_app.config['OPENAI_BASE_URL'],
            temperature=0.7
        )

        prompt = f"""请为{job_title}职位的{interview_type}生成一份详细的面试准备清单。

请包含：
1. 面试前准备
   - 需要复习的知识点
   - 需要准备的项目案例
   - 需要了解的公司信息

2. 面试中注意事项
   - 自我介绍要点
   - 回答问题的技巧
   - 需要避免的错误

3. 面试后跟进
   - 感谢信模板
   - 后续跟进时机

4. 常见问题及应对
   - 优缺点回答
   - 离职原因回答
   - 职业规划回答

请用Markdown格式输出。"""

        response = llm.invoke(prompt)
        return response.content

    except Exception as e:
        return f"生成面试清单失败: {str(e)}"


def get_interview_tools():
    """获取所有面试相关工具"""
    return [
        generate_interview_questions,
        optimize_self_intro,
        salary_negotiation_tips,
        analyze_job_description,
        mock_interview,
        interview_checklist
    ]
