"""意图识别器单元测试"""

import pytest
from app.agents.orchestrator import IntentClassifier


class TestIntentClassifier:
    """意图识别器测试"""

    def setup_method(self):
        """测试前准备"""
        self.classifier = IntentClassifier()

    def test_career_keywords(self):
        """测试职业相关关键词识别"""
        result = self.classifier.classify_keywords("我想找工作")
        assert "career" in result
        assert result["career"]["score"] > 0

    def test_resume_keywords(self):
        """测试简历相关关键词识别"""
        result = self.classifier.classify_keywords("帮我写简历")
        assert "resume" in result
        assert result["resume"]["score"] > 0

    def test_interview_keywords(self):
        """测试面试相关关键词识别"""
        result = self.classifier.classify_keywords("准备面试")
        assert "interview" in result
        assert result["interview"]["score"] > 0

    def test_skill_keywords(self):
        """测试技能相关关键词识别"""
        result = self.classifier.classify_keywords("学习路径是什么")
        assert "skill" in result
        assert result["skill"]["score"] > 0

    def test_side_job_keywords(self):
        """测试副业相关关键词识别"""
        result = self.classifier.classify_keywords("有什么副业推荐")
        assert "side_job" in result
        assert result["side_job"]["score"] > 0

    def test_no_keywords(self):
        """测试无关键词匹配"""
        result = self.classifier.classify_keywords("今天天气怎么样")
        assert len(result) == 0

    def test_multiple_keywords(self):
        """测试多意图识别"""
        result = self.classifier.classify_keywords("我想找工作，需要写简历")
        assert "career" in result
        assert "resume" in result


class TestQualityAssessor:
    """质量评估器测试"""

    def setup_method(self):
        """测试前准备"""
        from app.agents.orchestrator import QualityAssessor
        self.assessor = QualityAssessor()

    def test_empty_output(self):
        """测试空输出"""
        result = self.assessor.assess("", "career")
        assert result["ok"] is False
        assert result["score"] == 0

    def test_good_output(self):
        """测试良好输出"""
        output = """
        **核心结论**：基于您的背景，建议您考虑以下发展方向。

        **详细分析**：
        - **优势**：您有扎实的技术基础
        - **机会**：市场需求旺盛

        **行动建议**：
        1. 继续深耕技术
        2. 扩展人脉网络
        """
        result = self.assessor.assess(output, "career")
        assert result["ok"] is True
        assert result["score"] >= 40

    def test_should_retry(self):
        """测试是否应该重试"""
        # 低分应该重试
        assessment = {"ok": False, "score": 30}
        assert self.assessor.should_retry(assessment) is True

        # 合格不应该重试
        assessment = {"ok": True, "score": 60}
        assert self.assessor.should_retry(assessment) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
