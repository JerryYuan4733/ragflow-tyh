"""单元测试: services/document_sync_service.py — 文档同步服务"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.document_sync_service import DocumentSyncService, SYNC_PAGE_SIZE
from app.services.document_status import (
    STATUS_PENDING,
    STATUS_PARSING,
    STATUS_READY,
    STATUS_ERROR,
)
from app.adapters.ragflow_types import DocumentInfo


# ==================== 辅助工厂函数 ====================

def make_rf_doc(
    doc_id: str = "rf-001",
    name: str = "test.pdf",
    run: str = "3",
    progress: float = 1.0,
    size: int = 1024,
    doc_type: str = "application/pdf",
) -> DocumentInfo:
    """构造 RAGFlow 文档信息"""
    return DocumentInfo(
        id=doc_id,
        name=name,
        run=run,
        progress=progress,
        size=size,
        type=doc_type,
    )


def make_local_doc(
    doc_id: str = "local-001",
    ragflow_document_id: str = "rf-001",
    ragflow_dataset_id: str = "ds-001",
    team_id: str = "team-001",
    filename: str = "test.pdf",
    status: str = STATUS_READY,
) -> MagicMock:
    """构造本地 DocumentMeta Mock"""
    doc = MagicMock()
    doc.id = doc_id
    doc.ragflow_document_id = ragflow_document_id
    doc.ragflow_dataset_id = ragflow_dataset_id
    doc.team_id = team_id
    doc.filename = filename
    doc.status = status
    doc.run = "3"
    doc.progress = 1.0
    doc.last_synced_at = None
    return doc


def make_team_dataset(
    dataset_id: str = "ds-001",
    dataset_name: str = "测试知识库",
    team_id: str = "team-001",
) -> MagicMock:
    """构造 TeamDataset Mock"""
    ds = MagicMock()
    ds.ragflow_dataset_id = dataset_id
    ds.ragflow_dataset_name = dataset_name
    ds.team_id = team_id
    return ds


# ==================== Mock 数据库辅助 ====================

def mock_db_session(scalars_result: list) -> AsyncMock:
    """构造 AsyncSession Mock，execute 返回给定结果"""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = scalars_result
    db.execute.return_value = result_mock
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


# ==================== 测试类 ====================

class TestSyncDataset:
    """sync_dataset() 单个知识库同步"""

    @pytest.fixture
    def ragflow_client(self):
        """Mock RAGFlow 客户端"""
        client = AsyncMock()
        return client

    @pytest.fixture
    def service(self, ragflow_client):
        return DocumentSyncService(ragflow_client)

    @pytest.mark.asyncio
    async def test_new_docs_inserted(self, service, ragflow_client):
        """RAGFlow 有、本地无 → 应插入新记录"""
        # Arrange
        ragflow_client.list_documents.return_value = [
            make_rf_doc(doc_id="rf-new-1", name="new.pdf", run="3"),
        ]
        db = mock_db_session([])  # 本地无文档

        # Act
        result = await service.sync_dataset(db, "team-001", "ds-001", "测试知识库", user_id="user-001")

        # Assert
        assert result["new"] == 1
        assert result["updated"] == 0
        assert result["orphans"] == 0
        assert result["ragflow_count"] == 1
        assert db.add.called

    @pytest.mark.asyncio
    async def test_existing_docs_updated(self, service, ragflow_client):
        """两边都有 → 应更新状态"""
        # Arrange
        ragflow_client.list_documents.return_value = [
            make_rf_doc(doc_id="rf-001", run="1", progress=0.5),  # 解析中
        ]
        local_doc = make_local_doc(
            ragflow_document_id="rf-001", status=STATUS_PENDING
        )
        db = mock_db_session([local_doc])

        # Act
        result = await service.sync_dataset(db, "team-001", "ds-001", user_id="user-001")

        # Assert
        assert result["new"] == 0
        assert result["updated"] == 1
        assert result["orphans"] == 0
        assert local_doc.status == STATUS_PARSING
        assert local_doc.progress == 0.5

    @pytest.mark.asyncio
    async def test_orphan_docs_marked_error(self, service, ragflow_client):
        """本地有、RAGFlow 无 → 应标记为 error"""
        # Arrange
        ragflow_client.list_documents.return_value = []  # RAGFlow 无文档
        local_doc = make_local_doc(
            ragflow_document_id="rf-gone", status=STATUS_READY
        )
        db = mock_db_session([local_doc])

        # Act
        result = await service.sync_dataset(db, "team-001", "ds-001", user_id="user-001")

        # Assert
        assert result["orphans"] == 1
        assert local_doc.status == STATUS_ERROR

    @pytest.mark.asyncio
    async def test_filename_synced_on_change(self, service, ragflow_client):
        """RAGFlow 文件名变化时应同步更新"""
        # Arrange
        ragflow_client.list_documents.return_value = [
            make_rf_doc(doc_id="rf-001", name="renamed.pdf"),
        ]
        local_doc = make_local_doc(
            ragflow_document_id="rf-001", filename="old_name.pdf"
        )
        db = mock_db_session([local_doc])

        # Act
        await service.sync_dataset(db, "team-001", "ds-001", user_id="user-001")

        # Assert
        assert local_doc.filename == "renamed.pdf"

    @pytest.mark.asyncio
    async def test_filename_not_changed_if_same(self, service, ragflow_client):
        """文件名相同时不应修改"""
        # Arrange
        ragflow_client.list_documents.return_value = [
            make_rf_doc(doc_id="rf-001", name="same.pdf"),
        ]
        local_doc = make_local_doc(
            ragflow_document_id="rf-001", filename="same.pdf"
        )
        db = mock_db_session([local_doc])

        # Act
        await service.sync_dataset(db, "team-001", "ds-001", user_id="user-001")

        # Assert
        assert local_doc.filename == "same.pdf"

    @pytest.mark.asyncio
    async def test_ragflow_api_error_raises(self, service, ragflow_client):
        """RAGFlow API 异常应向上抛出"""
        # Arrange
        ragflow_client.list_documents.side_effect = Exception("API timeout")
        db = mock_db_session([])

        # Act & Assert
        with pytest.raises(Exception, match="API timeout"):
            await service.sync_dataset(db, "team-001", "ds-001", user_id="user-001")

    @pytest.mark.asyncio
    async def test_mixed_scenario(self, service, ragflow_client):
        """混合场景：新增 + 更新 + 异常同时存在"""
        # Arrange
        ragflow_client.list_documents.return_value = [
            make_rf_doc(doc_id="rf-existing", name="a.pdf", run="3"),
            make_rf_doc(doc_id="rf-new", name="b.pdf", run="0"),
        ]
        local_existing = make_local_doc(
            ragflow_document_id="rf-existing", status=STATUS_PENDING
        )
        local_orphan = make_local_doc(
            doc_id="local-orphan",
            ragflow_document_id="rf-deleted",
            status=STATUS_READY,
        )
        db = mock_db_session([local_existing, local_orphan])

        # Act
        result = await service.sync_dataset(db, "team-001", "ds-001", user_id="user-001")

        # Assert
        assert result["new"] == 1
        assert result["updated"] == 1
        assert result["orphans"] == 1
        assert result["ragflow_count"] == 2

    @pytest.mark.asyncio
    async def test_local_doc_without_ragflow_id_ignored(self, service, ragflow_client):
        """本地记录无 ragflow_document_id 时不应被标记为异常"""
        # Arrange
        ragflow_client.list_documents.return_value = []
        local_doc = make_local_doc(ragflow_document_id=None)  # 无 ragflow_id
        db = mock_db_session([local_doc])

        # Act
        result = await service.sync_dataset(db, "team-001", "ds-001", user_id="user-001")

        # Assert
        assert result["orphans"] == 0

    @pytest.mark.asyncio
    async def test_list_documents_called_with_correct_params(self, service, ragflow_client):
        """应使用正确的参数调用 list_documents"""
        # Arrange
        ragflow_client.list_documents.return_value = []
        db = mock_db_session([])

        # Act
        await service.sync_dataset(db, "team-001", "ds-abc", user_id="user-001")

        # Assert
        ragflow_client.list_documents.assert_awaited_once_with(
            "ds-abc", page=1, size=SYNC_PAGE_SIZE
        )


class TestSyncAllDatasets:
    """sync_all_datasets() 全量同步"""

    @pytest.fixture
    def ragflow_client(self):
        client = AsyncMock()
        return client

    @pytest.fixture
    def service(self, ragflow_client):
        return DocumentSyncService(ragflow_client)

    @pytest.mark.asyncio
    async def test_no_datasets_returns_empty(self, service):
        """团队无知识库时应返回空结果"""
        db = mock_db_session([])  # 无 team_datasets

        result = await service.sync_all_datasets(db, "team-001", user_id="user-001")

        assert result["datasets_synced"] == 0
        assert result["new_docs"] == 0
        assert result["message"] == "当前团队未绑定知识库"

    @pytest.mark.asyncio
    async def test_single_dataset_synced(self, service, ragflow_client):
        """单个知识库应被正确同步"""
        # Arrange: mock db.execute 返回 team_datasets 然后返回 local_docs
        ds = make_team_dataset(dataset_id="ds-001", dataset_name="KB1")

        # 第1次 execute → 返回 team_datasets
        # 第2次 execute（sync_dataset 内部）→ 返回 local_docs
        db = AsyncMock()
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result_mock = MagicMock()
            if call_count[0] == 1:
                # 返回 team_datasets
                result_mock.scalars.return_value.all.return_value = [ds]
            else:
                # sync_dataset 内部查询 local_docs
                result_mock.scalars.return_value.all.return_value = []
            return result_mock

        db.execute = mock_execute
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        ragflow_client.list_documents.return_value = [
            make_rf_doc(doc_id="rf-001", name="doc.pdf"),
        ]

        # Act
        result = await service.sync_all_datasets(db, "team-001", user_id="user-001")

        # Assert
        assert result["datasets_synced"] == 1
        assert result["new_docs"] == 1
        assert result["total_ragflow_docs"] == 1

    @pytest.mark.asyncio
    async def test_dataset_error_counted_separately(self, service, ragflow_client):
        """单个 dataset 同步失败不应影响其他 dataset 的汇总"""
        ds1 = make_team_dataset(dataset_id="ds-ok", dataset_name="OK")
        ds2 = make_team_dataset(dataset_id="ds-fail", dataset_name="FAIL")

        db = AsyncMock()
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result_mock = MagicMock()
            if call_count[0] == 1:
                result_mock.scalars.return_value.all.return_value = [ds1, ds2]
            else:
                result_mock.scalars.return_value.all.return_value = []
            return result_mock

        db.execute = mock_execute
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        # ds-ok 正常返回，ds-fail 抛异常
        async def mock_list(dataset_id, **kwargs):
            if dataset_id == "ds-fail":
                raise Exception("connection timeout")
            return [make_rf_doc(doc_id="rf-1")]

        ragflow_client.list_documents = mock_list

        # Act
        result = await service.sync_all_datasets(db, "team-001", user_id="user-001")

        # Assert
        assert result["datasets_synced"] == 1  # 只有 ds-ok 成功
        assert result["new_docs"] == 1
        # details 中应有 error 项
        errors = [d for d in result["details"] if "error" in d]
        assert len(errors) == 1
        assert "connection timeout" in errors[0]["error"]
