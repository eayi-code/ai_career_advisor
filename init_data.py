"""数据初始化脚本 - 导入职位、技能、副业数据"""

from app import create_app, db
from app.models.job import Job, JobSkill
from app.models.skill import Skill, SkillCategory, LearningResource
from app.models.side_job import SideJob


def init_jobs():
    """初始化职位数据"""
    jobs_data = [
        {
            "title": "数据分析师", "industry": "互联网", "city": "北京",
            "description": "负责数据采集、清洗、分析和可视化，为业务决策提供数据支持",
            "responsibilities": ["搭建数据分析体系", "制作数据报表", "分析用户行为数据", "输出分析报告"],
            "salary_min": 10000, "salary_max": 25000, "salary_avg": 17500,
            "experience_years": 1, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 3,
            "skills": ["Python", "SQL", "Excel", "数据可视化", "统计学", "Tableau"]
        },
        {
            "title": "高级数据分析师", "industry": "互联网", "city": "上海",
            "description": "负责复杂数据分析项目，带领团队完成数据驱动的业务优化",
            "responsibilities": ["设计数据分析框架", "建立数据指标体系", "指导初级分析师", "推动数据驱动决策"],
            "salary_min": 20000, "salary_max": 40000, "salary_avg": 30000,
            "experience_years": 3, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 4,
            "skills": ["Python", "SQL", "机器学习", "数据可视化", "项目管理", "业务理解"]
        },
        {
            "title": "数据科学家", "industry": "互联网", "city": "深圳",
            "description": "运用机器学习和深度学习技术解决复杂业务问题",
            "responsibilities": ["构建预测模型", "优化算法", "数据挖掘", "模型部署"],
            "salary_min": 30000, "salary_max": 60000, "salary_avg": 45000,
            "experience_years": 3, "education_requirement": "硕士",
            "is_hot": True, "growth_potential": "极高", "difficulty_level": 5,
            "skills": ["Python", "机器学习", "深度学习", "TensorFlow", "统计学", "数学建模"]
        },
        {
            "title": "前端开发工程师", "industry": "互联网", "city": "北京",
            "description": "负责Web前端开发，实现产品界面和交互功能",
            "responsibilities": ["开发Web页面", "实现交互功能", "优化性能", "兼容性处理"],
            "salary_min": 12000, "salary_max": 30000, "salary_avg": 21000,
            "experience_years": 1, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 3,
            "skills": ["JavaScript", "HTML", "CSS", "React", "Vue", "Git"]
        },
        {
            "title": "高级前端开发工程师", "industry": "互联网", "city": "杭州",
            "description": "负责前端架构设计和技术选型，解决复杂技术问题",
            "responsibilities": ["前端架构设计", "技术选型", "代码审查", "性能优化"],
            "salary_min": 25000, "salary_max": 50000, "salary_avg": 37500,
            "experience_years": 5, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 4,
            "skills": ["JavaScript", "TypeScript", "React", "Node.js", "Webpack", "架构设计"]
        },
        {
            "title": "后端开发工程师", "industry": "互联网", "city": "上海",
            "description": "负责服务器端开发，设计和实现API接口",
            "responsibilities": ["开发API接口", "数据库设计", "系统架构", "性能优化"],
            "salary_min": 15000, "salary_max": 35000, "salary_avg": 25000,
            "experience_years": 1, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 3,
            "skills": ["Java", "Python", "MySQL", "Redis", "Spring", "Linux"]
        },
        {
            "title": "Java开发工程师", "industry": "金融", "city": "上海",
            "description": "负责Java后端开发，参与金融系统设计与开发",
            "responsibilities": ["Java开发", "系统设计", "代码审查", "技术文档编写"],
            "salary_min": 18000, "salary_max": 40000, "salary_avg": 29000,
            "experience_years": 2, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 4,
            "skills": ["Java", "Spring Boot", "MySQL", "Redis", "微服务", "Docker"]
        },
        {
            "title": "Python开发工程师", "industry": "互联网", "city": "深圳",
            "description": "使用Python进行后端开发和数据处理",
            "responsibilities": ["Python开发", "API设计", "数据处理", "自动化脚本"],
            "salary_min": 15000, "salary_max": 35000, "salary_avg": 25000,
            "experience_years": 1, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 3,
            "skills": ["Python", "Django", "Flask", "MySQL", "Redis", "Linux"]
        },
        {
            "title": "产品经理", "industry": "互联网", "city": "北京",
            "description": "负责产品规划、设计和推动落地",
            "responsibilities": ["需求分析", "产品设计", "项目管理", "数据分析"],
            "salary_min": 15000, "salary_max": 40000, "salary_avg": 27500,
            "experience_years": 2, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 4,
            "skills": ["需求分析", "原型设计", "项目管理", "数据分析", "用户研究", "沟通能力"]
        },
        {
            "title": "高级产品经理", "industry": "互联网", "city": "杭州",
            "description": "负责核心产品线，制定产品策略",
            "responsibilities": ["产品策略制定", "团队管理", "跨部门协调", "数据分析"],
            "salary_min": 30000, "salary_max": 60000, "salary_avg": 45000,
            "experience_years": 5, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "极高", "difficulty_level": 5,
            "skills": ["产品策略", "团队管理", "数据分析", "商业思维", "用户研究", "行业洞察"]
        },
        {
            "title": "UI设计师", "industry": "互联网", "city": "上海",
            "description": "负责产品界面设计，制定设计规范",
            "responsibilities": ["界面设计", "图标设计", "设计规范制定", "与开发对接"],
            "salary_min": 10000, "salary_max": 25000, "salary_avg": 17500,
            "experience_years": 1, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 3,
            "skills": ["Figma", "Sketch", "Photoshop", "Illustrator", "设计规范", "色彩搭配"]
        },
        {
            "title": "UX设计师", "industry": "互联网", "city": "深圳",
            "description": "负责用户体验设计，提升产品易用性",
            "responsibilities": ["用户研究", "交互设计", "可用性测试", "设计优化"],
            "salary_min": 15000, "salary_max": 35000, "salary_avg": 25000,
            "experience_years": 2, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 4,
            "skills": ["用户研究", "交互设计", "Figma", "原型设计", "数据分析", "心理学"]
        },
        {
            "title": "测试工程师", "industry": "互联网", "city": "北京",
            "description": "负责软件测试，保证产品质量",
            "responsibilities": ["编写测试用例", "执行测试", "缺陷跟踪", "自动化测试"],
            "salary_min": 10000, "salary_max": 25000, "salary_avg": 17500,
            "experience_years": 1, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 3,
            "skills": ["测试理论", "Selenium", "Python", "SQL", "Linux", "Jenkins"]
        },
        {
            "title": "测试开发工程师", "industry": "互联网", "city": "上海",
            "description": "开发自动化测试框架，提升测试效率",
            "responsibilities": ["搭建测试框架", "开发测试工具", "性能测试", "持续集成"],
            "salary_min": 18000, "salary_max": 40000, "salary_avg": 29000,
            "experience_years": 3, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 4,
            "skills": ["Python", "Java", "Selenium", "Jenkins", "Docker", "性能测试"]
        },
        {
            "title": "运维工程师", "industry": "互联网", "city": "深圳",
            "description": "负责服务器运维和系统监控",
            "responsibilities": ["服务器管理", "系统监控", "故障处理", "自动化运维"],
            "salary_min": 12000, "salary_max": 30000, "salary_avg": 21000,
            "experience_years": 1, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 3,
            "skills": ["Linux", "Shell", "Docker", "Kubernetes", "Nginx", "监控工具"]
        },
        {
            "title": "DevOps工程师", "industry": "互联网", "city": "北京",
            "description": "负责CI/CD流水线搭建，推动开发运维一体化",
            "responsibilities": ["CI/CD搭建", "容器化部署", "自动化脚本", "云资源管理"],
            "salary_min": 20000, "salary_max": 45000, "salary_avg": 32500,
            "experience_years": 3, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 4,
            "skills": ["Docker", "Kubernetes", "Jenkins", "AWS", "Terraform", "Python"]
        },
        {
            "title": "算法工程师", "industry": "人工智能", "city": "北京",
            "description": "负责机器学习算法研发和优化",
            "responsibilities": ["算法研发", "模型训练", "算法优化", "论文阅读"],
            "salary_min": 25000, "salary_max": 55000, "salary_avg": 40000,
            "experience_years": 2, "education_requirement": "硕士",
            "is_hot": True, "growth_potential": "极高", "difficulty_level": 5,
            "skills": ["Python", "机器学习", "深度学习", "TensorFlow", "PyTorch", "数学"]
        },
        {
            "title": "NLP算法工程师", "industry": "人工智能", "city": "深圳",
            "description": "负责自然语言处理相关算法研发",
            "responsibilities": ["NLP算法开发", "文本分析", "模型优化", "技术调研"],
            "salary_min": 30000, "salary_max": 60000, "salary_avg": 45000,
            "experience_years": 2, "education_requirement": "硕士",
            "is_hot": True, "growth_potential": "极高", "difficulty_level": 5,
            "skills": ["Python", "NLP", "深度学习", "Transformer", "BERT", "PyTorch"]
        },
        {
            "title": "计算机视觉工程师", "industry": "人工智能", "city": "上海",
            "description": "负责图像识别和计算机视觉算法开发",
            "responsibilities": ["CV算法开发", "图像处理", "模型训练", "产品落地"],
            "salary_min": 25000, "salary_max": 50000, "salary_avg": 37500,
            "experience_years": 2, "education_requirement": "硕士",
            "is_hot": True, "growth_potential": "极高", "difficulty_level": 5,
            "skills": ["Python", "计算机视觉", "深度学习", "OpenCV", "PyTorch", "C++"]
        },
        {
            "title": "Android开发工程师", "industry": "互联网", "city": "北京",
            "description": "负责Android应用开发",
            "responsibilities": ["Android开发", "性能优化", "bug修复", "版本迭代"],
            "salary_min": 15000, "salary_max": 35000, "salary_avg": 25000,
            "experience_years": 1, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 3,
            "skills": ["Java", "Kotlin", "Android SDK", "SQLite", "Git", "设计模式"]
        },
        {
            "title": "iOS开发工程师", "industry": "互联网", "city": "上海",
            "description": "负责iOS应用开发",
            "responsibilities": ["iOS开发", "性能优化", "bug修复", "版本迭代"],
            "salary_min": 15000, "salary_max": 35000, "salary_avg": 25000,
            "experience_years": 1, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 3,
            "skills": ["Swift", "Objective-C", "iOS SDK", "Xcode", "Git", "设计模式"]
        },
        {
            "title": "网络安全工程师", "industry": "互联网", "city": "深圳",
            "description": "负责网络安全防护和漏洞修复",
            "responsibilities": ["安全审计", "漏洞扫描", "安全加固", "应急响应"],
            "salary_min": 15000, "salary_max": 35000, "salary_avg": 25000,
            "experience_years": 2, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 4,
            "skills": ["网络安全", "渗透测试", "Linux", "Python", "防火墙", "加密技术"]
        },
        {
            "title": "数据库管理员", "industry": "金融", "city": "北京",
            "description": "负责数据库管理和维护",
            "responsibilities": ["数据库管理", "性能调优", "备份恢复", "数据安全"],
            "salary_min": 15000, "salary_max": 35000, "salary_avg": 25000,
            "experience_years": 2, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 4,
            "skills": ["MySQL", "Oracle", "Redis", "MongoDB", "Linux", "Shell"]
        },
        {
            "title": "云计算工程师", "industry": "互联网", "city": "上海",
            "description": "负责云平台架构设计和运维",
            "responsibilities": ["云架构设计", "资源管理", "成本优化", "技术支持"],
            "salary_min": 20000, "salary_max": 45000, "salary_avg": 32500,
            "experience_years": 3, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "高", "difficulty_level": 4,
            "skills": ["AWS", "阿里云", "Docker", "Kubernetes", "Terraform", "Python"]
        },
        {
            "title": "区块链开发工程师", "industry": "金融科技", "city": "深圳",
            "description": "负责区块链应用开发",
            "responsibilities": ["智能合约开发", "链上应用开发", "技术调研", "代码审计"],
            "salary_min": 25000, "salary_max": 50000, "salary_avg": 37500,
            "experience_years": 2, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 5,
            "skills": ["Solidity", "Go", "Rust", "Web3", "密码学", "分布式系统"]
        },
        {
            "title": "游戏开发工程师", "industry": "游戏", "city": "上海",
            "description": "负责游戏客户端或服务端开发",
            "responsibilities": ["游戏开发", "性能优化", "功能实现", "bug修复"],
            "salary_min": 15000, "salary_max": 35000, "salary_avg": 25000,
            "experience_years": 1, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 4,
            "skills": ["C++", "Unity", "Unreal Engine", "Lua", "3D数学", "图形学"]
        },
        {
            "title": "运营专员", "industry": "互联网", "city": "北京",
            "description": "负责产品运营和用户增长",
            "responsibilities": ["内容运营", "用户运营", "活动策划", "数据分析"],
            "salary_min": 8000, "salary_max": 18000, "salary_avg": 13000,
            "experience_years": 0, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 2,
            "skills": ["内容创作", "数据分析", "Excel", "沟通能力", "创意能力", "用户研究"]
        },
        {
            "title": "新媒体运营", "industry": "互联网", "city": "杭州",
            "description": "负责社交媒体账号运营和内容创作",
            "responsibilities": ["内容策划", "账号运营", "粉丝互动", "数据分析"],
            "salary_min": 8000, "salary_max": 20000, "salary_avg": 14000,
            "experience_years": 0, "education_requirement": "本科",
            "is_hot": True, "growth_potential": "中", "difficulty_level": 2,
            "skills": ["文案写作", "视频剪辑", "Photoshop", "数据分析", "社交媒体", "创意能力"]
        },
        {
            "title": "市场营销经理", "industry": "互联网", "city": "上海",
            "description": "负责市场营销策略制定和执行",
            "responsibilities": ["市场调研", "营销策划", "渠道管理", "预算管理"],
            "salary_min": 15000, "salary_max": 35000, "salary_avg": 25000,
            "experience_years": 3, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "高", "difficulty_level": 4,
            "skills": ["市场分析", "营销策划", "数据分析", "团队管理", "沟通能力", "商业思维"]
        },
        {
            "title": "人力资源专员", "industry": "互联网", "city": "深圳",
            "description": "负责招聘、培训、绩效等人力资源工作",
            "responsibilities": ["招聘管理", "培训组织", "绩效考核", "员工关系"],
            "salary_min": 8000, "salary_max": 18000, "salary_avg": 13000,
            "experience_years": 0, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 2,
            "skills": ["招聘技巧", "劳动法", "沟通能力", "Excel", "PPT", "组织能力"]
        },
        {
            "title": "财务分析师", "industry": "金融", "city": "北京",
            "description": "负责财务数据分析和报告",
            "responsibilities": ["财务分析", "预算编制", "报表制作", "成本控制"],
            "salary_min": 12000, "salary_max": 30000, "salary_avg": 21000,
            "experience_years": 2, "education_requirement": "本科",
            "is_hot": False, "growth_potential": "中", "difficulty_level": 3,
            "skills": ["财务分析", "Excel", "SQL", "Python", "会计知识", "财务建模"]
        },
    ]

    for job_data in jobs_data:
        skills = job_data.pop('skills')
        job = Job(**job_data)
        db.session.add(job)
        db.session.flush()

        for skill_name in skills:
            job_skill = JobSkill(job_id=job.id, skill_name=skill_name, importance='required')
            db.session.add(job_skill)

    db.session.commit()
    print(f'导入 {len(jobs_data)} 条职位数据')


def init_skills():
    """初始化技能数据"""
    categories = {
        '编程语言': '各类编程语言技能',
        '数据科学': '数据分析和机器学习相关技能',
        '前端开发': 'Web前端相关技能',
        '后端开发': '服务端开发相关技能',
        '人工智能': 'AI和深度学习相关技能',
        '设计': 'UI/UX设计相关技能',
        '产品': '产品管理相关技能',
        '运维': '运维和DevOps相关技能',
        '软技能': '沟通、管理等软技能',
    }

    category_objs = {}
    for name, desc in categories.items():
        cat = SkillCategory(name=name, description=desc)
        db.session.add(cat)
        db.session.flush()
        category_objs[name] = cat

    skills_data = [
        {"name": "Python", "category": "编程语言", "difficulty": 2, "demand": "极高", "months": 3,
         "resources": [
             {"title": "Python官方教程", "type": "文档", "difficulty": "入门", "duration": "20小时"},
             {"title": "《Python编程：从入门到实践》", "type": "书籍", "difficulty": "入门", "duration": "40小时"},
             {"title": "廖雪峰Python教程", "type": "在线课程", "difficulty": "入门", "duration": "30小时"},
         ]},
        {"name": "Java", "category": "编程语言", "difficulty": 3, "demand": "高", "months": 4,
         "resources": [
             {"title": "《Java核心技术》", "type": "书籍", "difficulty": "入门", "duration": "60小时"},
             {"title": "尚硅谷Java教程", "type": "视频", "difficulty": "入门", "duration": "100小时"},
         ]},
        {"name": "JavaScript", "category": "编程语言", "difficulty": 2, "demand": "极高", "months": 3,
         "resources": [
             {"title": "《JavaScript高级程序设计》", "type": "书籍", "difficulty": "中级", "duration": "50小时"},
             {"title": "MDN Web Docs", "type": "文档", "difficulty": "入门", "duration": "30小时"},
         ]},
        {"name": "SQL", "category": "数据科学", "difficulty": 2, "demand": "极高", "months": 1,
         "resources": [
             {"title": "《SQL必知必会》", "type": "书籍", "difficulty": "入门", "duration": "15小时"},
             {"title": "LeetCode SQL题库", "type": "练习", "difficulty": "中级", "duration": "20小时"},
         ]},
        {"name": "数据分析", "category": "数据科学", "difficulty": 3, "demand": "高", "months": 3,
         "resources": [
             {"title": "《利用Python进行数据分析》", "type": "书籍", "difficulty": "中级", "duration": "40小时"},
             {"title": "Coursera数据分析专项课程", "type": "在线课程", "difficulty": "入门", "duration": "60小时"},
         ]},
        {"name": "机器学习", "category": "人工智能", "difficulty": 4, "demand": "高", "months": 6,
         "resources": [
             {"title": "吴恩达机器学习课程", "type": "视频", "difficulty": "入门", "duration": "60小时"},
             {"title": "《机器学习》西瓜书", "type": "书籍", "difficulty": "中级", "duration": "80小时"},
         ]},
        {"name": "深度学习", "category": "人工智能", "difficulty": 5, "demand": "高", "months": 6,
         "resources": [
             {"title": "吴恩达深度学习课程", "type": "视频", "difficulty": "中级", "duration": "80小时"},
             {"title": "《深度学习》花书", "type": "书籍", "difficulty": "高级", "duration": "100小时"},
         ]},
        {"name": "React", "category": "前端开发", "difficulty": 3, "demand": "高", "months": 2,
         "resources": [
             {"title": "React官方文档", "type": "文档", "difficulty": "入门", "duration": "20小时"},
             {"title": "《React设计模式与最佳实践》", "type": "书籍", "difficulty": "中级", "duration": "30小时"},
         ]},
        {"name": "Vue", "category": "前端开发", "difficulty": 2, "demand": "高", "months": 2,
         "resources": [
             {"title": "Vue.js官方文档", "type": "文档", "difficulty": "入门", "duration": "15小时"},
             {"title": "尚硅谷Vue教程", "type": "视频", "difficulty": "入门", "duration": "40小时"},
         ]},
        {"name": "MySQL", "category": "后端开发", "difficulty": 2, "demand": "极高", "months": 2,
         "resources": [
             {"title": "《MySQL必知必会》", "type": "书籍", "difficulty": "入门", "duration": "20小时"},
         ]},
        {"name": "Redis", "category": "后端开发", "difficulty": 3, "demand": "高", "months": 1,
         "resources": [
             {"title": "《Redis设计与实现》", "type": "书籍", "difficulty": "中级", "duration": "30小时"},
         ]},
        {"name": "Docker", "category": "运维", "difficulty": 3, "demand": "高", "months": 1,
         "resources": [
             {"title": "Docker官方文档", "type": "文档", "difficulty": "入门", "duration": "15小时"},
             {"title": "《Docker技术入门与实践》", "type": "书籍", "difficulty": "入门", "duration": "25小时"},
         ]},
        {"name": "Kubernetes", "category": "运维", "difficulty": 4, "demand": "高", "months": 3,
         "resources": [
             {"title": "Kubernetes官方文档", "type": "文档", "difficulty": "中级", "duration": "30小时"},
         ]},
        {"name": "Figma", "category": "设计", "difficulty": 2, "demand": "高", "months": 1,
         "resources": [
             {"title": "Figma官方教程", "type": "文档", "difficulty": "入门", "duration": "10小时"},
         ]},
        {"name": "TensorFlow", "category": "人工智能", "difficulty": 4, "demand": "高", "months": 3,
         "resources": [
             {"title": "TensorFlow官方教程", "type": "文档", "difficulty": "中级", "duration": "40小时"},
         ]},
        {"name": "PyTorch", "category": "人工智能", "difficulty": 4, "demand": "高", "months": 3,
         "resources": [
             {"title": "PyTorch官方教程", "type": "文档", "difficulty": "中级", "duration": "40小时"},
         ]},
        {"name": "项目管理", "category": "产品", "difficulty": 3, "demand": "高", "months": 2,
         "resources": [
             {"title": "《PMBOK指南》", "type": "书籍", "difficulty": "中级", "duration": "50小时"},
         ]},
        {"name": "数据分析思维", "category": "软技能", "difficulty": 3, "demand": "高", "months": 2,
         "resources": [
             {"title": "《数据化运营》", "type": "书籍", "difficulty": "中级", "duration": "30小时"},
         ]},
    ]

    for skill_data in skills_data:
        resources = skill_data.pop('resources')
        skill = Skill(
            name=skill_data['name'],
            category_id=category_objs[skill_data['category']].id,
            difficulty_level=skill_data['difficulty'],
            market_demand=skill_data['demand'],
            learning_months=skill_data['months']
        )
        db.session.add(skill)
        db.session.flush()

        for res in resources:
            resource = LearningResource(
                skill_id=skill.id,
                title=res['title'],
                type=res['type'],
                difficulty=res['difficulty'],
                duration=res['duration']
            )
            db.session.add(resource)

    db.session.commit()
    print(f'导入 {len(skills_data)} 条技能数据')


def init_side_jobs():
    """初始化副业数据"""
    side_jobs_data = [
        {
            "title": "自由撰稿", "category": "内容创作",
            "description": "为网站、公众号、杂志等撰写文章",
            "income_min": 3000, "income_max": 15000, "hours_per_week": 10,
            "startup_cost": 0, "difficulty_level": 2,
            "platforms": ["知乎", "公众号", "头条号", "简书", "豆瓣"],
            "skills_required": ["写作", "文案", "SEO"],
            "getting_started": ["注册平台账号", "确定写作方向", "持续输出内容", "积累粉丝"],
            "pros": ["时间灵活", "零成本启动", "可积累个人品牌"],
            "cons": ["收入不稳定", "需要持续输出", "竞争激烈"]
        },
        {
            "title": "短视频创作", "category": "内容创作",
            "description": "在抖音、B站等平台创作短视频内容",
            "income_min": 2000, "income_max": 50000, "hours_per_week": 15,
            "startup_cost": 2000, "difficulty_level": 3,
            "platforms": ["抖音", "B站", "小红书", "快手", "视频号"],
            "skills_required": ["视频剪辑", "创意", "拍摄", "运营"],
            "getting_started": ["确定内容方向", "学习视频剪辑", "持续更新内容", "分析数据优化"],
            "pros": ["收入上限高", "可积累粉丝", "变现方式多样"],
            "cons": ["需要持续更新", "前期投入大", "竞争激烈"]
        },
        {
            "title": "UI设计接单", "category": "设计",
            "description": "为企业或个人提供UI设计服务",
            "income_min": 5000, "income_max": 20000, "hours_per_week": 15,
            "startup_cost": 0, "difficulty_level": 3,
            "platforms": ["猪八戒", "站酷", "Dribbble", "Behance", "淘宝"],
            "skills_required": ["Figma", "Sketch", "Photoshop", "设计规范"],
            "getting_started": ["准备作品集", "注册接单平台", "完善个人资料", "积极投标"],
            "pros": ["收入较高", "可积累作品", "技能可复用"],
            "cons": ["需要作品集", "沟通成本高", "甲方需求多变"]
        },
        {
            "title": "编程外包", "category": "技术",
            "description": "承接网站、小程序、APP等开发项目",
            "income_min": 8000, "income_max": 50000, "hours_per_week": 20,
            "startup_cost": 0, "difficulty_level": 4,
            "platforms": ["程序员客栈", "开源众包", "Upwork", "Freelancer", "码市"],
            "skills_required": ["编程", "项目管理", "沟通"],
            "getting_started": ["确定技术栈", "准备项目案例", "注册接单平台", "从小项目开始"],
            "pros": ["收入高", "可积累项目经验", "拓展人脉"],
            "cons": ["时间投入大", "沟通成本高", "可能有尾款风险"]
        },
        {
            "title": "在线教育", "category": "教育",
            "description": "录制或直播教授专业技能课程",
            "income_min": 4000, "income_max": 30000, "hours_per_week": 10,
            "startup_cost": 1000, "difficulty_level": 3,
            "platforms": ["网易云课堂", "腾讯课堂", "Udemy", "B站", "知识星球"],
            "skills_required": ["专业知识", "教学能力", "视频制作"],
            "getting_started": ["确定教学方向", "准备课程大纲", "录制试听课程", "发布并推广"],
            "pros": ["被动收入", "可积累影响力", "时间灵活"],
            "cons": ["前期投入大", "需要专业能力", "竞争激烈"]
        },
        {
            "title": "电商代运营", "category": "电商",
            "description": "帮助商家运营淘宝、拼多多等店铺",
            "income_min": 5000, "income_max": 25000, "hours_per_week": 15,
            "startup_cost": 0, "difficulty_level": 3,
            "platforms": ["淘宝", "拼多多", "京东", "抖音电商"],
            "skills_required": ["电商运营", "数据分析", "营销推广"],
            "getting_started": ["学习电商运营", "积累实操经验", "寻找合作商家", "签订合作协议"],
            "pros": ["收入稳定", "可积累经验", "市场需求大"],
            "cons": ["需要经验", "责任大", "可能有纠纷"]
        },
        {
            "title": "自媒体运营", "category": "内容创作",
            "description": "运营微信公众号、知乎等自媒体账号",
            "income_min": 2000, "income_max": 20000, "hours_per_week": 10,
            "startup_cost": 0, "difficulty_level": 2,
            "platforms": ["微信公众号", "知乎", "头条号", "小红书"],
            "skills_required": ["写作", "运营", "SEO", "用户研究"],
            "getting_started": ["确定内容定位", "持续输出内容", "积累粉丝", "探索变现方式"],
            "pros": ["零成本", "时间灵活", "可积累品牌"],
            "cons": ["见效慢", "需要持续更新", "收入不稳定"]
        },
        {
            "title": "翻译", "category": "语言",
            "description": "为企业或个人提供中英文翻译服务",
            "income_min": 3000, "income_max": 15000, "hours_per_week": 10,
            "startup_cost": 0, "difficulty_level": 3,
            "platforms": ["有道翻译", "Gengo", "ProZ", "淘宝", "猪八戒"],
            "skills_required": ["英语", "中文", "翻译技巧", "专业领域知识"],
            "getting_started": ["考取翻译证书", "准备翻译样本", "注册接单平台", "从小单开始"],
            "pros": ["时间灵活", "可积累专业领域", "收入稳定"],
            "cons": ["需要语言能力", "可能枯燥", "AI翻译冲击"]
        },
        {
            "title": "摄影摄像", "category": "创意",
            "description": "为企业或个人提供摄影摄像服务",
            "income_min": 5000, "income_max": 30000, "hours_per_week": 15,
            "startup_cost": 10000, "difficulty_level": 3,
            "platforms": ["淘宝", "小红书", "朋友圈", "本地社群"],
            "skills_required": ["摄影", "后期处理", "沟通", "审美"],
            "getting_started": ["购买设备", "学习摄影技术", "拍摄作品集", "推广获客"],
            "pros": ["收入高", "可发展为事业", "技能可复用"],
            "cons": ["设备投入大", "需要技术", "季节性波动"]
        },
        {
            "title": "线上客服", "category": "服务",
            "description": "为电商平台或企业提供在线客服服务",
            "income_min": 2000, "income_max": 6000, "hours_per_week": 20,
            "startup_cost": 0, "difficulty_level": 1,
            "platforms": ["淘宝", "京东", "拼多多", "58同城"],
            "skills_required": ["沟通能力", "打字速度", "耐心", "产品知识"],
            "getting_started": ["提升打字速度", "了解平台规则", "寻找招聘机会", "接受培训"],
            "pros": ["门槛低", "时间灵活", "收入稳定"],
            "cons": ["收入较低", "工作枯燥", "需要耐心"]
        },
        {
            "title": "知识付费", "category": "教育",
            "description": "通过知识星球、得到等平台分享专业知识",
            "income_min": 3000, "income_max": 50000, "hours_per_week": 8,
            "startup_cost": 0, "difficulty_level": 3,
            "platforms": ["知识星球", "得到", "小报童", "微信"],
            "skills_required": ["专业知识", "写作", "运营", "用户研究"],
            "getting_started": ["确定专业领域", "持续输出内容", "积累粉丝", "设置付费内容"],
            "pros": ["被动收入", "可积累影响力", "时间灵活"],
            "cons": ["需要专业能力", "前期积累慢", "需要持续更新"]
        },
        {
            "title": "代运营小红书", "category": "运营",
            "description": "帮助品牌或个人运营小红书账号",
            "income_min": 3000, "income_max": 15000, "hours_per_week": 10,
            "startup_cost": 0, "difficulty_level": 2,
            "platforms": ["小红书"],
            "skills_required": ["小红书运营", "内容创作", "数据分析", "审美"],
            "getting_started": ["研究小红书算法", "运营自己的账号", "积累案例", "寻找客户"],
            "pros": ["需求大", "时间灵活", "可积累经验"],
            "cons": ["平台规则变化", "需要持续学习", "竞争激烈"]
        },
        {
            "title": "PPT定制", "category": "设计",
            "description": "为企业或个人定制专业PPT",
            "income_min": 2000, "income_max": 10000, "hours_per_week": 10,
            "startup_cost": 0, "difficulty_level": 2,
            "platforms": ["淘宝", "猪八戒", "威客", "朋友圈"],
            "skills_required": ["PPT", "设计", "排版", "逻辑思维"],
            "getting_started": ["提升PPT技能", "准备作品集", "注册接单平台", "从低价单开始"],
            "pros": ["门槛低", "时间灵活", "需求稳定"],
            "cons": ["收入有限", "可能枯燥", "需要耐心"]
        },
        {
            "title": "数据分析接单", "category": "技术",
            "description": "为企业提供数据分析和可视化服务",
            "income_min": 5000, "income_max": 25000, "hours_per_week": 15,
            "startup_cost": 0, "difficulty_level": 3,
            "platforms": ["程序员客栈", "猪八戒", "淘宝", "LinkedIn"],
            "skills_required": ["Python", "SQL", "数据可视化", "Excel"],
            "getting_started": ["提升数据分析能力", "准备项目案例", "注册接单平台", "积极投标"],
            "pros": ["收入高", "可积累经验", "技能可复用"],
            "cons": ["需要专业能力", "沟通成本高", "项目周期不定"]
        },
        {
            "title": "线上家教", "category": "教育",
            "description": "通过线上平台为学生提供辅导服务",
            "income_min": 3000, "income_max": 12000, "hours_per_week": 10,
            "startup_cost": 0, "difficulty_level": 2,
            "platforms": ["VIPKID", "掌门1对1", "作业帮", "网易有道"],
            "skills_required": ["专业知识", "教学能力", "耐心", "沟通"],
            "getting_started": ["确定教学科目", "准备教学资料", "注册平台", "通过面试"],
            "pros": ["时间灵活", "收入稳定", "有意义"],
            "cons": ["需要专业能力", "可能占用周末", "需要耐心"]
        },
    ]

    for job_data in side_jobs_data:
        side_job = SideJob(**job_data)
        db.session.add(side_job)

    db.session.commit()
    print(f'导入 {len(side_jobs_data)} 条副业数据')


def run():
    """执行数据初始化"""
    app = create_app()
    with app.app_context():
        print('开始初始化数据...')

        # 清空现有数据
        JobSkill.query.delete()
        Job.query.delete()
        LearningResource.query.delete()
        Skill.query.delete()
        SkillCategory.query.delete()
        SideJob.query.delete()
        db.session.commit()

        # 导入数据
        init_jobs()
        init_skills()
        init_side_jobs()

        print('数据初始化完成!')


if __name__ == '__main__':
    run()
