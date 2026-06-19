"""多智能体编排器 - 完美版

核心改进：
1. DAG依赖图解析 - 支持复杂依赖关系
2. 共享上下文机制 - Agent间数据共享
3. 智能意图识别 - 结合用户档案和对话历史
4. 智能结果合并 - LLM整合多Agent输出
5. 增强错误恢复 - 降级策略和备选方案
6. 增强质量评估 - 多维度质量检查
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from enum import Enum
from app.agents.career_agent import CareerAgent, SkillAgent, SideJobAgent, ResumeAgent, InterviewAgent
from app.agents.base_agent import ClientDisconnectedError
from app.memory.long_term import LongTermMemory
from langchain_openai import ChatOpenAI
from flask import current_app
import json
import time


# ==================== 数据结构定义 ====================

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEGRADED = "degraded"  # 降级执行


@dataclass
class ExecutionStep:
    """执行步骤"""
    step_id: int
    step_type: str  # intent_analysis, task_split, agent_call, quality_check, result_merge, error_recovery
    title: str
    detail: str
    agent: str = ""
    status: str = TaskStatus.PENDING.value
    output: str = ""
    duration: float = 0
    quality_score: int = 0
    error_msg: str = ""


@dataclass
class SubTask:
    """子任务定义"""
    task_id: str
    agent: str
    task: str
    order: int = 0
    depends_on: List[str] = field(default_factory=list)
    priority: int = 1  # 1=高, 2=中, 3=低
    timeout: int = 120  # 超时秒数
    can_parallel: bool = True  # 是否可并行
    fallback_agent: str = ""  # 降级Agent


@dataclass
class AgentResult:
    """Agent执行结果"""
    task_id: str
    agent: str
    success: bool
    output: str = ""
    error: str = ""
    duration: float = 0
    quality_score: int = 0
    tools_used: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class SharedContext:
    """共享上下文 - Agent间数据共享"""
    user_id: int
    user_input: str
    user_profile: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict] = field(default_factory=list)
    agent_outputs: Dict[str, str] = field(default_factory=dict)  # agent_name -> output
    extracted_info: Dict[str, Any] = field(default_factory=dict)  # 提取的用户信息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    def get_agent_output(self, agent_name: str) -> str:
        """获取指定Agent的输出"""
        return self.agent_outputs.get(agent_name, "")

    def get_all_outputs(self) -> Dict[str, str]:
        """获取所有Agent输出"""
        return self.agent_outputs.copy()

    def add_agent_output(self, agent_name: str, output: str):
        """添加Agent输出"""
        self.agent_outputs[agent_name] = output

    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        parts = []
        if self.user_profile:
            parts.append(f"用户档案: {json.dumps(self.user_profile, ensure_ascii=False, indent=2)}")
        if self.agent_outputs:
            outputs_summary = "\n".join([f"- {name}: {output[:200]}..." for name, output in self.agent_outputs.items()])
            parts.append(f"已完成的分析:\n{outputs_summary}")
        return "\n\n".join(parts)


# ==================== DAG依赖图解析器 ====================

class DAGResolver:
    """DAG依赖图解析器"""

    def __init__(self, tasks: List[SubTask]):
        self.tasks = {t.task_id: t for t in tasks}
        self.graph: Dict[str, Set[str]] = defaultdict(set)  # task_id -> 依赖它的task_ids
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # task_id -> 它依赖的task_ids
        self._build_graph()

    def _build_graph(self):
        """构建依赖图"""
        for task in self.tasks.values():
            # 确保task_id在图中存在
            if task.task_id not in self.graph:
                self.graph[task.task_id] = set()
            for dep_id in task.depends_on:
                if dep_id in self.tasks:
                    self.graph[dep_id].add(task.task_id)  # dep_id -> task_id (dep_id完成后才能执行task_id)
                    self.reverse_graph[task.task_id].add(dep_id)  # task_id依赖dep_id

    def get_execution_layers(self) -> List[List[str]]:
        """获取执行层级（拓扑排序）"""
        # 计算入度 - 确保所有task都在in_degree中
        in_degree = {}
        for task_id in self.tasks:
            in_degree[task_id] = len(self.reverse_graph.get(task_id, set()))

        layers = []
        while True:
            # 找出所有入度为0的节点
            ready = [task_id for task_id, degree in in_degree.items() if degree == 0]
            if not ready:
                break

            layers.append(ready)

            # 移除已处理的节点
            for task_id in ready:
                del in_degree[task_id]
                for dependent in self.graph[task_id]:
                    if dependent in in_degree:
                        in_degree[dependent] -= 1

        # 检查是否有循环依赖
        if in_degree:
            raise ValueError(f"检测到循环依赖: {list(in_degree.keys())}")

        return layers

    def get_parallel_groups(self) -> List[List[str]]:
        """获取可并行执行的任务组"""
        layers = self.get_execution_layers()
        parallel_groups = []

        for layer in layers:
            # 检查每个任务是否可并行
            parallel_tasks = []
            serial_tasks = []

            for task_id in layer:
                task = self.tasks[task_id]
                if task.can_parallel and len(layer) > 1:
                    parallel_tasks.append(task_id)
                else:
                    serial_tasks.append(task_id)

            if parallel_tasks:
                parallel_groups.append(parallel_tasks)
            if serial_tasks:
                for task_id in serial_tasks:
                    parallel_groups.append([task_id])

        return parallel_groups

    def validate(self) -> List[str]:
        """验证依赖图，返回错误信息"""
        errors = []

        # 检查所有依赖是否存在
        for task in self.tasks.values():
            for dep_id in task.depends_on:
                if dep_id not in self.tasks:
                    errors.append(f"任务 {task.task_id} 依赖的 {dep_id} 不存在")

        # 检查循环依赖
        try:
            self.get_execution_layers()
        except ValueError as e:
            errors.append(str(e))

        return errors


# ==================== 智能意图识别器 ====================

class IntentClassifier:
    """智能意图识别器 - 性能优化版

    优化点：
    1. 意图缓存：相同输入直接返回缓存结果，避免重复计算
    2. 提高置信度阈值：从0.25提高到0.4，减少不必要的LLM调用
    3. 主意图优先逻辑：某个意图明显领先时直接使用，不调用LLM
    4. 优化关键词权重：提高区分度
    """

    def __init__(self):
        # 意图缓存（最近100条）
        self._intent_cache = {}
        self._cache_max_size = 100

        self.keyword_weights = {
            "career": {
                "high": ["职业", "工作", "岗位", "求职", "offer", "公司", "就业", "全职", "薪资", "工资", "待遇", "发展前景",
                         "职位", "应聘", "投简历", "找工作", "转行", "跳槽", "换工作", "行业", "方向"],
                "medium": ["招聘", "入职", "晋升", "升职", "职业规划", "职业发展", "就业形势", "就业市场",
                           "大厂", "外企", "国企", "创业公司", "互联网", "金融"],
                "low": ["发展", "前景", "规划", "方向", "前途", "出路", "未来", "选择"]
            },
            "side_job": {
                "high": ["副业", "兼职", "赚钱", "额外收入", "自由职业", "接单", "外快", "变现",
                         "第二职业", "斜杠", "在家赚钱", "业余收入", "被动收入"],
                "medium": ["远程工作", "居家办公", "网赚", "自媒体", "电商", "带货", "直播",
                           "知识付费", "课程变现", "技术接单", "外包"],
                "low": ["投资", "理财", "收入", "赚点钱", "零花钱", "补贴"]
            },
            "skill": {
                "high": ["技能", "学习", "提升", "差距", "培训", "课程", "学什么", "学哪些",
                         "学习路径", "学习计划", "怎么学", "从哪学"],
                "medium": ["能力", "技术栈", "知识", "入门", "进阶", "教程", "学多久",
                           "难度", "难学", "好学", "速成", "精通"],
                "low": ["成长", "进步", "掌握", "学会", "练习", "实践"]
            },
            "resume": {
                "high": ["简历", "resume", "CV", "履历", "求职信", "cover letter", "简历优化", "简历修改",
                         "写简历", "改简历", "简历模板", "简历生成"],
                "medium": ["优化简历", "ATS", "简历评分", "简历解析", "简历建议", "简历怎么写",
                           "工作经历", "项目经历", "个人简介", "自我评价"],
                "low": ["格式", "排版", "美化"]
            },
            "interview": {
                "high": ["面试", "自我介绍", "面试题", "薪资谈判", "offer谈判", "面试准备",
                         "模拟面试", "面试练习", "面试技巧"],
                "medium": ["二面", "终面", "HR面", "技术面", "面试问题", "怎么面试",
                           "面试经验", "面试流程", "群面", "无领导小组"],
                "low": ["面试结果", "面试问什么", "穿什么", "注意什么"]
            }
        }
        
        # Agent优先级（当多个Agent匹配度相同时，按此优先级选择）
        self.agent_priority = ["career", "resume", "interview", "skill", "side_job"]
        
        # 上下文关联规则：用户说某些词时，可能需要切换Agent
        self.context_switch_triggers = {
            "career_to_resume": ["帮我写简历", "生成简历", "简历优化", "针对这个岗位"],
            "career_to_interview": ["面试准备", "面试题", "自我介绍", "怎么面试"],
            "career_to_skill": ["技能差距", "需要学什么", "学习路径", "怎么提升"],
            "resume_to_career": ["这个岗位", "薪资多少", "发展前景", "其他岗位"],
            "interview_to_career": ["这个公司", "岗位要求", "行业前景"],
        }

    def classify_keywords(self, user_input: str, context: str = "") -> Dict[str, Dict]:
        """关键词匹配，返回所有意图及置信度"""
        full_input = f"{context} {user_input}".lower()
        scores = {}

        for agent_name, keywords in self.keyword_weights.items():
            score = 0
            matched_keywords = []
            for kw in keywords["high"]:
                if kw in full_input:
                    score += 3
                    matched_keywords.append(kw)
            for kw in keywords["medium"]:
                if kw in full_input:
                    score += 2
                    matched_keywords.append(kw)
            for kw in keywords["low"]:
                if kw in full_input:
                    score += 1
                    matched_keywords.append(kw)
            if score > 0:
                scores[agent_name] = {"score": score, "keywords": matched_keywords}

        return scores

    def classify_with_llm(self, user_input: str, user_profile: Dict = None) -> Dict[str, Any]:
        """使用LLM进行复合意图识别（优化版：精简prompt减少token消耗）"""
        try:
            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0
            )

            # 优化：只传递关键字段，减少token消耗
            profile_context = ""
            if user_profile:
                key_fields = {}
                if user_profile.get("target_job_title"):
                    key_fields["目标岗位"] = user_profile["target_job_title"]
                if user_profile.get("skills"):
                    key_fields["技能"] = user_profile["skills"][:5]  # 最多5个技能
                if user_profile.get("work_experience"):
                    key_fields["工作年限"] = user_profile["work_experience"]
                if key_fields:
                    profile_context = f"\n用户背景：{json.dumps(key_fields, ensure_ascii=False)}"

            prompt = f"""分析用户问题涉及哪些任务类别。

类别：career(职业/求职), skill(技能/学习), side_job(副业/兼职), resume(简历), interview(面试)
{profile_context}

问题：{user_input}

返回JSON：
{{"intents": ["类别"], "reasoning": "理由", "confidence": 0.9}}

规则：intents可含1-3个类别。只返回JSON。"""

            response = llm.invoke(prompt)
            content = response.content.strip()
            
            # 尝试提取JSON（可能被包裹在```json ... ```中）
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                content = json_match.group(1).strip()
            
            # 尝试解析JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # 尝试找到第一个{和最后一个}
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1 and end > start:
                    result = json.loads(content[start:end+1])
                else:
                    raise ValueError(f"无法解析JSON: {content[:100]}")

            # 验证和清理
            valid_agents = ["career", "skill", "side_job", "resume", "interview"]
            intents = [i for i in result.get("intents", ["career"]) if i in valid_agents]
            subtasks = [t for t in result.get("subtasks", []) if t.get("agent") in valid_agents]

            return {
                "intents": intents or ["career"],
                "reasoning": result.get("reasoning", ""),
                "confidence": result.get("confidence", 0.8),
                "subtasks": subtasks,
                "user_intent_summary": result.get("user_intent_summary", "")
            }

        except Exception as e:
            print(f"LLM意图识别失败: {e}")
            return {"intents": ["career"], "reasoning": f"识别失败: {str(e)}", "confidence": 0.5, "subtasks": []}

    def classify(self, user_input: str, context: str = "", user_profile: Dict = None, 
                 last_agent: str = None, conversation_history: List = None) -> Dict[str, Any]:
        """综合意图识别 - 性能优化版

        优化点：
        1. 意图缓存：相同输入直接返回缓存结果
        2. 提高置信度阈值：从0.25→0.4，减少不必要的LLM调用
        3. 主意图优先：某个意图置信度>55%时直接使用，不调用LLM
        """
        # ===== 缓存检查 =====
        cache_key = f"{user_input.strip()}|{last_agent or ''}"
        if cache_key in self._intent_cache:
            cached = self._intent_cache[cache_key]
            # 深拷贝避免修改缓存
            import copy
            return copy.deepcopy(cached)

        # ===== 第一步：关键词匹配 =====
        scores = self.classify_keywords(user_input, context)
        
        # ===== 第二步：检查是否需要Agent切换（基于上下文）=====
        if last_agent and conversation_history:
            switch_result = self._check_context_switch(user_input, last_agent, conversation_history)
            if switch_result:
                # 上下文切换信号强，优先使用切换后的Agent
                scores[switch_result] = scores.get(switch_result, {"score": 0, "keywords": []})
                scores[switch_result]["score"] += 5  # 给上下文切换加分
                scores[switch_result]["keywords"].append("上下文切换")

        # ===== 检查用户档案，判断是否需要前置任务 =====
        need_career_prefix = False
        if user_profile:
            has_target_job = bool(user_profile.get("target_job_title"))
            if not has_target_job and "resume" in scores:
                need_career_prefix = True
            if not has_target_job and "interview" in scores:
                need_career_prefix = True

        # ===== 未匹配到关键词 =====
        if not scores:
            if last_agent:
                result = {
                    "intents": [last_agent],
                    "is_composite": False,
                    "confidence": 0.6,
                    "reasoning": f"继续使用{last_agent} Agent处理",
                    "scores": {},
                    "subtasks": []
                }
            else:
                result = {
                    "intents": ["career"],
                    "is_composite": False,
                    "confidence": 0.5,
                    "reasoning": "未匹配到关键词，默认使用职业规划",
                    "scores": {},
                    "subtasks": []
                }
            # 缓存结果
            self._cache_intent(cache_key, result)
            return result

        # ===== 计算总分和高置信度意图 =====
        total = sum(s["score"] for s in scores.values())
        high_confidence = []
        for name, data in scores.items():
            confidence = data["score"] / total
            # 优化：提高阈值从0.25到0.4，减少被识别为"高置信度"的意图数量
            if confidence >= 0.4:
                high_confidence.append({"name": name, "confidence": confidence, "keywords": data["keywords"]})
        
        # 按分数排序
        high_confidence.sort(key=lambda x: x["confidence"], reverse=True)

        # 如果需要添加career前置
        if need_career_prefix and "career" not in scores:
            scores["career"] = {"score": 2, "keywords": ["目标岗位"]}
            high_confidence.insert(0, {"name": "career", "confidence": 0.3, "keywords": ["目标岗位"]})

        # ===== 优化：主意图优先逻辑 =====
        # 如果第一个意图的置信度明显高于第二个（>55%且领先15%以上），直接使用，不调用LLM
        if len(high_confidence) >= 2:
            top = high_confidence[0]
            second = high_confidence[1]
            if top["confidence"] >= 0.55 and (top["confidence"] - second["confidence"]) >= 0.15:
                # 主意图明确，直接使用
                result = {
                    "intents": [top["name"]],
                    "is_composite": False,
                    "confidence": top["confidence"],
                    "reasoning": f"主意图明确: {top['name']}({top['confidence']:.0%})",
                    "scores": scores,
                    "subtasks": []
                }
                self._cache_intent(cache_key, result)
                return result

        # ===== 多个高置信度意图，使用LLM确认 =====
        if len(high_confidence) >= 2:
            try:
                llm_result = self.classify_with_llm(user_input, user_profile)
                
                # 如果需要添加career前置
                if need_career_prefix and "career" not in llm_result["intents"]:
                    llm_result["intents"] = ["career"] + llm_result["intents"]
                
                result = {
                    "intents": llm_result["intents"],
                    "is_composite": len(llm_result["intents"]) > 1,
                    "confidence": llm_result.get("confidence", 0.8),
                    "reasoning": llm_result.get("reasoning", "复合意图识别"),
                    "scores": scores,
                    "subtasks": llm_result.get("subtasks", []),
                    "user_intent_summary": llm_result.get("user_intent_summary", "")
                }
                self._cache_intent(cache_key, result)
                return result
            except Exception as e:
                # LLM调用失败，使用关键词匹配结果
                print(f"LLM复合意图识别失败，使用关键词结果: {e}")
                # 只取前两个最相关的意图
                intents = [h["name"] for h in high_confidence[:2]]
                result = {
                    "intents": intents,
                    "is_composite": len(intents) > 1,
                    "confidence": 0.7,
                    "reasoning": f"关键词匹配: {', '.join(intents)}",
                    "scores": scores,
                    "subtasks": []
                }
                self._cache_intent(cache_key, result)
                return result

        # ===== 单意图 =====
        best = max(scores.items(), key=lambda x: x[1]["score"])

        # 如果是resume/interview但没有目标岗位，转为复合意图
        if best[0] in ["resume", "interview"] and need_career_prefix:
            result = {
                "intents": ["career", best[0]],
                "is_composite": True,
                "confidence": 0.8,
                "reasoning": f"用户请求{best[0]}服务但未确定目标岗位，需要先进行职业规划",
                "scores": scores,
                "subtasks": []
            }
            self._cache_intent(cache_key, result)
            return result

        result = {
            "intents": [best[0]],
            "is_composite": False,
            "confidence": best[1]["score"] / total if total > 0 else 0.5,
            "reasoning": f"匹配关键词: {', '.join(best[1]['keywords'][:3])}",
            "scores": scores,
            "subtasks": []
        }
        self._cache_intent(cache_key, result)
        return result

    def _cache_intent(self, key: str, result: Dict[str, Any]):
        """缓存意图识别结果"""
        # 缓存满时清除最早的条目
        if len(self._intent_cache) >= self._cache_max_size:
            # 删除第一个条目（FIFO）
            first_key = next(iter(self._intent_cache))
            del self._intent_cache[first_key]
        import copy
        self._intent_cache[key] = copy.deepcopy(result)
    
    def _check_context_switch(self, user_input: str, last_agent: str, 
                              conversation_history: List) -> Optional[str]:
        """检查是否需要根据上下文切换Agent"""
        user_input_lower = user_input.lower()
        
        # 检查切换触发词
        for trigger_key, triggers in self.context_switch_triggers.items():
            from_agent, to_agent = trigger_key.split("_to_")
            if from_agent == last_agent:
                for trigger in triggers:
                    if trigger in user_input_lower:
                        return to_agent
        
        # 基于对话历史的智能判断
        if conversation_history:
            # 如果用户之前在做职业规划，现在问"这个岗位"相关问题
            if last_agent == "career" and any(kw in user_input_lower for kw in ["这个岗位", "这个职位", "这个公司"]):
                return "career"  # 继续使用career
            
            # 如果用户之前在做简历，现在问薪资相关
            if last_agent == "resume" and any(kw in user_input_lower for kw in ["薪资", "工资", "待遇"]):
                return "career"  # 切换到career
        
        return None


# ==================== 结果合并器 ====================

class ResultMerger:
    """智能结果合并器"""

    def __init__(self):
        pass

    def merge_with_llm(self, results: List[AgentResult], user_input: str, context: SharedContext, on_token_callback=None) -> str:
        """使用LLM智能合并多个Agent的结果"""
        if not results:
            return "抱歉，处理失败，请重试。"

        if len(results) == 1:
            return results[0].output

        try:
            callbacks = []
            if on_token_callback:
                from app.agents.base_agent import TokenStreamingHandler
                callbacks.append(TokenStreamingHandler(on_token_callback))

            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0.7,
                streaming=bool(on_token_callback),
                callbacks=callbacks
            )

            # 构建Agent输出摘要
            outputs_summary = []
            for r in results:
                if r.success and r.output:
                    agent_names = {
                        "career": "职业规划顾问",
                        "skill": "技能发展顾问",
                        "side_job": "副业规划专家",
                        "resume": "简历优化专家",
                        "interview": "面试教练"
                    }
                    agent_name = agent_names.get(r.agent, r.agent)
                    outputs_summary.append(f"【{agent_name}的分析】\n{r.output}")

            if not outputs_summary:
                return "抱歉，处理失败，请重试。"

            if len(outputs_summary) == 1:
                return outputs_summary[0].split("\n", 1)[-1] if "\n" in outputs_summary[0] else outputs_summary[0]

            prompt = f"""整合多个顾问的分析结果为一个连贯回复。

用户问题：{user_input}

分析结果：
{chr(10).join(outputs_summary)}

要求：
1. 保留核心观点，消除重复
2. 按逻辑顺序组织（职业规划→技能分析→简历建议）
3. 使用Markdown格式增强可读性
4. 在最后添加综合建议

直接返回整合内容，不要前缀。"""

            response = llm.invoke(prompt)
            # 始终返回合并后的内容，确保内容能被保存到数据库
            return response.content.strip()

        except Exception as e:
            print(f"LLM合并失败: {e}")
            # 降级为简单拼接
            return self.merge_simple(results)

    def merge_simple(self, results: List[AgentResult]) -> str:
        """简单合并（降级方案）"""
        outputs = []
        for r in results:
            if r.success and r.output:
                outputs.append(r.output)

        if not outputs:
            return "抱歉，处理失败，请重试。"

        if len(outputs) == 1:
            return outputs[0]

        merged = "以下是综合分析结果：\n\n"
        for i, output in enumerate(outputs, 1):
            merged += f"---\n\n{output}\n\n"

        return merged


# ==================== 质量评估器 ====================

class QualityAssessor:
    """质量评估器"""

    def __init__(self):
        self.min_length = 20
        self.max_retries = 2

    def assess(self, output: str, agent_name: str, task: str = "") -> Dict[str, Any]:
        """评估输出质量"""
        if not output:
            return {"ok": False, "score": 0, "msg": "输出为空", "issues": ["empty_output"]}

        issues = []
        score = 50  # 基础分

        # 长度检查
        if len(output) < self.min_length:
            issues.append("too_short")
            score -= 30
        elif len(output) > 100:
            score += 10
        elif len(output) > 300:
            score += 10

        # 错误关键词检查
        error_patterns = ["抱歉", "无法", "失败", "错误", "不支持", "暂不支持"]
        error_count = sum(1 for pattern in error_patterns if pattern in output)
        if error_count > 0 and len(output) < 100:
            issues.append("contains_errors")
            score -= 20

        # 格式化检查（Markdown格式加分）
        format_indicators = ["**", "- ", "1. ", "##", "|"]
        format_count = sum(1 for indicator in format_indicators if indicator in output)
        if format_count > 0:
            score += min(format_count * 5, 15)

        # 内容相关性检查（简单）
        relevance_keywords = ["建议", "推荐", "分析", "总结", "方案", "策略", "路径"]
        relevance_count = sum(1 for kw in relevance_keywords if kw in output)
        if relevance_count > 0:
            score += min(relevance_count * 5, 15)

        # 任务特定检查
        if agent_name == "resume":
            if "简历" in output or "resume" in output.lower():
                score += 10
        elif agent_name == "interview":
            if "面试" in output or "自我介绍" in output:
                score += 10
        elif agent_name == "career":
            if "岗位" in output or "职业" in output or "薪资" in output:
                score += 10

        # 限制分数范围
        score = max(0, min(100, score))

        return {
            "ok": score >= 40,
            "score": score,
            "msg": self._get_quality_msg(score),
            "issues": issues
        }

    def _get_quality_msg(self, score: int) -> str:
        if score >= 80:
            return "质量优秀"
        elif score >= 60:
            return "质量良好"
        elif score >= 40:
            return "质量合格"
        else:
            return "质量不合格"

    def should_retry(self, assessment: Dict[str, Any]) -> bool:
        """判断是否需要重试"""
        return not assessment["ok"] and assessment["score"] > 20


# ==================== 错误恢复器 ====================

class ErrorRecovery:
    """错误恢复器"""

    def __init__(self):
        self.fallback_strategies = {
            "career": self._career_fallback,
            "skill": self._skill_fallback,
            "side_job": self._side_job_fallback,
            "resume": self._resume_fallback,
            "interview": self._interview_fallback
        }

    def recover(self, agent_name: str, error: str, context: SharedContext) -> Optional[AgentResult]:
        """尝试从错误中恢复"""
        strategy = self.fallback_strategies.get(agent_name)
        if strategy:
            return strategy(error, context)
        return None

    def _career_fallback(self, error: str, context: SharedContext) -> Optional[AgentResult]:
        """职业规划降级策略"""
        # 返回通用建议
        return AgentResult(
            task_id="fallback",
            agent="career",
            success=True,
            output="基于您的问题，建议您：\n1. 明确职业目标和发展方向\n2. 了解目标岗位的技能要求\n3. 制定学习和提升计划\n\n如需更详细的分析，请稍后重试。",
            status=TaskStatus.DEGRADED
        )

    def _skill_fallback(self, error: str, context: SharedContext) -> Optional[AgentResult]:
        """技能分析降级策略"""
        return AgentResult(
            task_id="fallback",
            agent="skill",
            success=True,
            output="技能提升建议：\n1. 确定目标岗位的核心技能\n2. 评估当前技能与目标的差距\n3. 制定学习路径和时间表\n\n如需详细的技能差距分析，请稍后重试。",
            status=TaskStatus.DEGRADED
        )

    def _side_job_fallback(self, error: str, context: SharedContext) -> Optional[AgentResult]:
        """副业分析降级策略"""
        return AgentResult(
            task_id="fallback",
            agent="side_job",
            success=True,
            output="副业选择建议：\n1. 评估可用时间和技能\n2. 选择与主业相关的副业\n3. 从小规模开始尝试\n\n如需详细的副业推荐，请稍后重试。",
            status=TaskStatus.DEGRADED
        )

    def _resume_fallback(self, error: str, context: SharedContext) -> Optional[AgentResult]:
        """简历优化降级策略"""
        return AgentResult(
            task_id="fallback",
            agent="resume",
            success=True,
            output="简历优化建议：\n1. 突出核心技能和成就\n2. 使用量化数据展示成果\n3. 针对目标岗位定制简历\n\n如需详细的简历分析和优化，请稍后重试。",
            status=TaskStatus.DEGRADED
        )

    def _interview_fallback(self, error: str, context: SharedContext) -> Optional[AgentResult]:
        """面试准备降级策略"""
        return AgentResult(
            task_id="fallback",
            agent="interview",
            success=True,
            output="面试准备建议：\n1. 研究公司和岗位要求\n2. 准备STAR法则回答问题\n3. 练习自我介绍和常见问题\n\n如需详细的面试指导，请稍后重试。",
            status=TaskStatus.DEGRADED
        )


# ==================== 增强版编排器 ====================

class AgentOrchestrator:
    """多智能体编排器 - 完美版"""

    def __init__(self, max_workers: int = 3, on_step_callback=None, on_token_callback=None):
        self.agents: Dict[str, Any] = {}
        self.memory = LongTermMemory()
        self.max_workers = max_workers
        self.intent_classifier = IntentClassifier()
        self.result_merger = ResultMerger()
        self.quality_assessor = QualityAssessor()
        self.error_recovery = ErrorRecovery()
        self.on_step_callback = on_step_callback  # 步骤更新回调函数
        self.on_token_callback = on_token_callback  # 流式Token回调函数
        self._initialize_agents()
    
    def _emit_step(self, step_data: Dict[str, Any]):
        """发送步骤更新事件"""
        if self.on_step_callback:
            try:
                self.on_step_callback(step_data)
            except Exception as e:
                print(f"[Orchestrator] 回调函数异常: {e}")

    def _initialize_agents(self):
        """初始化所有Agent"""
        # 传入回调函数给每个Agent
        on_tool_callback = self.on_step_callback
        on_token_callback = self.on_token_callback
        
        self.agents["career"] = CareerAgent(on_tool_callback=on_tool_callback, on_token_callback=on_token_callback)
        self.agents["skill"] = SkillAgent(on_tool_callback=on_tool_callback, on_token_callback=on_token_callback)
        self.agents["side_job"] = SideJobAgent(on_tool_callback=on_tool_callback, on_token_callback=on_token_callback)
        self.agents["resume"] = ResumeAgent(on_tool_callback=on_tool_callback, on_token_callback=on_token_callback)
        self.agents["interview"] = InterviewAgent(on_tool_callback=on_tool_callback, on_token_callback=on_token_callback)

    def _load_user_profile(self, user_id: int) -> Dict[str, Any]:
        """加载用户档案"""
        try:
            from flask_login import current_user
            from app.models.profile import UserProfile
            from app import db

            db.session.rollback()

            if user_id:
                profile = UserProfile.query.filter_by(user_id=user_id).first()
                if profile:
                    return {
                        "target_job_title": profile.target_job_title,
                        "target_jobs": profile.target_jobs or [],
                        "skills": profile.skills or [],
                        "work_experience": profile.work_experience,
                        "education": profile.education,
                        "major": profile.major,
                        "current_job_title": profile.current_job_title,
                        "target_industry": profile.target_industry,
                        "location_preference": profile.location_preference,
                        "target_salary_min": profile.target_salary_min,
                        "target_salary_max": profile.target_salary_max,
                        "job_search_status": profile.job_search_status,
                        "work_preference": profile.work_preference,
                        "company_type_preference": profile.company_type_preference,
                        "projects": profile.projects or [],
                        "certifications": profile.certifications or [],
                        "available_hours_per_week": profile.available_hours_per_week,
                        "side_job_income_target": profile.side_job_income_target,
                        "career_goals": profile.career_goals
                    }
        except Exception as e:
            print(f"加载用户档案失败: {e}")

        return {}

    def _execute_single_agent(self, agent_name: str, task: str, context: SharedContext) -> AgentResult:
        """执行单个Agent任务"""
        task_id = f"{agent_name}_{int(time.time() * 1000)}"
        start_time = time.time()

        if agent_name not in self.agents:
            print(f"[Agent] 错误: 未知的Agent类型 {agent_name}")
            return AgentResult(
                task_id=task_id,
                agent=agent_name,
                success=False,
                error=f"未知的Agent类型: {agent_name}",
                duration=time.time() - start_time,
                status=TaskStatus.FAILED
            )

        try:
            # 构建包含共享上下文的任务描述
            enhanced_task = self._enhance_task_with_context(task, agent_name, context)
            print(f"[Agent] 执行 {agent_name} Agent，任务长度: {len(enhanced_task)}")
            print(f"[Agent] 任务内容预览: {enhanced_task[:200]}...")

            # 临时禁用token回调，避免在复合意图处理中重复发送内容
            original_token_callback = self.agents[agent_name].on_token_callback
            self.agents[agent_name].on_token_callback = None
            
            result = self.agents[agent_name].run(enhanced_task, context.user_id)
            
            # 恢复token回调
            self.agents[agent_name].on_token_callback = original_token_callback
            
            duration = time.time() - start_time
            
            print(f"[Agent] {agent_name} Agent 执行结果: success={result.get('success')}")
            if result.get('error'):
                print(f"[Agent] {agent_name} Agent 错误: {result.get('error')}")
            if result.get('output'):
                print(f"[Agent] {agent_name} Agent 输出长度: {len(result.get('output', ''))}")

            if result.get("success"):
                output = result.get("output", "")
                # 添加到共享上下文
                context.add_agent_output(agent_name, output)

                # 获取完整的工具调用信息
                intermediate_steps = result.get("intermediate_steps", [])

                return AgentResult(
                    task_id=task_id,
                    agent=agent_name,
                    success=True,
                    output=output,
                    duration=duration,
                    tools_used=intermediate_steps,  # 保存完整的工具调用信息
                    status=TaskStatus.COMPLETED
                )
            else:
                return AgentResult(
                    task_id=task_id,
                    agent=agent_name,
                    success=False,
                    error=result.get("error", "未知错误"),
                    duration=duration,
                    status=TaskStatus.FAILED
                )

        except ClientDisconnectedError as e:
            raise e
        except Exception as e:
            print(f"[Agent] {agent_name} Agent 异常: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                from app import db
                db.session.rollback()
            except Exception:
                pass
            return AgentResult(
                task_id=task_id,
                agent=agent_name,
                success=False,
                error=str(e),
                duration=time.time() - start_time,
                status=TaskStatus.FAILED
            )

    def _enhance_task_with_context(self, task: str, agent_name: str, context: SharedContext) -> str:
        """使用共享上下文增强任务描述"""
        parts = [task]

        # 添加用户档案信息
        if context.user_profile:
            profile_summary = self._summarize_profile_for_agent(context.user_profile, agent_name)
            if profile_summary:
                parts.append(f"\n用户档案信息：\n{profile_summary}")

        # 添加其他Agent的输出（如果存在）
        other_outputs = []
        for name, output in context.agent_outputs.items():
            if name != agent_name and output:
                agent_names = {
                    "career": "职业规划",
                    "skill": "技能分析",
                    "side_job": "副业分析",
                    "resume": "简历优化",
                    "interview": "面试准备"
                }
                other_outputs.append(f"【{agent_names.get(name, name)}的分析结果】\n{output[:500]}")

        if other_outputs:
            parts.append(f"\n已完成的分析（供参考）：\n{chr(10).join(other_outputs)}")

        return "\n".join(parts)

    def _summarize_profile_for_agent(self, profile: Dict, agent_name: str) -> str:
        """为特定Agent总结用户档案"""
        relevant_fields = {
            "career": ["target_job_title", "target_jobs", "skills", "work_experience", "education", "current_job_title", "target_industry", "location_preference", "target_salary_min", "target_salary_max", "job_search_status"],
            "skill": ["skills", "target_job_title", "work_experience", "education"],
            "side_job": ["skills", "available_hours_per_week", "side_job_income_target", "work_experience"],
            "resume": ["target_job_title", "skills", "work_experience", "education", "major", "current_job_title", "projects", "certifications"],
            "interview": ["target_job_title", "skills", "work_experience", "education", "current_job_title"]
        }

        fields = relevant_fields.get(agent_name, [])
        summary_parts = []

        for field in fields:
            value = profile.get(field)
            if value:
                if field == "target_salary_min" or field == "target_salary_max":
                    if profile.get("target_salary_min") or profile.get("target_salary_max"):
                        summary_parts.append(f"目标薪资: {profile.get('target_salary_min', 0)}k-{profile.get('target_salary_max', 0)}k")
                elif field == "job_search_status":
                    status_map = {"observing": "观望中", "employed": "在职看机会", "resigned": "已离职", "fresh": "应届生"}
                    summary_parts.append(f"求职状态: {status_map.get(value, value)}")
                elif field == "work_preference":
                    pref_map = {"remote": "远程", "onsite": "坐班", "hybrid": "混合", "flexible": "不限"}
                    summary_parts.append(f"工作偏好: {pref_map.get(value, value)}")
                elif field == "company_type_preference":
                    type_map = {"big_company": "大厂", "startup": "创业公司", "foreign": "外企", "flexible": "不限"}
                    summary_parts.append(f"公司类型偏好: {type_map.get(value, value)}")
                elif isinstance(value, list):
                    if value and isinstance(value[0], dict):
                        # 项目经历等复杂结构
                        items = [item.get("name", str(item)) for item in value[:3]]
                        summary_parts.append(f"{field}: {', '.join(items)}")
                    else:
                        summary_parts.append(f"{field}: {', '.join(str(v) for v in value[:5])}")
                else:
                    summary_parts.append(f"{field}: {value}")

        return "\n".join(summary_parts) if summary_parts else ""

    def _execute_with_retry(self, agent_name: str, task: str, context: SharedContext, max_retries: int = 1) -> AgentResult:
        """带重试的Agent执行"""
        last_result = None

        for attempt in range(max_retries + 1):
            result = self._execute_single_agent(agent_name, task, context)

            if result.success:
                # 评估质量
                quality = self.quality_assessor.assess(result.output, agent_name, task)
                result.quality_score = quality["score"]

                if quality["ok"]:
                    return result

                # 质量不合格，检查是否应该重试
                if attempt < max_retries and self.quality_assessor.should_retry(quality):
                    print(f"Agent {agent_name} 质量不合格（{quality['score']}分），重试 {attempt + 1}/{max_retries}")
                    continue

            last_result = result

            if attempt < max_retries:
                print(f"Agent {agent_name} 执行失败，重试 {attempt + 1}/{max_retries}")
                continue  # 继续重试

        # 所有重试都失败，尝试降级
        if last_result and not last_result.success:
            fallback_result = self.error_recovery.recover(agent_name, last_result.error, context)
            if fallback_result:
                print(f"Agent {agent_name} 使用降级策略")
                return fallback_result

        return last_result or AgentResult(
            task_id=f"{agent_name}_failed",
            agent=agent_name,
            success=False,
            error="执行失败",
            status=TaskStatus.FAILED
        )

    def _try_hardcoded_split(self, user_input: str, intents: List[str], context: SharedContext) -> Optional[List[SubTask]]:
        """尝试硬编码拆分常见复合意图，避免LLM调用

        常见复合意图：
        - career + resume：先确定目标岗位，再生成简历
        - career + interview：先确定目标岗位，再准备面试
        - career + skill：先确定目标岗位，再分析技能差距
        - resume + interview：先优化简历，再准备面试
        """
        intent_set = set(intents)
        has_target_job = bool(context.user_profile.get("target_job_title"))
        tasks = []
        task_id_counter = 0

        def next_task_id():
            nonlocal task_id_counter
            task_id_counter += 1
            return f"task_{task_id_counter}"

        # career + resume
        if intent_set == {"career", "resume"}:
            if not has_target_job:
                # 需要先确定目标岗位
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="career",
                    task="了解用户背景，确定目标岗位",
                    order=1, depends_on=[], can_parallel=False
                ))
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="resume",
                    task="根据目标岗位生成简历",
                    order=2, depends_on=["task_1"], can_parallel=False
                ))
            else:
                # 已有目标岗位，直接生成简历
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="resume",
                    task=f"根据目标岗位'{context.user_profile.get('target_job_title')}'生成简历",
                    order=1, depends_on=[], can_parallel=False
                ))
            return tasks

        # career + interview
        if intent_set == {"career", "interview"}:
            if not has_target_job:
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="career",
                    task="了解用户背景，确定目标岗位",
                    order=1, depends_on=[], can_parallel=False
                ))
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="interview",
                    task="根据目标岗位准备面试",
                    order=2, depends_on=["task_1"], can_parallel=False
                ))
            else:
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="interview",
                    task=f"根据目标岗位'{context.user_profile.get('target_job_title')}'准备面试",
                    order=1, depends_on=[], can_parallel=False
                ))
            return tasks

        # career + skill
        if intent_set == {"career", "skill"}:
            if not has_target_job:
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="career",
                    task="了解用户背景，确定目标岗位",
                    order=1, depends_on=[], can_parallel=False
                ))
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="skill",
                    task="根据目标岗位分析技能差距",
                    order=2, depends_on=["task_1"], can_parallel=False
                ))
            else:
                # 已有目标岗位，可以并行
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="career",
                    task="分析目标岗位的市场情况",
                    order=1, depends_on=[], can_parallel=True
                ))
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="skill",
                    task=f"分析与目标岗位'{context.user_profile.get('target_job_title')}'的技能差距",
                    order=1, depends_on=[], can_parallel=True
                ))
            return tasks

        # resume + interview（无career）
        if intent_set == {"resume", "interview"}:
            tasks.append(SubTask(
                task_id=next_task_id(), agent="resume",
                task="优化简历",
                order=1, depends_on=[], can_parallel=True
            ))
            tasks.append(SubTask(
                task_id=next_task_id(), agent="interview",
                task="准备面试",
                order=1, depends_on=[], can_parallel=True
            ))
            return tasks

        # career + resume + interview（三意图）
        if intent_set == {"career", "resume", "interview"}:
            if not has_target_job:
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="career",
                    task="了解用户背景，确定目标岗位",
                    order=1, depends_on=[], can_parallel=False
                ))
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="resume",
                    task="根据目标岗位生成简历",
                    order=2, depends_on=["task_1"], can_parallel=True
                ))
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="interview",
                    task="根据目标岗位准备面试",
                    order=2, depends_on=["task_1"], can_parallel=True
                ))
            else:
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="resume",
                    task=f"根据目标岗位'{context.user_profile.get('target_job_title')}'生成简历",
                    order=1, depends_on=[], can_parallel=True
                ))
                tasks.append(SubTask(
                    task_id=next_task_id(), agent="interview",
                    task=f"根据目标岗位'{context.user_profile.get('target_job_title')}'准备面试",
                    order=1, depends_on=[], can_parallel=True
                ))
            return tasks

        # 不是常见复合意图，返回None让LLM处理
        return None

    def _split_composite_task(self, user_input: str, intents: List[str], context: SharedContext) -> List[SubTask]:
        """拆分复合任务，生成子任务列表

        优化：常见复合意图直接硬编码拆分，避免LLM调用
        """
        # ===== 常见复合意图硬编码（避免LLM调用）=====
        hardcoded = self._try_hardcoded_split(user_input, intents, context)
        if hardcoded:
            return hardcoded

        # ===== 复杂复合意图使用LLM拆分 =====
        try:
            llm = ChatOpenAI(
                model=current_app.config['OPENAI_MODEL'],
                api_key=current_app.config['OPENAI_API_KEY'],
                base_url=current_app.config['OPENAI_BASE_URL'],
                temperature=0
            )

            # 检查用户档案
            profile_context = ""
            need_career_first = False

            if context.user_profile:
                has_target_job = bool(context.user_profile.get("target_job_title"))
                if has_target_job:
                    profile_context = f"\n用户已确定目标岗位：{context.user_profile.get('target_job_title')}"
                else:
                    if "resume" in intents or "interview" in intents:
                        need_career_first = True
                        profile_context = "\n用户尚未确定目标岗位，需要先进行职业规划"

            agent_names = {
                "career": "职业规划顾问",
                "skill": "技能发展顾问",
                "side_job": "副业规划专家",
                "resume": "简历优化专家",
                "interview": "面试教练"
            }

            agents_str = ", ".join([f"{i}({agent_names.get(i, i)})" for i in intents])

            # 如果需要先确定目标岗位
            if need_career_first and "career" not in intents:
                intents = ["career"] + intents
                agents_str = f"career(职业规划顾问), {agents_str}"

            prompt = f"""拆分用户问题为子任务列表。

可用Agent：{agents_str}
{profile_context}

问题：{user_input}

返回JSON数组：
[{{"task_id":"task_1","agent":"agent_name","task":"子任务描述","order":1,"depends_on":[],"can_parallel":true}}]

规则：
1. 子任务独立可执行
2. 无目标岗位时，简历/面试任务前必须先有career任务
3. depends_on引用其他task_id
4. can_parallel: 无依赖=true，有依赖=false

只返回JSON。"""

            response = llm.invoke(prompt)
            content = response.content.strip()
            
            # 尝试提取JSON（可能被包裹在```json ... ```中）
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                content = json_match.group(1).strip()
            
            # 尝试解析JSON
            try:
                subtasks_data = json.loads(content)
            except json.JSONDecodeError:
                # 尝试找到第一个[和最后一个]
                start = content.find('[')
                end = content.rfind(']')
                if start != -1 and end != -1 and end > start:
                    subtasks_data = json.loads(content[start:end+1])
                else:
                    raise ValueError(f"无法解析JSON: {content[:100]}")

            # 转换为SubTask对象
            valid_agents = ["career", "skill", "side_job", "resume", "interview"]
            subtasks = []

            for task_data in subtasks_data:
                if task_data.get("agent") not in valid_agents:
                    continue

                subtask = SubTask(
                    task_id=task_data.get("task_id", f"task_{len(subtasks) + 1}"),
                    agent=task_data["agent"],
                    task=task_data.get("task", user_input),
                    order=task_data.get("order", len(subtasks) + 1),
                    depends_on=task_data.get("depends_on", []),
                    priority=task_data.get("priority", 1),
                    can_parallel=task_data.get("can_parallel", True),
                    fallback_agent=task_data.get("fallback_agent", "")
                )
                subtasks.append(subtask)

            return subtasks if subtasks else [SubTask(
                task_id="task_1",
                agent=intents[0],
                task=user_input,
                order=1,
                depends_on=[],
                priority=1,
                can_parallel=False
            )]

        except Exception as e:
            print(f"任务拆分失败: {e}")
            return [SubTask(
                task_id="task_1",
                agent=intents[0],
                task=user_input,
                order=1,
                depends_on=[],
                priority=1,
                can_parallel=False
            )]

    def _execute_subtasks(self, subtasks: List[SubTask], context: SharedContext) -> List[AgentResult]:
        """执行子任务（支持DAG依赖）"""
        results = []

        # 构建DAG
        dag = DAGResolver(subtasks)

        # 验证DAG
        errors = dag.validate()
        if errors:
            print(f"DAG验证错误: {errors}")
            # 降级为顺序执行
            for subtask in sorted(subtasks, key=lambda t: t.order):
                result = self._execute_with_retry(subtask.agent, subtask.task, context)
                result.task_id = subtask.task_id
                results.append(result)
            return results

        # 获取并行执行组
        parallel_groups = dag.get_parallel_groups()
        
        # 获取Flask应用对象（用于在线程中创建上下文）
        from flask import current_app
        app = current_app._get_current_object()

        for group in parallel_groups:
            if len(group) == 1:
                # 单个任务，直接执行
                task_id = group[0]
                subtask = dag.tasks[task_id]
                result = self._execute_with_retry(subtask.agent, subtask.task, context)
                result.task_id = task_id
                results.append(result)
            else:
                # 多个任务，并行执行
                def execute_in_context(agent_name, task, ctx, app_obj):
                    """在线程中创建应用上下文并执行"""
                    with app_obj.app_context():
                        return self._execute_with_retry(agent_name, task, ctx)
                
                with ThreadPoolExecutor(max_workers=min(len(group), self.max_workers)) as executor:
                    future_to_task = {}
                    for task_id in group:
                        subtask = dag.tasks[task_id]
                        future = executor.submit(execute_in_context, subtask.agent, subtask.task, context, app)
                        future_to_task[future] = subtask

                    for future in as_completed(future_to_task):
                        subtask = future_to_task[future]
                        try:
                            result = future.result()
                            result.task_id = subtask.task_id
                            results.append(result)
                        except Exception as e:
                            results.append(AgentResult(
                                task_id=subtask.task_id,
                                agent=subtask.agent,
                                success=False,
                                error=str(e),
                                status=TaskStatus.FAILED
                            ))

        return results

    def _extract_user_info(self, user_input: str, user_id: int = None) -> str:
        """从用户输入中提取个人信息并更新到用户档案"""
        if not user_id:
            return ""

        try:
            from flask_login import current_user
            from app.models.profile import UserProfile
            from app import db
            import re

            db.session.rollback()

            profile = UserProfile.query.filter_by(user_id=user_id).first()
            if not profile:
                profile = UserProfile(user_id=user_id)
                db.session.add(profile)

            updated_fields = []

            # 提取技能
            skill_keywords = ["我会", "我懂", "我擅长", "我熟悉", "技能", "掌握"]
            if any(kw in user_input for kw in skill_keywords):
                skills_match = re.search(r'(?:我会|我懂|我擅长|我熟悉|技能[是为：:]|掌握)\s*(.+?)(?:[，。,.]|$)', user_input)
                if skills_match:
                    skills_text = skills_match.group(1)
                    skills = [s.strip() for s in re.split(r'[,，、和与]', skills_text) if s.strip()]
                    if skills:
                        current_skills = profile.skills or []
                        profile.skills = list(set(current_skills + skills))
                        updated_fields.append(f"技能：{', '.join(skills)}")

            # 提取工作年限
            exp_patterns = [
                r'(\d+)\s*年[工作经验]',
                r'[工作经验]\s*(\d+)\s*年',
                r'有\s*(\d+)\s*年'
            ]
            for pattern in exp_patterns:
                exp_match = re.search(pattern, user_input)
                if exp_match:
                    profile.work_experience = int(exp_match.group(1))
                    updated_fields.append(f"工作年限：{exp_match.group(1)}年")
                    break

            # 提取学历
            edu_keywords = {
                "本科": "bachelor",
                "硕士": "master",
                "博士": "doctorate",
                "大专": "associate",
                "高中": "high_school"
            }
            for keyword, value in edu_keywords.items():
                if keyword in user_input:
                    profile.education = value
                    updated_fields.append(f"学历：{keyword}")
                    break

            # 提取专业
            major_match = re.search(r'(?:专业[是为：:]|我是)\s*(.+?)(?:专业|毕业|学生|[，。,.]|$)', user_input)
            if major_match:
                profile.major = major_match.group(1).strip()
                updated_fields.append(f"专业：{profile.major}")

            # 提取当前职位
            job_match = re.search(r'(?:我是|职位[是为：:]|担任)\s*(.+?)(?:工程师|开发|设计师|经理|主管|[，。,.]|$)', user_input)
            if job_match:
                profile.current_job_title = job_match.group(0).strip()
                updated_fields.append(f"当前职位：{profile.current_job_title}")

            # 提取目标岗位
            target_job_patterns = [
                r'(?:目标岗位[是为：:]|想做|想当|想应聘)\s*(.+?)(?:[，。,.]|$)',
                r'(?:我想[成为做当])\s*(.+?)(?:工程师|开发|设计师|经理|主管|[，。,.]|$)'
            ]
            for pattern in target_job_patterns:
                target_match = re.search(pattern, user_input)
                if target_match:
                    target_job = target_match.group(1).strip()
                    if len(target_job) >= 2:
                        profile.target_job_title = target_job
                        from datetime import datetime
                        target_jobs = profile.target_jobs or []
                        existing_titles = [j.get("title") for j in target_jobs]
                        if target_job not in existing_titles:
                            target_jobs.append({
                                "title": target_job,
                                "added_at": datetime.utcnow().isoformat()
                            })
                            profile.target_jobs = target_jobs
                        updated_fields.append(f"目标岗位：{target_job}")
                    break

            # 提取目标行业
            industry_match = re.search(r'(?:目标行业|行业[是为：:])\s*(.+?)(?:[，。,.]|$)', user_input)
            if industry_match:
                profile.target_industry = industry_match.group(1).strip()
                updated_fields.append(f"目标行业：{profile.target_industry}")

            # 提取意向城市
            city_match = re.search(r'(?:意向城市|想去|偏好城市|城市[是为：:])\s*(.+?)(?:[，。,.]|$)', user_input)
            if city_match:
                profile.location_preference = city_match.group(1).strip()
                updated_fields.append(f"意向城市：{profile.location_preference}")

            # 提取证书
            cert_patterns = [
                r'(?:有|考了|拿到|获得)\s*(.+?)(?:证书|认证|资格)',
                r'(?:证书[是为：:])\s*(.+?)(?:[，。,.]|$)'
            ]
            for pattern in cert_patterns:
                cert_match = re.search(pattern, user_input)
                if cert_match:
                    cert = cert_match.group(1).strip()
                    current_certs = profile.certifications or []
                    if cert not in current_certs:
                        current_certs.append(cert)
                        profile.certifications = current_certs
                        updated_fields.append(f"证书：{cert}")
                    break

            # 提取项目经历
            project_match = re.search(r'(?:做过|参与过|负责过)\s*(.+?)(?:项目|系统|平台|应用)', user_input)
            if project_match:
                project_name = project_match.group(1).strip()
                current_projects = profile.projects or []
                existing_names = [p.get("name") for p in current_projects]
                if project_name not in existing_names:
                    current_projects.append({
                        "name": project_name,
                        "role": "",
                        "tech_stack": "",
                        "achievement": ""
                    })
                    profile.projects = current_projects
                    updated_fields.append(f"项目经历：{project_name}")

            # 提取可用时间
            time_match = re.search(r'(?:每周|每天)\s*(?:有|能)\s*(\d+)\s*(?:小时|个小时)', user_input)
            if time_match:
                profile.available_hours_per_week = int(time_match.group(1))
                updated_fields.append(f"每周可用时间：{time_match.group(1)}小时")

            # 提取收入目标
            income_match = re.search(r'(?:月收入|赚|收入)\s*(?:目标[是为：:])?\s*(\d+)\s*(?:元|块)', user_input)
            if income_match:
                profile.side_job_income_target = float(income_match.group(1))
                updated_fields.append(f"副业收入目标：{income_match.group(1)}元")

            if updated_fields:
                db.session.commit()
                return "已自动更新您的职业档案：" + "、".join(updated_fields)

            return ""

        except Exception as e:
            db.session.rollback()
            print(f"提取用户信息失败: {e}")
            return ""

    def process(self, user_input: str, user_id: int = None, force_agent: str = None,
                last_agent: str = None, conversation_history: List = None) -> Dict[str, Any]:
        """处理用户请求 - 主入口（增强版）"""
        start_time = time.time()
        execution_steps = []
        step_id = 0

        # 创建共享上下文
        user_profile = self._load_user_profile(user_id) if user_id else {}
        context = SharedContext(
            user_id=user_id,
            user_input=user_input,
            user_profile=user_profile
        )

        # 步骤1：意图分析
        step_id += 1
        if force_agent:
            intent_result = {
                "intents": [force_agent],
                "is_composite": False,
                "confidence": 1.0,
                "reasoning": f"用户指定使用 {force_agent} Agent",
                "subtasks": []
            }
        else:
            intent_result = self.intent_classifier.classify(
                user_input, 
                user_profile=user_profile,
                last_agent=last_agent,
                conversation_history=conversation_history
            )

        intents = intent_result["intents"]
        is_composite = intent_result["is_composite"]

        agent_names = {
            "career": "职业规划顾问",
            "skill": "技能发展顾问",
            "side_job": "副业规划专家",
            "resume": "简历优化专家",
            "interview": "面试教练"
        }

        intent_step = {
            "step_id": step_id,
            "type": "intent_analysis",
            "title": "意图分析",
            "detail": f"识别到{'复合' if is_composite else '单'}意图：{', '.join([agent_names.get(i, i) for i in intents])}",
            "intents": intents,
            "is_composite": is_composite,
            "confidence": intent_result.get("confidence", 0),
            "reasoning": intent_result.get("reasoning", ""),
            "user_intent_summary": intent_result.get("user_intent_summary", ""),
            "status": TaskStatus.COMPLETED.value
        }
        execution_steps.append(intent_step)
        self._emit_step(intent_step)

        # 单Agent处理
        if not is_composite:
            agent_name = intents[0]

            # 步骤2：Agent调用
            step_id += 1
            agent_call_step = {
                "step_id": step_id,
                "type": "agent_call",
                "title": f"调用{agent_names.get(agent_name, agent_name)}",
                "detail": f"正在执行任务...",
                "agent": agent_name,
                "status": TaskStatus.RUNNING.value
            }
            execution_steps.append(agent_call_step)
            self._emit_step(agent_call_step)

            result = self._execute_with_retry(agent_name, user_input, context)

            # 更新Agent调用步骤状态
            execution_steps[-1]["status"] = result.status.value
            execution_steps[-1]["duration"] = result.duration
            execution_steps[-1]["quality_score"] = result.quality_score
            execution_steps[-1]["detail"] = f"执行完成，耗时{result.duration:.1f}秒"
            self._emit_step(execution_steps[-1])

            # 步骤3：质量检查
            step_id += 1
            quality = self.quality_assessor.assess(result.output, agent_name, user_input)
            quality_step = {
                "step_id": step_id,
                "type": "quality_check",
                "title": "质量检查",
                "detail": f"{quality['msg']} (质量分数: {quality['score']})",
                "score": quality["score"],
                "status": TaskStatus.COMPLETED.value if quality["ok"] else TaskStatus.FAILED.value
            }
            execution_steps.append(quality_step)
            self._emit_step(quality_step)

            # 构建返回结果
            final_result = {
                "success": result.success,
                "output": result.output if result.success else result.error,
                "agent_used": agent_name,
                "intermediate_steps": result.tools_used or [],
                "steps": execution_steps,
                "total_duration": time.time() - start_time,
                "score": result.quality_score  # 前端期望score字段
            }

            # 自动提取用户信息
            if result.success and result.output:
                extract_result = self._extract_user_info(user_input, user_id)
                if extract_result:
                    final_result["output"] = final_result["output"] + "\n\n---\n" + extract_result

            return final_result

        # 复合Agent处理
        # 步骤2：任务拆分
        step_id += 1
        subtasks = self._split_composite_task(user_input, intents, context)

        task_split_step = {
            "step_id": step_id,
            "type": "task_split",
            "title": "任务拆分",
            "detail": f"将任务拆分为{len(subtasks)}个子任务",
            "subtasks": [{"task_id": t.task_id, "agent": t.agent, "task": t.task, "depends_on": t.depends_on} for t in subtasks],
            "status": TaskStatus.COMPLETED.value
        }
        execution_steps.append(task_split_step)
        self._emit_step(task_split_step)

        # 步骤3：执行子任务
        step_id += 1
        execution_start_step = {
            "step_id": step_id,
            "type": "execution_start",
            "title": "开始执行",
            "detail": f"执行{len(subtasks)}个子任务",
            "status": TaskStatus.RUNNING.value
        }
        execution_steps.append(execution_start_step)
        self._emit_step(execution_start_step)

        results = self._execute_subtasks(subtasks, context)

        # 记录每个子任务的执行结果
        for result in results:
            step_id += 1
            subtask_step = {
                "step_id": step_id,
                "type": "agent_call",
                "title": f"子任务：{agent_names.get(result.agent, result.agent)}",
                "detail": result.output[:200] if result.success else result.error,
                "agent": result.agent,
                "status": result.status.value,
                "duration": result.duration,
                "quality_score": result.quality_score
            }
            execution_steps.append(subtask_step)
            self._emit_step(subtask_step)
            
            # 添加工具调用信息到execution_steps
            if result.tools_used:
                for tool_info in result.tools_used:
                    if isinstance(tool_info, dict) and tool_info.get("action"):
                        tool_step = {
                            "step_id": step_id,
                            "type": "tool",
                            "title": f"调用工具: {tool_info.get('action', '')}",
                            "detail": tool_info.get("output", "")[:100] + "..." if tool_info.get("output") else "执行完成",
                            "status": "completed"
                        }
                        execution_steps.append(tool_step)
                        self._emit_step(tool_step)

        # 更新执行开始步骤状态
        execution_steps[-len(results) - 1]["status"] = TaskStatus.COMPLETED.value
        self._emit_step(execution_steps[-len(results) - 1])

        # 步骤4：结果合并
        step_id += 1
        result_merge_step = {
            "step_id": step_id,
            "type": "result_merge",
            "title": "结果合并",
            "detail": f"合并{len(results)}个Agent的输出",
            "status": TaskStatus.RUNNING.value
        }
        execution_steps.append(result_merge_step)
        self._emit_step(result_merge_step)

        # 使用LLM智能合并结果
        final_output = self.result_merger.merge_with_llm(results, user_input, context, on_token_callback=self.on_token_callback)

        execution_steps[-1]["status"] = TaskStatus.COMPLETED.value
        self._emit_step(execution_steps[-1])

        # 自动提取用户信息
        extract_result = self._extract_user_info(user_input, user_id)
        if extract_result:
            final_output = final_output + "\n\n---\n" + extract_result

        return {
            "success": True,
            "output": final_output,
            "agent_used": ",".join(intents),
            "intermediate_steps": [],
            "steps": execution_steps,
            "is_composite": True,
            "total_duration": time.time() - start_time,
            "subtask_results": [{"agent": r.agent, "success": r.success, "score": r.quality_score} for r in results]
        }

    def get_agent_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            name: {
                "name": agent.agent_name,
                "tools": [t.name for t in agent.tools]
            }
            for name, agent in self.agents.items()
        }
