"""单元测试: adapters/content_filter.py — 敏感内容过滤"""

from app.adapters.content_filter import filter_content, SAFE_REPLY


class TestFilterContent:
    """敏感内容过滤"""

    def test_normal_text_passes(self):
        text, filtered = filter_content("这是一段正常的业务文本")
        assert text == "这是一段正常的业务文本"
        assert filtered is False

    def test_empty_text(self):
        text, filtered = filter_content("")
        assert text == ""
        assert filtered is False

    def test_none_like_empty(self):
        """空字符串不触发过滤"""
        text, filtered = filter_content("")
        assert filtered is False

    def test_competitor_keyword_a(self):
        text, filtered = filter_content("推荐使用竞品A的方案")
        assert filtered is True
        assert text == SAFE_REPLY

    def test_competitor_keyword_b(self):
        text, filtered = filter_content("竞品B的价格更低")
        assert filtered is True
        assert text == SAFE_REPLY

    def test_fake_policy_guarantee(self):
        text, filtered = filter_content("我们保证年化收益20%")
        assert filtered is True
        assert text == SAFE_REPLY

    def test_fake_policy_promise(self):
        text, filtered = filter_content("承诺高额回报")
        assert filtered is True
        assert text == SAFE_REPLY

    def test_fake_policy_zero_risk(self):
        text, filtered = filter_content("该产品零风险投资")
        assert filtered is True
        assert text == SAFE_REPLY

    def test_safe_reply_is_warning(self):
        """安全回复包含警告标识"""
        assert "⚠️" in SAFE_REPLY

    def test_partial_match_not_filtered(self):
        """不包含完整关键词的文本不被过滤"""
        text, filtered = filter_content("这个品牌A不错")
        assert filtered is False
