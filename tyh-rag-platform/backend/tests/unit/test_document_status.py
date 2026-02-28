"""单元测试: services/document_status.py — 文档状态常量与映射函数"""

import pytest

from app.services.document_status import (
    map_ragflow_status,
    STATUS_PENDING,
    STATUS_PARSING,
    STATUS_READY,
    STATUS_ERROR,
    RAGFLOW_RUN_UNSTART,
    RAGFLOW_RUN_RUNNING,
    RAGFLOW_RUN_DONE,
    RAGFLOW_RUN_FAIL,
    RAGFLOW_RUN_CANCEL,
    PARSABLE_STATUSES,
    BATCH_PARSE_LIMIT,
)


class TestStatusConstants:
    """状态常量值验证"""

    def test_status_values_are_strings(self):
        """所有状态常量应为字符串"""
        for s in [STATUS_PENDING, STATUS_PARSING, STATUS_READY, STATUS_ERROR]:
            assert isinstance(s, str)

    def test_status_values_unique(self):
        """状态常量不应重复"""
        statuses = [STATUS_PENDING, STATUS_PARSING, STATUS_READY, STATUS_ERROR]
        assert len(statuses) == len(set(statuses))

    def test_parsable_statuses_contains_pending_and_error(self):
        """可解析状态集合应包含 pending 和 error"""
        assert STATUS_PENDING in PARSABLE_STATUSES
        assert STATUS_ERROR in PARSABLE_STATUSES

    def test_parsable_statuses_excludes_ready_and_parsing(self):
        """可解析状态集合不应包含 ready 和 parsing"""
        assert STATUS_READY not in PARSABLE_STATUSES
        assert STATUS_PARSING not in PARSABLE_STATUSES

    def test_batch_parse_limit_is_positive(self):
        """批量解析上限应为正整数"""
        assert isinstance(BATCH_PARSE_LIMIT, int)
        assert BATCH_PARSE_LIMIT > 0


class TestMapRagflowStatus:
    """map_ragflow_status() 映射函数"""

    # ---- 数字字符串形式（RAGFlow 实际返回值） ----

    def test_unstart_number(self):
        """run='0' → pending"""
        assert map_ragflow_status(RAGFLOW_RUN_UNSTART) == STATUS_PENDING

    def test_running_number(self):
        """run='1' → parsing"""
        assert map_ragflow_status(RAGFLOW_RUN_RUNNING) == STATUS_PARSING

    def test_fail_number(self):
        """run='2' → error"""
        assert map_ragflow_status(RAGFLOW_RUN_FAIL) == STATUS_ERROR

    def test_done_number(self):
        """run='3' → ready"""
        assert map_ragflow_status(RAGFLOW_RUN_DONE) == STATUS_READY

    def test_cancel_number(self):
        """run='4' → error"""
        assert map_ragflow_status(RAGFLOW_RUN_CANCEL) == STATUS_ERROR

    # ---- 英文字符串形式 ----

    def test_unstart_string(self):
        """run='unstart' → pending"""
        assert map_ragflow_status("unstart") == STATUS_PENDING

    def test_running_string(self):
        """run='running' → parsing"""
        assert map_ragflow_status("running") == STATUS_PARSING

    def test_done_string(self):
        """run='done' → ready"""
        assert map_ragflow_status("done") == STATUS_READY

    def test_fail_string(self):
        """run='fail' → error"""
        assert map_ragflow_status("fail") == STATUS_ERROR

    def test_cancel_string(self):
        """run='cancel' → error"""
        assert map_ragflow_status("cancel") == STATUS_ERROR

    # ---- 边界条件 ----

    def test_unknown_value_defaults_to_pending(self):
        """未知 run 值应回退为 pending"""
        assert map_ragflow_status("unknown_value") == STATUS_PENDING

    def test_empty_string_defaults_to_pending(self):
        """空字符串应回退为 pending"""
        assert map_ragflow_status("") == STATUS_PENDING

    def test_none_as_string_defaults_to_pending(self):
        """None 转 str 后应回退为 pending"""
        assert map_ragflow_status("None") == STATUS_PENDING

    def test_integer_input_converted_to_string(self):
        """整数输入应被 str() 转换后正确映射"""
        # map_ragflow_status 内部 str(run)
        assert map_ragflow_status(0) == STATUS_PENDING
        assert map_ragflow_status(1) == STATUS_PARSING
        assert map_ragflow_status(3) == STATUS_READY

    def test_case_sensitive(self):
        """映射支持数字、小写、大写，但混合大小写仍回退"""
        # 大写格式（RAGFlow API 实际返回）应正确映射
        assert map_ragflow_status("FAIL") == STATUS_ERROR
        assert map_ragflow_status("DONE") == STATUS_READY
        assert map_ragflow_status("RUNNING") == STATUS_PARSING
        assert map_ragflow_status("UNSTART") == STATUS_PENDING
        assert map_ragflow_status("CANCEL") == STATUS_ERROR
        # 混合大小写不在映射中，应回退到 pending
        assert map_ragflow_status("Done") == STATUS_PENDING
        assert map_ragflow_status("Fail") == STATUS_PENDING
