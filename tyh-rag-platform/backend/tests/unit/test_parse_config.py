"""
文档解析配置完善 - 单元测试
覆盖: FR-01~FR-08, NFR-01
"""

import pytest
import sys
import os

# 确保可以 import app 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ==================== 兼容转换测试 ====================

class TestNormalizeLayoutRecognize:
    """NFR-01: layout_recognize 布尔值→字符串枚举转换"""

    def test_true_to_deepdoc(self):
        from app.api.v1.endpoints.settings import _normalize_layout_recognize
        assert _normalize_layout_recognize(True) == "DeepDOC"

    def test_false_to_plain_text(self):
        from app.api.v1.endpoints.settings import _normalize_layout_recognize
        assert _normalize_layout_recognize(False) == "Plain Text"

    def test_string_deepdoc_unchanged(self):
        from app.api.v1.endpoints.settings import _normalize_layout_recognize
        assert _normalize_layout_recognize("DeepDOC") == "DeepDOC"

    def test_string_plain_text_unchanged(self):
        from app.api.v1.endpoints.settings import _normalize_layout_recognize
        assert _normalize_layout_recognize("Plain Text") == "Plain Text"

    def test_invalid_string_fallback(self):
        from app.api.v1.endpoints.settings import _normalize_layout_recognize
        assert _normalize_layout_recognize("InvalidEngine") == "DeepDOC"

    def test_none_fallback(self):
        from app.api.v1.endpoints.settings import _normalize_layout_recognize
        assert _normalize_layout_recognize(None) == "DeepDOC"

    def test_int_fallback(self):
        from app.api.v1.endpoints.settings import _normalize_layout_recognize
        assert _normalize_layout_recognize(1) == "DeepDOC"


class TestNormalizeParserConfig:
    """NFR-01: parser_config 规范化（过滤无效参数、布尔转换）"""

    def test_layout_recognize_bool_converted_in_manual(self):
        from app.api.v1.endpoints.settings import _normalize_parser_config
        result = _normalize_parser_config("manual", {
            "layout_recognize": True,
        })
        assert result["layout_recognize"] == "DeepDOC"

    def test_qa_removes_invalid_chunk_token_num(self):
        """FR-05: qa 模式无参数，多余字段应被过滤"""
        from app.api.v1.endpoints.settings import _normalize_parser_config
        result = _normalize_parser_config("qa", {
            "chunk_token_num": 512,
            "extra_field": "should_be_removed",
        })
        # qa 模式 params=[]，所有字段都应被过滤
        assert result == {}

    def test_table_removes_invalid_chunk_token_num(self):
        """FR-05: table 模式无参数，多余字段应被过滤"""
        from app.api.v1.endpoints.settings import _normalize_parser_config
        result = _normalize_parser_config("table", {"chunk_token_num": 512})
        assert result == {}

    def test_naive_keeps_valid_params(self):
        from app.api.v1.endpoints.settings import _normalize_parser_config
        result = _normalize_parser_config("naive", {
            "chunk_token_num": 256,
            "delimiter": "\n。",
            "html4excel": True,
            "enable_children": True,
        })
        assert result["chunk_token_num"] == 256
        assert result["delimiter"] == "\n。"
        assert result["html4excel"] is True
        assert result["enable_children"] is True

    def test_naive_filters_old_layout_recognize(self):
        """naive 模式不再有 layout_recognize，旧数据应被过滤"""
        from app.api.v1.endpoints.settings import _normalize_parser_config
        result = _normalize_parser_config("naive", {
            "chunk_token_num": 512,
            "layout_recognize": True,
        })
        assert "layout_recognize" not in result
        assert result["chunk_token_num"] == 512

    def test_picture_filters_invalid_params(self):
        """picture 模式仅保留 auto_keywords/auto_questions"""
        from app.api.v1.endpoints.settings import _normalize_parser_config
        result = _normalize_parser_config("picture", {
            "image_context_size": 128,
            "layout_recognize": True,
        })
        assert result == {}


class TestGetDefaultsForMethod:
    """测试各模式默认值提取"""

    def test_naive_has_all_defaults(self):
        from app.api.v1.endpoints.settings import _get_defaults_for_method
        defaults = _get_defaults_for_method("naive")
        assert defaults["chunk_token_num"] == 512
        assert defaults["delimiter"] == "\n"
        assert defaults["html4excel"] is False
        assert defaults["enable_children"] is False
        assert defaults["image_table_context_window"] == 0
        assert defaults["auto_keywords"] == 0
        assert "layout_recognize" not in defaults
        assert "raptor" not in defaults

    def test_qa_empty_defaults(self):
        from app.api.v1.endpoints.settings import _get_defaults_for_method
        defaults = _get_defaults_for_method("qa")
        assert defaults == {}

    def test_table_empty_defaults(self):
        from app.api.v1.endpoints.settings import _get_defaults_for_method
        defaults = _get_defaults_for_method("table")
        assert defaults == {}

    def test_manual_has_layout_recognize(self):
        """manual 模式有 layout_recognize"""
        from app.api.v1.endpoints.settings import _get_defaults_for_method
        defaults = _get_defaults_for_method("manual")
        assert defaults["layout_recognize"] == "DeepDOC"
        assert defaults["auto_keywords"] == 0

    def test_one_has_layout_recognize(self):
        from app.api.v1.endpoints.settings import _get_defaults_for_method
        defaults = _get_defaults_for_method("one")
        assert defaults["layout_recognize"] == "DeepDOC"

    def test_picture_has_auto_keywords(self):
        from app.api.v1.endpoints.settings import _get_defaults_for_method
        defaults = _get_defaults_for_method("picture")
        assert defaults["auto_keywords"] == 0
        assert "layout_recognize" not in defaults
        assert "image_context_size" not in defaults


# ==================== PARSER_CONFIG_SCHEMA 完整性测试 ====================

class TestParserConfigSchema:
    """FR-04: 各模式参数完整性校验"""

    def test_all_12_modes_defined(self):
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA
        expected = {"naive", "manual", "presentation", "laws", "paper",
                    "book", "one", "picture", "qa", "table", "tag", "resume"}
        assert set(PARSER_CONFIG_SCHEMA.keys()) == expected

    def test_naive_has_basic_and_advanced(self):
        """naive 基础参数 4 个 + 高级参数 5 个（对齐 RAGFlow General 模式）"""
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA
        params = PARSER_CONFIG_SCHEMA["naive"]["params"]
        basic = [p for p in params if p.get("level") == "basic"]
        advanced = [p for p in params if p.get("level") == "advanced"]
        assert len(basic) == 4  # chunk_token_num, delimiter, enable_children, children_delimiter
        assert len(advanced) == 5  # toc_extraction, image_table_context_window, auto_keywords, auto_questions, html4excel

    def test_layout_recognize_is_select_type(self):
        """非 naive 模式的 layout_recognize 必须是 select 类型"""
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA
        modes_with_lr = ["manual", "presentation", "laws", "paper", "book", "one"]
        for mode in modes_with_lr:
            params = PARSER_CONFIG_SCHEMA[mode]["params"]
            lr_param = next((p for p in params if p["key"] == "layout_recognize"), None)
            assert lr_param is not None, f"{mode} 缺少 layout_recognize"
            assert lr_param["type"] == "select", f"{mode} layout_recognize 类型错误"
            assert lr_param["default"] == "DeepDOC"

    def test_naive_no_layout_recognize(self):
        """naive 模式不应有 layout_recognize（对齐 RAGFlow Image 1）"""
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA
        keys = [p["key"] for p in PARSER_CONFIG_SCHEMA["naive"]["params"]]
        assert "layout_recognize" not in keys

    def test_naive_chunk_token_num_max_2048(self):
        """naive chunk_token_num 范围 0-2048（对齐 RAGFlow MaxTokenNumberFormField）"""
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA
        p = next(p for p in PARSER_CONFIG_SCHEMA["naive"]["params"] if p["key"] == "chunk_token_num")
        assert p["max"] == 2048

    def test_naive_image_table_context_window_max_256(self):
        """image_table_context_window 范围 0-256（对齐 RAGFlow ImageContextWindow）"""
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA
        p = next(p for p in PARSER_CONFIG_SCHEMA["naive"]["params"] if p["key"] == "image_table_context_window")
        assert p["max"] == 256
        assert p["default"] == 0

    def test_qa_table_tag_resume_no_params(self):
        """FR-05: qa/table/tag/resume 无可配置参数"""
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA
        for mode in ["qa", "table", "tag", "resume"]:
            assert PARSER_CONFIG_SCHEMA[mode]["params"] == [], f"{mode} 不应有参数"

    def test_picture_no_layout_recognize(self):
        """picture 模式不应有 layout_recognize"""
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA
        keys = [p["key"] for p in PARSER_CONFIG_SCHEMA["picture"]["params"]]
        assert "layout_recognize" not in keys
        assert "auto_keywords" in keys

    def test_auto_keywords_max_30(self):
        """所有含 auto_keywords 的模式 max 应为 30（对齐 RAGFlow）"""
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA
        for mode, schema in PARSER_CONFIG_SCHEMA.items():
            for p in schema["params"]:
                if p["key"] == "auto_keywords":
                    assert p["max"] == 30, f"{mode} auto_keywords max 错误"

    def test_naive_delimiter_default(self):
        """naive delimiter 默认值为 \\n（对齐 RAGFlow）"""
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA
        params = PARSER_CONFIG_SCHEMA["naive"]["params"]
        delim = next(p for p in params if p["key"] == "delimiter")
        assert delim["default"] == "\n"


# ==================== Pydantic 模型测试 ====================

class TestParseConfigUpdate:
    """FR-07: Pydantic 请求体校验"""

    def test_valid_request(self):
        from app.api.v1.endpoints.settings import ParseConfigUpdate
        req = ParseConfigUpdate(
            method_map={".pdf": "manual", ".docx": "naive"},
            parser_configs={"naive": {"chunk_token_num": 256}},
        )
        assert req.get_method_map() == {".pdf": "manual", ".docx": "naive"}

    def test_config_field_compatibility(self):
        """兼容前端发送 config 字段"""
        from app.api.v1.endpoints.settings import ParseConfigUpdate
        req = ParseConfigUpdate(config={".pdf": "naive"})
        assert req.get_method_map() == {".pdf": "naive"}

    def test_invalid_extension_raises(self):
        from app.api.v1.endpoints.settings import ParseConfigUpdate
        with pytest.raises(Exception):
            ParseConfigUpdate.validate_method_map_values({"pdf": "naive"})

    def test_invalid_method_raises(self):
        from app.api.v1.endpoints.settings import ParseConfigUpdate
        with pytest.raises(Exception):
            ParseConfigUpdate.validate_method_map_values({".pdf": "invalid_mode"})

    def test_valid_method_map_passes(self):
        from app.api.v1.endpoints.settings import ParseConfigUpdate
        # 不应抛出异常
        ParseConfigUpdate.validate_method_map_values({
            ".pdf": "manual",
            ".xlsx": "qa",
            ".docx": "naive",
        })


# ==================== SandboxService 测试 ====================

class TestSandboxService:
    """FR-01/FR-02: SandboxService 缓存和取值"""

    def test_get_parser_config_empty_cache(self):
        from app.services.sandbox_service import SandboxService
        # 清空缓存
        original = dict(SandboxService.PARSER_CONFIGS)
        SandboxService.PARSER_CONFIGS.clear()
        try:
            result = SandboxService.get_parser_config("naive")
            assert result == {}
        finally:
            SandboxService.PARSER_CONFIGS.update(original)

    def test_get_parser_config_with_cache(self):
        from app.services.sandbox_service import SandboxService
        original = dict(SandboxService.PARSER_CONFIGS)
        SandboxService.PARSER_CONFIGS["naive"] = {"chunk_token_num": 256}
        try:
            result = SandboxService.get_parser_config("naive")
            assert result == {"chunk_token_num": 256}
            # 应返回副本，不影响原缓存
            result["extra"] = True
            assert "extra" not in SandboxService.PARSER_CONFIGS["naive"]
        finally:
            SandboxService.PARSER_CONFIGS.clear()
            SandboxService.PARSER_CONFIGS.update(original)

    def test_get_parser_config_expands_context_window(self):
        """image_table_context_window 应展开为 image_context_size + table_context_size"""
        from app.services.sandbox_service import SandboxService
        original = dict(SandboxService.PARSER_CONFIGS)
        SandboxService.PARSER_CONFIGS["naive"] = {
            "chunk_token_num": 512,
            "image_table_context_window": 100,
        }
        try:
            result = SandboxService.get_parser_config("naive")
            assert "image_table_context_window" not in result
            assert result["image_context_size"] == 100
            assert result["table_context_size"] == 100
            assert result["chunk_token_num"] == 512
        finally:
            SandboxService.PARSER_CONFIGS.clear()
            SandboxService.PARSER_CONFIGS.update(original)

    def test_get_chunk_method_known_ext(self):
        from app.services.sandbox_service import SandboxService
        assert SandboxService.get_chunk_method("report.pdf") == "manual"
        assert SandboxService.get_chunk_method("data.xlsx") == "qa"
        assert SandboxService.get_chunk_method("doc.docx") == "naive"
        assert SandboxService.get_chunk_method("slides.pptx") == "presentation"

    def test_get_chunk_method_unknown_ext(self):
        from app.services.sandbox_service import SandboxService
        assert SandboxService.get_chunk_method("file.xyz") == "naive"


# ==================== VALID_CHUNK_METHODS 测试 ====================

class TestValidChunkMethods:
    """FR-07: 有效解析模式集合"""

    def test_all_schema_methods_in_valid_set(self):
        from app.api.v1.endpoints.settings import PARSER_CONFIG_SCHEMA, VALID_CHUNK_METHODS
        for method in PARSER_CONFIG_SCHEMA:
            assert method in VALID_CHUNK_METHODS, f"{method} 不在 VALID_CHUNK_METHODS 中"
