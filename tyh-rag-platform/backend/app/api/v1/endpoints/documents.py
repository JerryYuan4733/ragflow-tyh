import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_kb_admin
from app.db.session import get_db
from app.models import User, DocumentMeta, TeamDataset, SystemConfig
from app.services.sandbox_service import sandbox_service
from app.services.document_status import (
    STATUS_PENDING, STATUS_PARSING, STATUS_ERROR, STATUS_READY,
    PARSABLE_STATUSES, BATCH_PARSE_LIMIT, map_ragflow_status,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# 本地文件存储目录
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _save_file_locally(doc_id: str, filename: str, content: bytes) -> Path:
    """保存文件到本地存储"""
    doc_dir = UPLOAD_DIR / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_path = doc_dir / filename
    file_path.write_bytes(content)
    return file_path


def _get_local_file(doc_id: str, filename: str) -> Optional[Path]:
    """获取本地存储的文件路径"""
    file_path = UPLOAD_DIR / doc_id / filename
    if file_path.exists():
        return file_path
    # 也搜索目录下任何文件（替换后文件名可能变化）
    doc_dir = UPLOAD_DIR / doc_id
    if doc_dir.exists():
        files = list(doc_dir.iterdir())
        if files:
            return files[0]
    return None


def _cleanup_local_file(doc_id: str):
    """清理本地存储的文档文件"""
    doc_dir = UPLOAD_DIR / doc_id
    if doc_dir.exists():
        shutil.rmtree(doc_dir, ignore_errors=True)


async def _get_default_parse_mode(db: AsyncSession) -> str:
    """从 system_config 读取默认解析模式，无配置时返回 'auto'"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "default_parse_mode")
    )
    config = result.scalar_one_or_none()
    if config:
        try:
            return json.loads(config.config_value)
        except (json.JSONDecodeError, TypeError):
            return config.config_value
    return "auto"


# ===== 分类管理 =====

CATEGORIES_FILE = UPLOAD_DIR / "_categories.json"


def _load_categories() -> list[str]:
    """加载已保存的分类路径列表"""
    if CATEGORIES_FILE.exists():
        try:
            return json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_categories(cats: list[str]):
    CATEGORIES_FILE.write_text(json.dumps(cats, ensure_ascii=False), encoding="utf-8")


def _build_tree(paths: list[str]) -> list[dict]:
    """将扁平路径列表构建成树结构"""
    tree: dict = {}
    for p in sorted(set(paths)):
        parts = [x for x in p.strip("/").split("/") if x]
        node = tree
        for part in parts:
            if part not in node:
                node[part] = {}
            node = node[part]

    def to_list(d: dict, prefix: str = "") -> list[dict]:
        result = []
        for name, children in d.items():
            path = f"{prefix}/{name}"
            item: dict = {"name": name, "path": path}
            if children:
                item["children"] = to_list(children, path)
            result.append(item)
        return result

    return to_list(tree)


@router.get("/my-datasets")
async def get_my_datasets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户活跃团队绑定的知识库列表（所有角色可用）"""
    if not user.active_team_id:
        return {"items": [], "total": 0}
    result = await db.execute(
        select(TeamDataset).where(TeamDataset.team_id == user.active_team_id)
        .order_by(TeamDataset.created_at.asc())
    )
    datasets = list(result.scalars().all())
    return {
        "items": [
            {
                "id": ds.id,
                "ragflow_dataset_id": ds.ragflow_dataset_id,
                "ragflow_dataset_name": ds.ragflow_dataset_name or ds.ragflow_dataset_id,
                "document_count": ds.document_count,
                "chunk_count": ds.chunk_count,
            }
            for ds in datasets
        ],
        "total": len(datasets),
    }


@router.get("/categories")
async def get_categories(
    user: User = Depends(get_current_user),
):
    """获取文档分类树"""
    return _build_tree(_load_categories())


@router.post("/categories", status_code=201)
async def create_category(
    request: dict,
    user: User = Depends(require_kb_admin),
):
    """创建文档分类"""
    name = request.get("name", "").strip()
    parent_path = request.get("parent_path") or ""
    if not name:
        raise HTTPException(status_code=400, detail="分类名称不能为空")

    new_path = f"{parent_path}/{name}" if parent_path else f"/{name}"
    cats = _load_categories()
    if new_path not in cats:
        cats.append(new_path)
        _save_categories(cats)

    return {"path": new_path, "name": name}


@router.delete("/categories")
async def delete_category(
    request: dict,
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除文档分类，该分类下的文档回归根目录"""
    path = request.get("path", "").strip()
    if not path or path == "/":
        raise HTTPException(status_code=400, detail="不能删除根目录")

    cats = _load_categories()
    # 删除该分类及其子分类
    new_cats = [c for c in cats if c != path and not c.startswith(path + "/")]
    _save_categories(new_cats)

    # 将该分类下的文档回归根目录
    if user.active_team_id:
        result = await db.execute(
            select(DocumentMeta).where(
                DocumentMeta.team_id == user.active_team_id,
                DocumentMeta.category_path.startswith(path),
            )
        )
        docs = list(result.scalars().all())
        for doc in docs:
            doc.category_path = "/"
        if docs:
            await db.commit()

    return {"message": "分类已删除", "affected_docs": len(docs) if user.active_team_id else 0}


@router.put("/batch-category")
async def batch_update_category(
    request: dict,
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量修改文档分类"""
    doc_ids = request.get("document_ids", [])
    category_path = request.get("category_path", "").strip()
    if not doc_ids:
        raise HTTPException(status_code=400, detail="未选择文档")
    if not category_path:
        raise HTTPException(status_code=400, detail="分类路径不能为空")

    result = await db.execute(
        select(DocumentMeta).where(
            DocumentMeta.id.in_(doc_ids),
            DocumentMeta.team_id == user.active_team_id,
        )
    )
    docs = list(result.scalars().all())
    for doc in docs:
        doc.category_path = category_path
    await db.commit()
    return {"message": "分类已更新", "updated": len(docs)}


# ===== 固定路径路由（必须在 /{doc_id} 参数路由之前注册）=====

@router.post("/sync")
async def sync_documents(
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """全量同步 RAGFlow 文档到本地（当前团队所有知识库）"""
    if not user.active_team_id:
        raise HTTPException(status_code=400, detail="当前用户未关联团队")

    from app.services.document_sync_service import DocumentSyncService
    from app.adapters.ragflow_client import ragflow_client
    sync_service = DocumentSyncService(ragflow_client)
    result = await sync_service.sync_all_datasets(db, user.active_team_id, user_id=user.id)
    return result


@router.post("/batch-parse")
async def batch_parse_documents(
    request: dict,
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量触发文档解析"""
    document_ids = request.get("document_ids", [])
    if not document_ids:
        raise HTTPException(status_code=400, detail="document_ids 不能为空")
    if len(document_ids) > BATCH_PARSE_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"单次最多 {BATCH_PARSE_LIMIT} 个文档"
        )

    results = []
    success_count = 0
    failed_count = 0

    for doc_id in document_ids:
        result = await db.execute(
            select(DocumentMeta).where(DocumentMeta.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            results.append({"doc_id": doc_id, "status": "error", "success": False, "error": "文档不存在"})
            failed_count += 1
            continue

        if doc.status not in PARSABLE_STATUSES:
            results.append({
                "doc_id": doc_id, "status": doc.status, "success": False,
                "error": f"文档当前状态不允许解析（当前状态: {doc.status}）"
            })
            failed_count += 1
            continue

        if not doc.ragflow_document_id or not doc.ragflow_dataset_id:
            results.append({
                "doc_id": doc_id, "status": doc.status, "success": False,
                "error": "文档缺少 RAGFlow 信息，无法解析"
            })
            failed_count += 1
            continue

        try:
            parse_ok = await sandbox_service.auto_parse_document(
                doc.filename, doc.ragflow_document_id, dataset_id=doc.ragflow_dataset_id
            )
            doc.status = STATUS_PARSING if parse_ok else STATUS_ERROR
            results.append({"doc_id": doc_id, "status": doc.status, "success": True})
            success_count += 1
        except Exception as e:
            doc.status = STATUS_ERROR
            results.append({"doc_id": doc_id, "status": doc.status, "success": False, "error": str(e)})
            failed_count += 1

    await db.flush()
    return {
        "message": "批量解析已触发",
        "total": len(document_ids),
        "success": success_count,
        "failed": failed_count,
        "results": results,
    }


@router.delete("/cleanup-orphans")
async def cleanup_orphans(
    dataset_id: Optional[str] = None,
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """一键清理异常文档记录（status='error'）"""
    if not user.active_team_id:
        raise HTTPException(status_code=400, detail="当前用户未关联团队")

    query = select(DocumentMeta).where(
        DocumentMeta.team_id == user.active_team_id,
        DocumentMeta.status == STATUS_ERROR,
    )
    if dataset_id:
        query = query.where(DocumentMeta.ragflow_dataset_id == dataset_id)

    result = await db.execute(query)
    orphans = list(result.scalars().all())

    for doc in orphans:
        _cleanup_local_file(doc.id)
        await db.delete(doc)

    # 显式提交，确保删除在 response 返回前持久化
    await db.commit()
    return {"message": "清理完成", "cleaned": len(orphans)}


@router.post("", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    category_path: str = Form(default="/"),
    dataset_id: str = Form(default=""),
    parse_mode: str = Form(default=""),
    priority: int = Form(default=0),
    expires_at: Optional[str] = Form(default=None),
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传文档 - 同步上传到 RAGFlow，成功后写入本地表"""
    # 校验 dataset_id 归属当前团队
    ragflow_dataset_id = dataset_id
    if ragflow_dataset_id and user.active_team_id:
        ds_check = await db.execute(
            select(TeamDataset).where(
                TeamDataset.team_id == user.active_team_id,
                TeamDataset.ragflow_dataset_id == ragflow_dataset_id,
            )
        )
        if not ds_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="该知识库不属于当前团队")

    # 读取文件内容
    file_content = await file.read()

    # 同步上传到 RAGFlow（阻塞等待结果）
    ragflow_doc_id = None
    if ragflow_dataset_id:
        try:
            ragflow_doc_id = await sandbox_service.upload_to_dataset(
                file.filename or "unknown", file_content,
                file.content_type or "application/octet-stream",
                dataset_id=ragflow_dataset_id,
            )
        except Exception as e:
            logger.error(f"RAGFlow上传失败: {file.filename} - {e}")
        if not ragflow_doc_id:
            raise HTTPException(status_code=500, detail="上传到 RAGFlow 失败")

    # 确定解析模式
    actual_parse_mode = parse_mode or await _get_default_parse_mode(db)

    # RAGFlow 上传成功，写入本地数据库（保证一致性）
    initial_status = STATUS_PENDING
    doc = DocumentMeta(
        id=str(uuid.uuid4()),
        team_id=user.active_team_id,
        uploaded_by=user.id,
        filename=file.filename or "unknown",
        file_type=file.content_type or "application/octet-stream",
        file_size=len(file_content),
        category_path=category_path,
        ragflow_document_id=ragflow_doc_id,
        ragflow_dataset_id=ragflow_dataset_id or None,
        status=initial_status,
        priority=priority,
    )

    # 自动解析模式：设置解析方式 + 触发解析
    if actual_parse_mode == "auto" and ragflow_doc_id and ragflow_dataset_id:
        try:
            parse_ok = await sandbox_service.auto_parse_document(
                doc.filename, ragflow_doc_id, dataset_id=ragflow_dataset_id
            )
            doc.status = STATUS_PARSING if parse_ok else STATUS_ERROR
        except Exception as e:
            logger.warning(f"自动解析触发失败: {e}")
            doc.status = STATUS_ERROR

    db.add(doc)
    await db.flush()

    # 保存到本地（用于预览/下载）
    _save_file_locally(doc.id, doc.filename, file_content)

    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "ragflow_document_id": ragflow_doc_id,
        "ragflow_syncing": False,
    }


@router.get("")
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_path: Optional[str] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    dataset_id: Optional[str] = None,
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档列表（支持按知识库、状态过滤）"""
    cat_filter = category_path or category  # 兼容两种参数名
    query = select(DocumentMeta).where(DocumentMeta.team_id == user.active_team_id)
    if dataset_id:
        query = query.where(DocumentMeta.ragflow_dataset_id == dataset_id)
    if cat_filter:
        query = query.where(DocumentMeta.category_path.startswith(cat_filter))
    if keyword:
        query = query.where(DocumentMeta.filename.contains(keyword))
    if status:
        query = query.where(DocumentMeta.status == status)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(
        query.order_by(DocumentMeta.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    docs = result.scalars().all()

    # 统计当前筛选范围内的异常记录数（与文档列表同范围）
    orphan_query = select(func.count()).where(
        DocumentMeta.team_id == user.active_team_id,
        DocumentMeta.status == STATUS_ERROR,
    )
    if dataset_id:
        orphan_query = orphan_query.where(DocumentMeta.ragflow_dataset_id == dataset_id)
    orphan_result = await db.execute(orphan_query)
    orphan_count = orphan_result.scalar() or 0

    return {
        "items": [
            {
                "id": d.id, "filename": d.filename, "file_type": d.file_type,
                "file_size": d.file_size, "category_path": d.category_path,
                "version": d.version, "quality_score": d.quality_score,
                "is_expired": d.is_expired,
                "status": d.status,
                "ragflow_document_id": d.ragflow_document_id,
                "progress": d.progress,
                "last_synced_at": d.last_synced_at.isoformat() if d.last_synced_at else None,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
            } for d in docs
        ],
        "total": total,
        "orphan_count": orphan_count,
    }


@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档详情"""
    result = await db.execute(
        select(DocumentMeta).where(DocumentMeta.id == doc_id, DocumentMeta.team_id == user.active_team_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {
        "id": doc.id, "filename": doc.filename, "file_type": doc.file_type,
        "file_size": doc.file_size, "category_path": doc.category_path,
        "version": doc.version, "priority": doc.priority,
        "quality_score": doc.quality_score, "expires_at": doc.expires_at.isoformat() if doc.expires_at else None,
        "is_expired": doc.is_expired, "created_at": doc.created_at.isoformat(),
    }


@router.get("/{doc_id}/status")
async def get_document_status(
    doc_id: str,
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """从 RAGFlow 实时查询单文档状态（不依赖缓存）"""
    result = await db.execute(
        select(DocumentMeta).where(DocumentMeta.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if not doc.ragflow_document_id or not doc.ragflow_dataset_id:
        return {
            "doc_id": doc.id,
            "status": doc.status,
            "run": doc.run,
            "progress": doc.progress,
            "chunk_count": 0,
            "ragflow_document_id": doc.ragflow_document_id,
        }

    from app.adapters.ragflow_client import ragflow_client
    try:
        rf_doc = await ragflow_client.get_document_status(
            doc.ragflow_dataset_id, doc.ragflow_document_id
        )
        # 更新本地缓存
        doc.status = map_ragflow_status(rf_doc.run)
        doc.run = rf_doc.run
        doc.progress = rf_doc.progress
        doc.last_synced_at = datetime.utcnow()
        await db.flush()

        return {
            "doc_id": doc.id,
            "status": doc.status,
            "run": rf_doc.run,
            "progress": rf_doc.progress,
            "chunk_count": rf_doc.chunk_count,
            "ragflow_document_id": doc.ragflow_document_id,
        }
    except Exception as e:
        logger.warning(f"查询文档状态失败: {e}")
        return {
            "doc_id": doc.id,
            "status": doc.status,
            "run": doc.run,
            "progress": doc.progress,
            "chunk_count": 0,
            "ragflow_document_id": doc.ragflow_document_id,
            "error": str(e),
        }


@router.get("/{doc_id}/preview")
async def preview_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """预览文档 - 浏览器内联显示"""
    result = await db.execute(
        select(DocumentMeta).where(DocumentMeta.id == doc_id, DocumentMeta.team_id == user.active_team_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = _get_local_file(doc_id, doc.filename)
    if not file_path:
        raise HTTPException(status_code=404, detail="文件未找到，请重新上传")

    return FileResponse(
        path=str(file_path),
        media_type=doc.file_type or "application/octet-stream",
        filename=doc.filename,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(doc.filename)}"},
    )


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下载文档 - 强制下载"""
    result = await db.execute(
        select(DocumentMeta).where(DocumentMeta.id == doc_id, DocumentMeta.team_id == user.active_team_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = _get_local_file(doc_id, doc.filename)
    if not file_path:
        raise HTTPException(status_code=404, detail="文件未找到，请重新上传")

    return FileResponse(
        path=str(file_path),
        media_type=doc.file_type or "application/octet-stream",
        filename=doc.filename,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(doc.filename)}"},
    )


@router.post("/{doc_id}/parse")
async def parse_document(
    doc_id: str,
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """手动触发单文档解析（仅 pending/error 状态允许）"""
    result = await db.execute(
        select(DocumentMeta).where(DocumentMeta.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if doc.status not in PARSABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"文档当前状态不允许解析（当前状态: {doc.status}）"
        )

    if not doc.ragflow_document_id or not doc.ragflow_dataset_id:
        raise HTTPException(status_code=400, detail="文档缺少 RAGFlow 信息，无法解析")

    try:
        parse_ok = await sandbox_service.auto_parse_document(
            doc.filename, doc.ragflow_document_id, dataset_id=doc.ragflow_dataset_id
        )
        doc.status = STATUS_PARSING if parse_ok else STATUS_ERROR
    except Exception as e:
        logger.error(f"手动解析触发失败: {e}")
        doc.status = STATUS_ERROR

    await db.flush()
    return {"message": "解析已触发", "doc_id": doc.id, "status": doc.status}


@router.put("/{doc_id}")
async def update_document(
    doc_id: str,
    category_path: Optional[str] = None,
    priority: Optional[int] = None,
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新文档元数据"""
    result = await db.execute(select(DocumentMeta).where(DocumentMeta.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if category_path is not None:
        doc.category_path = category_path
    if priority is not None:
        doc.priority = priority
    await db.flush()
    return {"message": "更新成功"}


@router.post("/{doc_id}/replace")
async def replace_document(
    doc_id: str,
    file: UploadFile = File(...),
    parse_mode: str = Form(default=""),
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """版本替换文档 - 同步删旧+上新到 RAGFlow"""
    result = await db.execute(select(DocumentMeta).where(DocumentMeta.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_content = await file.read()
    old_ragflow_id = doc.ragflow_document_id
    ragflow_dataset_id = doc.ragflow_dataset_id or ""

    # 同步删除旧 RAGFlow 文档
    if old_ragflow_id and ragflow_dataset_id:
        try:
            await sandbox_service.delete_from_dataset(ragflow_dataset_id, old_ragflow_id)
            logger.info(f"替换-旧文档已删除: {old_ragflow_id}")
        except Exception as e:
            logger.warning(f"替换-删除旧文档失败: {e}")

    # 同步上传新文档到 RAGFlow
    new_ragflow_id = None
    if ragflow_dataset_id:
        try:
            new_ragflow_id = await sandbox_service.upload_to_dataset(
                file.filename or doc.filename, file_content,
                file.content_type or doc.file_type,
                dataset_id=ragflow_dataset_id,
            )
        except Exception as e:
            logger.error(f"替换-RAGFlow上传失败: {e}")
        if not new_ragflow_id:
            raise HTTPException(status_code=500, detail="替换文档上传到 RAGFlow 失败")

    # 更新元数据
    doc.version += 1
    doc.filename = file.filename or doc.filename
    doc.file_type = file.content_type or doc.file_type
    doc.file_size = len(file_content)
    doc.ragflow_document_id = new_ragflow_id
    doc.status = STATUS_PENDING

    # 确定解析模式并触发
    actual_parse_mode = parse_mode or await _get_default_parse_mode(db)
    if actual_parse_mode == "auto" and new_ragflow_id and ragflow_dataset_id:
        try:
            parse_ok = await sandbox_service.auto_parse_document(
                doc.filename, new_ragflow_id, dataset_id=ragflow_dataset_id
            )
            doc.status = STATUS_PARSING if parse_ok else STATUS_ERROR
        except Exception as e:
            logger.warning(f"替换-自动解析触发失败: {e}")
            doc.status = STATUS_ERROR

    await db.flush()

    # 保存到本地（覆盖旧文件）
    doc_dir = UPLOAD_DIR / doc.id
    if doc_dir.exists():
        for old_file in doc_dir.iterdir():
            old_file.unlink()
    _save_file_locally(doc.id, doc.filename, file_content)

    return {
        "message": "替换成功",
        "version": doc.version,
        "status": doc.status,
        "ragflow_document_id": new_ragflow_id,
        "ragflow_syncing": False,
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    user: User = Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除文档（同步删除 RAGFlow + 本地文件 + 数据库记录）"""
    result = await db.execute(select(DocumentMeta).where(DocumentMeta.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 使用文档自身记录的 dataset_id 删除 RAGFlow 文档
    ragflow_deleted = False
    if doc.ragflow_document_id and doc.ragflow_dataset_id:
        try:
            await sandbox_service.delete_from_dataset(
                doc.ragflow_dataset_id, doc.ragflow_document_id
            )
            ragflow_deleted = True
        except Exception as e:
            logger.warning(f"RAGFlow文档删除失败: {e}")

    # 清理本地文件
    _cleanup_local_file(doc.id)

    await db.delete(doc)
    await db.flush()
    return {"message": "删除成功", "ragflow_deleted": ragflow_deleted}


@router.get("/{doc_id}/versions")
async def get_versions(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取版本历史"""
    result = await db.execute(select(DocumentMeta).where(DocumentMeta.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"current_version": doc.version, "history": [{"version": doc.version, "updated_at": doc.updated_at.isoformat()}]}

