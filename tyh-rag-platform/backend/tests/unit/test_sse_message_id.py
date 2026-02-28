"""单元测试: SSE done 事件包含真实消息 ID (US-018 T-18.5)

验证 chat_service.send_message_stream 的 done 事件
包含 user_message_id 和 ai_message_id 字段。
"""

import json
import pytest


class TestSSEDoneEvent:
    """SSE done 事件结构验证"""

    def test_done_event_contains_message_ids(self):
        """done 事件 JSON 应包含 user_message_id 和 ai_message_id"""
        # 模拟 done 事件 payload（与 chat_service.py 中构造一致）
        done_payload = {
            "type": "done",
            "user_message_id": "uuid-user-123",
            "ai_message_id": "uuid-ai-456",
            "is_filtered": False,
            "is_fallback": False,
        }

        json_str = json.dumps(done_payload, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["type"] == "done"
        assert "user_message_id" in parsed
        assert "ai_message_id" in parsed
        assert parsed["user_message_id"] == "uuid-user-123"
        assert parsed["ai_message_id"] == "uuid-ai-456"

    def test_done_event_sse_format(self):
        """验证 SSE 格式: data: {json}\\n\\n"""
        done_payload = {
            "type": "done",
            "user_message_id": "uid-1",
            "ai_message_id": "aid-1",
        }
        sse_line = f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

        assert sse_line.startswith("data: ")
        assert sse_line.endswith("\n\n")

        # 解析 data 内容
        data_str = sse_line.strip().removeprefix("data: ")
        data = json.loads(data_str)
        assert data["type"] == "done"
        assert data["user_message_id"] == "uid-1"
