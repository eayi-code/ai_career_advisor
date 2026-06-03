"""
档案服务模块
处理用户档案相关的业务逻辑
"""

from app import db
from app.models.profile import UserProfile
from app.models.history import AnalysisHistory


class ProfileService:
    """档案服务类"""
    
    @staticmethod
    def get_profile_completion(user_id):
        """计算档案完善度"""
        try:
            db.session.rollback()
        except Exception:
            pass
        
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        # 字段权重
        field_weights = {
            'education': 5,
            'major': 5,
            'work_experience': 5,
            'current_job_title': 5,
            'skills': 10,
            'target_job_title': 10,
            'target_industry': 5,
            'target_salary_min': 5,
            'location_preference': 5,
            'job_search_status': 5,
            'work_preference': 5,
            'company_type_preference': 5,
            'projects': 10,
            'certifications': 5,
            'career_goals': 5,
        }
        
        total = sum(field_weights.values())
        filled = 0
        missing_fields = []
        
        if profile:
            for field, weight in field_weights.items():
                value = getattr(profile, field, None)
                is_filled = False
                
                if value is not None:
                    if isinstance(value, list) and len(value) > 0:
                        is_filled = True
                    elif isinstance(value, str) and value.strip():
                        is_filled = True
                    elif isinstance(value, (int, float)) and value > 0:
                        is_filled = True
                
                if is_filled:
                    filled += weight
                else:
                    missing_fields.append(field)
        
        completion = int(filled / total * 100)
        
        return {
            "completion": completion,
            "filled": filled,
            "total": total,
            "missing_fields": missing_fields
        }
    
    @staticmethod
    def get_milestones(user_id):
        """获取决策里程碑（对话成果）"""
        try:
            db.session.rollback()
        except Exception:
            pass
        
        histories = AnalysisHistory.query.filter_by(
            user_id=user_id
        ).order_by(AnalysisHistory.updated_at.desc()).limit(20).all()
        
        milestones = []
        for h in histories:
            achievements = ProfileService._extract_achievements(h)
            if achievements:
                milestones.append({
                    "conversation_id": h.conversation_id,
                    "date": h.updated_at.strftime('%m-%d') if h.updated_at else h.created_at.strftime('%m-%d'),
                    "agent": h.agent_used,
                    "title": achievements[0],
                    "achievements": achievements
                })
        
        return milestones
    
    @staticmethod
    def get_next_actions(user_id):
        """获取Next Action动态建议"""
        try:
            db.session.rollback()
        except Exception:
            pass
        
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        # 获取对话历史
        histories = AnalysisHistory.query.filter_by(
            user_id=user_id
        ).order_by(AnalysisHistory.updated_at.desc()).limit(20).all()
        
        # 分析用户状态
        actions = []
        used_agents = set()
        has_resume = False
        has_target_job = False
        has_skill_analysis = False
        has_interview_prep = False
        
        # 分析对话历史中的成就
        for h in histories:
            agent = h.agent_used or ''
            used_agents.add(agent)
            output = (h.result_data or {}).get('output', '')
            
            if agent == 'resume' or '简历' in output:
                if 'RESUME_START' in output or '个人简介' in output:
                    has_resume = True
            if agent == 'skill' or '差距' in output or '学习路径' in output:
                has_skill_analysis = True
            if agent == 'interview' or '面试题' in output or '自我介绍' in output:
                has_interview_prep = True
        
        # 检查档案状态
        has_skills = False
        has_projects = False
        has_career_goals = False
        
        if profile:
            has_target_job = bool(profile.target_job_title)
            has_skills = bool(profile.skills and len(profile.skills) > 0)
            has_projects = bool(profile.projects and len(profile.projects) > 0)
            has_career_goals = bool(profile.career_goals and profile.career_goals.strip())
        
        # 生成建议
        if not has_target_job:
            actions.append({
                "id": "set_target",
                "title": "设定职业目标",
                "desc": "明确您的目标职位，获得更精准的建议",
                "icon": "target",
                "color": "#3b82f6",
                "action": "chat",
                "target": "帮我确定目标岗位",
                "priority": 1
            })
        
        if not has_skills:
            actions.append({
                "id": "add_skills",
                "title": "添加技能清单",
                "desc": "记录您的技能，便于差距分析和学习规划",
                "icon": "skill",
                "color": "#8b5cf6",
                "action": "scroll",
                "target": "#careerProfile",
                "priority": 2
            })
        
        if has_skills and not has_skill_analysis:
            actions.append({
                "id": "analyze_skills",
                "title": "分析技能差距",
                "desc": "了解目标职位所需的技能，找到提升方向",
                "icon": "chart",
                "color": "#8b5cf6",
                "action": "chat",
                "target": "分析技能差距",
                "priority": 3
            })
        
        if not has_resume:
            actions.append({
                "id": "create_resume",
                "title": "生成专业简历",
                "desc": "根据您的档案自动生成简历",
                "icon": "resume",
                "color": "#ec4899",
                "action": "chat",
                "target": "帮我生成简历",
                "priority": 4
            })
        
        if has_target_job and not has_interview_prep:
            actions.append({
                "id": "interview_prep",
                "title": "准备面试",
                "desc": "获取面试题库和模拟练习",
                "icon": "interview",
                "color": "#f59e0b",
                "action": "chat",
                "target": "帮我准备面试",
                "priority": 5
            })
        
        if not has_projects:
            actions.append({
                "id": "add_projects",
                "title": "记录项目经验",
                "desc": "添加您的项目经历，丰富个人档案",
                "icon": "project",
                "color": "#3b82f6",
                "action": "scroll",
                "target": "#careerProfile",
                "priority": 6
            })
        
        if not has_career_goals:
            actions.append({
                "id": "career_goals",
                "title": "明确职业规划",
                "desc": "设定短期和长期的职业发展目标",
                "icon": "goal",
                "color": "#3b82f6",
                "action": "scroll",
                "target": "#careerProfile",
                "priority": 7
            })
        
        # 如果没有特别缺的，推荐副业探索
        if len(actions) <= 2:
            actions.append({
                "id": "explore_sidejob",
                "title": "探索副业机会",
                "desc": "发现适合您的副业，拓展收入来源",
                "icon": "money",
                "color": "#f59e0b",
                "action": "chat",
                "target": "推荐副业",
                "priority": 8
            })
        
        # 按优先级排序
        actions.sort(key=lambda x: x.get('priority', 99))
        
        return actions[:4]
    
    @staticmethod
    def update_profile(user_id, data):
        """更新用户档案"""
        try:
            profile = UserProfile.query.filter_by(user_id=user_id).first()
            
            if not profile:
                profile = UserProfile(user_id=user_id)
                db.session.add(profile)
            
            # 更新字段
            field_mapping = {
                'education': str,
                'major': str,
                'work_experience': str,
                'current_job_title': str,
                'skills': list,
                'target_job_title': str,
                'target_industry': str,
                'target_salary_min': int,
                'target_salary_max': int,
                'location_preference': str,
                'job_search_status': str,
                'work_preference': str,
                'company_type_preference': str,
                'projects': list,
                'certifications': list,
                'career_goals': str,
            }
            
            for field, field_type in field_mapping.items():
                if field in data:
                    value = data[field]
                    if field_type == list and isinstance(value, list):
                        setattr(profile, field, value)
                    elif field_type == str:
                        setattr(profile, field, str(value) if value else None)
                    elif field_type == int:
                        try:
                            setattr(profile, field, int(value) if value else None)
                        except (ValueError, TypeError):
                            pass
            
            db.session.commit()
            return {"success": True, "message": "档案更新成功"}
            
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _extract_achievements(history):
        """从对话历史中提取成就"""
        achievements = []
        
        if not history.result_data:
            return achievements
        
        output = history.result_data.get('output', '')
        agent = history.agent_used or ''
        
        # 根据不同Agent类型提取关键信息
        if agent == 'career':
            if '目标' in output or '推荐' in output:
                # 提取第一个有意义的段落
                lines = output.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 15 and not line.startswith('#') and not line.startswith('*'):
                        achievements.append(line[:80])
                        break
        
        elif agent == 'skill':
            if '学习路径' in output or '技能' in output:
                lines = output.split('\n')
                for line in lines:
                    line = line.strip()
                    if '学习' in line or '掌握' in line or '提升' in line:
                        achievements.append(line[:80])
                        break
        
        elif agent == 'resume':
            if '简历' in output:
                achievements.append('已生成专业简历')
        
        elif agent == 'interview':
            if '面试' in output:
                achievements.append('已完成面试准备')
        
        elif agent == 'side_job':
            if '副业' in output or '收入' in output:
                lines = output.split('\n')
                for line in lines:
                    line = line.strip()
                    if '推荐' in line or '副业' in line:
                        achievements.append(line[:80])
                        break
        
        return achievements[:3]
