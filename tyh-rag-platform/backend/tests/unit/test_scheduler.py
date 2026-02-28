"""单元测试: utils/scheduler.py — 质量评分算法"""

import pytest
from app.utils.scheduler import calculate_quality_score


class TestCalculateQualityScore:
    """文档质量评分算法"""

    def test_zero_chunks_returns_zero(self):
        assert calculate_quality_score(0, 1024) == 0.0

    def test_normal_score(self):
        """10个chunk, 1MB文件, 100%解析"""
        score = calculate_quality_score(10, 1024 * 1024)
        assert 0 < score <= 100

    def test_high_density_capped(self):
        """超高密度不超过60分基础分"""
        score = calculate_quality_score(1000, 1024)  # 极高密度
        assert score <= 100

    def test_full_progress_adds_40(self):
        """parse_progress=1.0 贡献40分"""
        full = calculate_quality_score(10, 1024 * 1024, parse_progress=1.0)
        half = calculate_quality_score(10, 1024 * 1024, parse_progress=0.5)
        assert full > half
        assert full - half == pytest.approx(20.0, abs=1.0)

    def test_zero_progress(self):
        """parse_progress=0 只有密度分"""
        score = calculate_quality_score(10, 1024 * 1024, parse_progress=0.0)
        assert score >= 0
        assert score <= 60  # 只有密度分

    def test_score_range(self):
        """分数在0-100范围"""
        for chunks in [1, 10, 50, 100, 500]:
            for size in [1024, 1024 * 1024, 10 * 1024 * 1024]:
                s = calculate_quality_score(chunks, size)
                assert 0 <= s <= 100, f"chunks={chunks}, size={size}, score={s}"

    def test_tiny_file(self):
        """极小文件(接近0)不崩溃"""
        score = calculate_quality_score(1, 1, parse_progress=1.0)
        assert score > 0

    def test_returns_float(self):
        score = calculate_quality_score(5, 1024 * 512)
        assert isinstance(score, float)
