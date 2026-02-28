"""单元测试: services/chat_service.py — 对话服务核心逻辑"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.chat_service import ChatService, DEFAULT_SUGGESTIONS, FALLBACK_MESSAGE


class TestGetSuggestions:
    """推荐问题"""

    @pytest.mark.asyncio
    async def test_returns_default_list(self):
        result = await ChatService.get_suggestions()
        assert isinstance(result, list)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_contains_expected_questions(self):
        result = await ChatService.get_suggestions()
        assert result == DEFAULT_SUGGESTIONS

    @pytest.mark.asyncio
    async def test_returns_strings(self):
        result = await ChatService.get_suggestions()
        for q in result:
            assert isinstance(q, str)
            assert len(q) > 0


class TestCreateSession:
    """创建会话"""

    @pytest.mark.asyncio
    async def test_creates_with_default_title(self):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"
        mock_user.active_team_id = "team-1"

        session = await ChatService.create_session(mock_db, mock_user)
        assert session.title == "新对话"
        assert session.user_id == "user-1"
        assert session.team_id == "team-1"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creates_with_custom_title(self):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"
        mock_user.active_team_id = "team-1"

        session = await ChatService.create_session(mock_db, mock_user, title="我的对话")
        assert session.title == "我的对话"


class TestDeleteSession:
    """删除会话"""

    @pytest.mark.asyncio
    async def test_delete_marks_inactive(self):
        mock_session = MagicMock()
        mock_session.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        mock_user = MagicMock()
        mock_user.id = "user-1"

        result = await ChatService.delete_session(mock_db, "sess-1", mock_user)
        assert result is True
        assert mock_session.is_active is False
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found_raises(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        mock_user = MagicMock()
        mock_user.id = "user-1"

        with pytest.raises(ValueError, match="会话不存在"):
            await ChatService.delete_session(mock_db, "nonexistent", mock_user)


class TestFallbackMessage:
    """降级消息"""

    def test_fallback_is_nonempty(self):
        assert len(FALLBACK_MESSAGE) > 0

    def test_fallback_contains_hint(self):
        assert "管理员" in FALLBACK_MESSAGE or "稍后" in FALLBACK_MESSAGE
