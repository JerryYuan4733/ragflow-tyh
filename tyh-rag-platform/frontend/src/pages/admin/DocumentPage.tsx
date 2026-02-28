import { useState, useEffect } from 'react';
import { Table, Button, Input, Upload, Space, Tag, Popconfirm, Tree, message, Modal, Select, Alert, Radio } from 'antd';
import {
    UploadOutlined, SearchOutlined, DeleteOutlined,
    InboxOutlined, FolderOutlined, FileTextOutlined,
    CheckCircleOutlined, SyncOutlined,
    DownloadOutlined, EyeOutlined, SwapOutlined,
    FolderAddOutlined, DatabaseOutlined,
    ClockCircleOutlined, CloseCircleOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { documentService } from '../../services/documentService';
import { useAuthStore } from '../../stores/authStore';
import api from '../../services/api';
import { formatTime } from '../../utils/timeFormat';

const { Dragger } = Upload;

export default function DocumentPage() {
    const [documents, setDocuments] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [keyword, setKeyword] = useState('');
    const [uploadModalOpen, setUploadModalOpen] = useState(false);
    const [selectedCategory, setSelectedCategory] = useState('/');
    // Dynamic category tree
    const [categoryTree, setCategoryTree] = useState<any[]>([]);
    const [categoryModalOpen, setCategoryModalOpen] = useState(false);
    const [newCategoryName, setNewCategoryName] = useState('');
    const [parentCategoryKey, setParentCategoryKey] = useState('/');
    // Replace modal
    const [replaceModalOpen, setReplaceModalOpen] = useState(false);
    const [replaceDocId, setReplaceDocId] = useState('');

    // 团队知识库
    const [teamDatasets, setTeamDatasets] = useState<any[]>([]);
    const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
    const [datasetsLoading, setDatasetsLoading] = useState(true);

    // 文档管理功能优化新增状态
    const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
    const [syncing, setSyncing] = useState(false);
    const [orphanCount, setOrphanCount] = useState(0);
    const [parseMode, setParseMode] = useState<'auto' | 'manual'>('auto');
    const user = useAuthStore((s) => s.user);
    const canSwitchDataset = user?.role === 'it_admin' || user?.role === 'kb_admin';
    const hasDatasets = teamDatasets.length > 0;

    // 文档分类分配弹窗状态
    const [categoryAssignModalOpen, setCategoryAssignModalOpen] = useState(false);
    const [assignTargetCategory, setAssignTargetCategory] = useState('/');

    // 权限判断：非普通用户可操作分类
    const canManageCategory = user?.role === 'it_admin' || user?.role === 'kb_admin';

    // 空树数据（无默认分类）
    const emptyTreeData = [
        { title: '全部文档', key: '/', icon: <FolderOutlined /> },
    ];

    // 加载动态分类树
    const loadCategories = async () => {
        try {
            const res = await api.get('/documents/categories');
            if (res.data && res.data.length > 0) {
                const buildTree = (items: any[]): any[] => items.map(item => ({
                    title: item.name,
                    key: item.path || `/${item.name}`,
                    icon: <FolderOutlined />,
                    children: item.children ? buildTree(item.children) : undefined,
                }));
                setCategoryTree([{
                    title: '全部文档', key: '/', icon: <FolderOutlined />,
                    children: buildTree(res.data),
                }]);
            } else {
                setCategoryTree(emptyTreeData);
            }
        } catch {
            setCategoryTree(emptyTreeData);
        }
    };

    // 删除分类
    const handleDeleteCategory = async (path: string) => {
        try {
            await documentService.deleteCategory(path);
            message.success('分类已删除');
            setSelectedCategory('/');
            loadCategories();
            loadDocuments();
        } catch {
            message.error('删除分类失败');
        }
    };

    // 批量分配文档分类
    const handleBatchCategory = async () => {
        if (selectedRowKeys.length === 0) return;
        try {
            await documentService.batchUpdateCategory(selectedRowKeys, assignTargetCategory);
            message.success('文档分类已更新');
            setCategoryAssignModalOpen(false);
            setSelectedRowKeys([]);
            loadDocuments();
        } catch {
            message.error('分类更新失败');
        }
    };

    const loadDocuments = async () => {
        try {
            const res = await documentService.list({
                page, page_size: pageSize, keyword,
                category: selectedCategory !== '/' ? selectedCategory : undefined,
                dataset_id: selectedDatasetId || undefined,
            });
            setDocuments(res.data.items || []);
            setTotal(res.data.total || 0);
            setOrphanCount(res.data.orphan_count || 0);
        } catch { }
    };

    // 刷新同步
    const handleSync = async () => {
        setSyncing(true);
        try {
            const res = await documentService.sync();
            const d = res.data;
            message.success(`同步完成：新增 ${d.new_docs} 个，更新 ${d.updated_docs} 个，异常 ${d.orphan_docs} 个`);
            loadDocuments();
        } catch {
            message.error('同步失败');
        } finally {
            setSyncing(false);
        }
    };

    // 批量解析
    const handleBatchParse = async () => {
        if (selectedRowKeys.length === 0) return;
        try {
            const res = await documentService.batchParse(selectedRowKeys);
            const d = res.data;
            message.success(`批量解析：成功 ${d.success} 个，失败 ${d.failed} 个`);
            setSelectedRowKeys([]);
            loadDocuments();
        } catch {
            message.error('批量解析失败');
        }
    };

    // 单文档解析
    const handleParse = async (docId: string) => {
        try {
            await documentService.parse(docId);
            message.success('解析已触发');
            loadDocuments();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '解析触发失败');
        }
    };

    // 清理异常记录
    const handleCleanupOrphans = async () => {
        try {
            const res = await documentService.cleanupOrphans(selectedDatasetId || undefined);
            message.success(`已清理 ${res.data.cleaned} 个异常记录`);
            loadDocuments();
        } catch {
            message.error('清理失败');
        }
    };

    // 加载团队绑定的知识库列表
    const loadTeamDatasets = async () => {
        setDatasetsLoading(true);
        try {
            const res = await documentService.getMyDatasets();
            const items = res.data?.items || [];
            setTeamDatasets(items);
            // 自动选中第一个知识库
            if (items.length > 0 && !selectedDatasetId) {
                setSelectedDatasetId(items[0].ragflow_dataset_id);
            }
        } catch {
            setTeamDatasets([]);
        } finally {
            setDatasetsLoading(false);
        }
    };

    // 加载默认解析模式
    const loadParseMode = async () => {
        try {
            const res = await documentService.getParseMode();
            if (res.data?.parse_mode) setParseMode(res.data.parse_mode);
        } catch { }
    };

    useEffect(() => { loadCategories(); loadTeamDatasets(); loadParseMode(); }, []);
    // 等待知识库加载完成后再拉取文档，避免空 datasetId 拉取全团队数据的竞态问题
    useEffect(() => {
        if (!datasetsLoading) {
            loadDocuments();
        }
    }, [page, pageSize, keyword, selectedCategory, selectedDatasetId, datasetsLoading]);

    const handleDelete = async (id: string) => {
        try {
            await documentService.delete(id);
            message.success('已删除');
            loadDocuments();
        } catch { }
    };

    const handleDownload = async (id: string, filename: string) => {
        try {
            const response = await fetch(`/api/v1/documents/${id}/download`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
            });
            if (!response.ok) throw new Error('下载失败');
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.click();
            URL.revokeObjectURL(url);
        } catch {
            message.error('下载失败');
        }
    };

    const handleAddCategory = async () => {
        if (!newCategoryName.trim()) return;
        try {
            await api.post('/documents/categories', {
                name: newCategoryName.trim(),
                parent_path: parentCategoryKey === '/' ? null : parentCategoryKey,
            });
            message.success('分类已创建');
            setCategoryModalOpen(false);
            setNewCategoryName('');
            loadCategories();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '创建分类失败');
        }
    };

    const uploadProps: UploadProps = {
        name: 'file',
        multiple: true,
        action: '/api/v1/documents',
        headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
        data: { category_path: selectedCategory, dataset_id: selectedDatasetId, parse_mode: parseMode },
        accept: '.pdf,.ppt,.pptx,.doc,.docx,.xls,.xlsx,.txt,.csv',
        onChange(info) {
            // 统一刷新：判断所有文件是否全部完成
            const allDone = info.fileList.every(f => f.status === 'done' || f.status === 'error');
            if (allDone && info.fileList.length > 0) {
                const successCount = info.fileList.filter(f => f.status === 'done').length;
                const errorCount = info.fileList.filter(f => f.status === 'error').length;
                if (errorCount > 0) {
                    message.warning(`上传完成：${successCount} 个成功，${errorCount} 个失败`);
                } else if (successCount > 0) {
                    message.success(`${successCount} 个文件上传成功`);
                }
                loadDocuments();
            }
        },
    };

    const replaceUploadProps: UploadProps = {
        name: 'file',
        action: `/api/v1/documents/${replaceDocId}/replace`,
        headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
        accept: '.pdf,.ppt,.pptx,.doc,.docx,.xls,.xlsx,.txt,.csv',
        maxCount: 1,
        onChange(info) {
            if (info.file.status === 'done') {
                message.success('文档已替换');
                setReplaceModalOpen(false);
                loadDocuments();
            } else if (info.file.status === 'error') {
                message.error('替换失败');
            }
        },
    };

    const statusTag = (status: string) => {
        const map: Record<string, { color: string; icon: any; text: string }> = {
            pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待解析' },
            uploading: { color: 'processing', icon: <SyncOutlined spin />, text: '上传中' },
            parsing: { color: 'processing', icon: <SyncOutlined spin />, text: '解析中' },
            ready: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
            error: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
        };
        const s = map[status] || { color: 'default', icon: null, text: status || '未知' };
        return <Tag color={s.color} icon={s.icon}>{s.text}</Tag>;
    };

    const columns = [
        {
            title: '文件名', dataIndex: 'filename', ellipsis: true,
            render: (v: string) => <><FileTextOutlined style={{ marginRight: 4 }} />{v}</>
        },
        {
            title: '大小', dataIndex: 'file_size', width: 90,
            render: (v: number) => v ? `${(v / 1024).toFixed(1)}KB` : '-'
        },
        { title: '状态', dataIndex: 'status', width: 90, render: statusTag },
        {
            title: '质量', dataIndex: 'quality_score', width: 70,
            render: (v: number) => v ? <Tag color={v > 60 ? 'green' : 'orange'}>{v}</Tag> : '-'
        },
        { title: '版本', dataIndex: 'version', width: 60 },
        {
            title: '更新时间', dataIndex: 'updated_at', width: 180,
            render: (v: string) => formatTime(v),
        },
        {
            title: '操作', width: 320,
            render: (_: any, r: any) => (
                <Space size="small">
                    <Button type="link" size="small" icon={<EyeOutlined />} disabled title="预览功能暂不可用">预览</Button>
                    <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => handleDownload(r.id, r.filename)}>下载</Button>
                    {(r.status === 'pending' || r.status === 'error') && (
                        <Button type="link" size="small" icon={<ThunderboltOutlined />} onClick={() => handleParse(r.id)}>解析</Button>
                    )}
                    <Button type="link" size="small" icon={<SwapOutlined />} onClick={() => { setReplaceDocId(r.id); setReplaceModalOpen(true); }}>替换</Button>
                    <Popconfirm title="确认删除?" description="将同时从 RAGFlow 中删除该文档" onConfirm={() => handleDelete(r.id)}>
                        <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div className="fade-in" style={{ display: 'flex', gap: 16 }}>
            {/* 左栏目录树 */}
            <div style={{
                width: 220, flexShrink: 0, padding: 16,
                background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--border)',
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h4 style={{ margin: 0 }}>📁 文档目录</h4>
                    {canManageCategory && (
                        <Button type="text" size="small" icon={<FolderAddOutlined />}
                            onClick={() => { setParentCategoryKey(selectedCategory); setCategoryModalOpen(true); }}
                            title="新增分类"
                        />
                    )}
                </div>
                <Tree
                    treeData={categoryTree.length > 0 ? categoryTree : emptyTreeData}
                    defaultExpandAll
                    selectedKeys={[selectedCategory]}
                    onSelect={(keys) => keys.length && setSelectedCategory(keys[0] as string)}
                    style={{ background: 'transparent' }}
                />
                {/* 删除当前选中分类按钮 */}
                {canManageCategory && selectedCategory !== '/' && (
                    <Popconfirm title="确认删除该分类？" description="该分类下的文档将回归根目录" onConfirm={() => handleDeleteCategory(selectedCategory)}>
                        <Button type="text" size="small" danger icon={<DeleteOutlined />} style={{ marginTop: 8, width: '100%' }}>
                            删除当前分类
                        </Button>
                    </Popconfirm>
                )}
            </div>

            {/* 主区域 */}
            <div style={{ flex: 1 }}>
                {/* 知识库状态提示 */}
                {!datasetsLoading && !hasDatasets && (
                    <Alert
                        type="warning"
                        showIcon
                        message="当前团队未绑定知识库"
                        description="请联系IT管理员在「团队管理」中绑定知识库后，才能上传和管理文档。"
                        style={{ marginBottom: 16 }}
                    />
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, gap: 12 }}>
                    <Input.Search
                        placeholder="搜索文档..."
                        prefix={<SearchOutlined />}
                        value={keyword}
                        onChange={e => setKeyword(e.target.value)}
                        onSearch={loadDocuments}
                        style={{ width: 300 }}
                        allowClear
                    />

                    {/* 知识库选择器：多知识库时显示，非普通用户可切换 */}
                    {hasDatasets && teamDatasets.length > 1 && (
                        <Select
                            value={selectedDatasetId}
                            onChange={setSelectedDatasetId}
                            disabled={!canSwitchDataset}
                            style={{ minWidth: 200 }}
                            suffixIcon={<DatabaseOutlined />}
                            options={teamDatasets.map((ds: any) => ({
                                value: ds.ragflow_dataset_id,
                                label: ds.ragflow_dataset_name,
                            }))}
                        />
                    )}
                    {hasDatasets && teamDatasets.length === 1 && (
                        <Tag icon={<DatabaseOutlined />} color="blue">
                            {teamDatasets[0].ragflow_dataset_name}
                        </Tag>
                    )}

                    <Space>
                        <Button
                            icon={<SyncOutlined spin={syncing} />}
                            onClick={handleSync}
                            loading={syncing}
                            disabled={!hasDatasets}
                        >
                            刷新同步
                        </Button>
                        {selectedRowKeys.length > 0 && (
                            <>
                                <Button icon={<ThunderboltOutlined />} onClick={handleBatchParse}>
                                    批量解析 ({selectedRowKeys.length})
                                </Button>
                                {canManageCategory && (
                                    <Button icon={<FolderOutlined />} onClick={() => { setAssignTargetCategory('/'); setCategoryAssignModalOpen(true); }}>
                                        移动分类 ({selectedRowKeys.length})
                                    </Button>
                                )}
                            </>
                        )}
                        {orphanCount > 0 && (
                            <Popconfirm title={`确认清理 ${orphanCount} 个异常记录？`} onConfirm={handleCleanupOrphans}>
                                <Button danger icon={<DeleteOutlined />}>
                                    清理异常 ({orphanCount})
                                </Button>
                            </Popconfirm>
                        )}
                        <Button
                            type="primary"
                            icon={<UploadOutlined />}
                            onClick={() => setUploadModalOpen(true)}
                            disabled={!hasDatasets}
                        >
                            上传文档
                        </Button>
                    </Space>
                </div>

                <Table columns={columns} dataSource={documents} rowKey="id"
                    rowSelection={{
                        selectedRowKeys,
                        onChange: (keys) => setSelectedRowKeys(keys as string[]),
                    }}
                    pagination={{
                        current: page, total, pageSize,
                        showSizeChanger: true,
                        onChange: (p, ps) => { setPage(p); setPageSize(ps); },
                    }}
                />

                {/* 批量上传弹窗 */}
                <Modal title="上传文档" open={uploadModalOpen} onCancel={() => setUploadModalOpen(false)} footer={null} width={600}>
                    <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>解析模式：</span>
                        <Radio.Group value={parseMode} onChange={e => setParseMode(e.target.value)} size="small">
                            <Radio.Button value="auto">自动解析</Radio.Button>
                            <Radio.Button value="manual">仅上传</Radio.Button>
                        </Radio.Group>
                        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                            {parseMode === 'auto' ? '上传后自动触发解析' : '仅上传到 RAGFlow，需手动解析'}
                        </span>
                    </div>
                    <Dragger {...uploadProps} style={{ padding: 24 }}>
                        <p className="ant-upload-drag-icon"><InboxOutlined style={{ fontSize: 48, color: 'var(--primary)' }} /></p>
                        <p style={{ color: 'var(--text-primary)' }}>点击或拖拽文件到此区域上传</p>
                        <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                            支持 PDF、PPT、Word、Excel、TXT、CSV，单文件最大 50MB
                        </p>
                    </Dragger>
                    <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-elevated)', borderRadius: 8 }}>
                        <h4 style={{ marginBottom: 8 }}>📋 质量自检清单</h4>
                        <ul style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 2 }}>
                            <li>✅ 文档内容完整，无乱码或空白页</li>
                            <li>✅ 文件格式正确（PDF/PPT/Word/Excel/TXT）</li>
                            <li>✅ 核心信息清晰，结构化排版</li>
                            <li>✅ 无敏感或过期信息</li>
                            <li>✅ 文件名包含明确主题，便于检索</li>
                        </ul>
                    </div>
                </Modal>

                {/* 替换弹窗 */}
                <Modal title="替换文档" open={replaceModalOpen} onCancel={() => setReplaceModalOpen(false)} footer={null} width={500}>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
                        上传新版本文件，系统将保留历史版本并自动递增版本号。
                    </p>
                    <Dragger {...replaceUploadProps}>
                        <p className="ant-upload-drag-icon"><SwapOutlined style={{ fontSize: 36, color: 'var(--primary)' }} /></p>
                        <p style={{ color: 'var(--text-primary)' }}>拖拽新版本文件到此处</p>
                    </Dragger>
                </Modal>

                {/* 新增分类弹窗 */}
                <Modal title="新增文档分类" open={categoryModalOpen}
                    onOk={handleAddCategory} onCancel={() => { setCategoryModalOpen(false); setNewCategoryName(''); }}>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 12 }}>
                        在「{parentCategoryKey === '/' ? '根目录' : parentCategoryKey}」下创建新分类
                    </p>
                    <Input
                        placeholder="分类名称"
                        value={newCategoryName}
                        onChange={e => setNewCategoryName(e.target.value)}
                        onPressEnter={handleAddCategory}
                    />
                </Modal>

                {/* 文档分类分配弹窗 */}
                <Modal title="移动文档到分类" open={categoryAssignModalOpen}
                    onOk={handleBatchCategory} onCancel={() => setCategoryAssignModalOpen(false)}>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 12 }}>
                        将已选的 {selectedRowKeys.length} 个文档移动到以下分类：
                    </p>
                    <Select
                        value={assignTargetCategory}
                        onChange={setAssignTargetCategory}
                        style={{ width: '100%' }}
                        options={(() => {
                            // 从 categoryTree 递归提取扁平分类列表
                            const opts: { value: string; label: string }[] = [{ value: '/', label: '根目录' }];
                            const extract = (nodes: any[]) => {
                                for (const n of nodes) {
                                    if (n.key && n.key !== '/') opts.push({ value: n.key, label: n.title || n.key });
                                    if (n.children) extract(n.children);
                                }
                            };
                            extract(categoryTree);
                            return opts;
                        })()}
                    />
                </Modal>
            </div>
        </div>
    );
}
