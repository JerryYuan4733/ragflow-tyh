import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Modal, Form, Popconfirm, Upload, Drawer, Timeline, message, Select, Tag, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import {
    PlusOutlined, SearchOutlined, DeleteOutlined, EditOutlined,
    ImportOutlined, DownloadOutlined, HistoryOutlined, MoreOutlined, SyncOutlined, ReloadOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { qaService } from '../../services/qaService';
import { documentService } from '../../services/documentService';
import { formatTime } from '../../utils/timeFormat';

export default function QAPage() {
    const [qaList, setQaList] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [keyword, setKeyword] = useState('');
    const [modalOpen, setModalOpen] = useState(false);
    const [editItem, setEditItem] = useState<any>(null);
    const [importModalOpen, setImportModalOpen] = useState(false);
    const [versionDrawer, setVersionDrawer] = useState(false);
    const [versions, setVersions] = useState<any[]>([]);
    const [form] = Form.useForm();
    const [editorTab, setEditorTab] = useState<'edit' | 'preview'>('edit');
    // T-15.2~15.5: 知识库筛选 + 状态筛选
    const [datasetId, setDatasetId] = useState<string | undefined>(undefined);
    const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
    const [sourceFilter, setSourceFilter] = useState<string | undefined>(undefined);
    const [datasets, setDatasets] = useState<{ ragflow_dataset_id: string; ragflow_dataset_name: string }[]>([]);
    const [syncLoading, setSyncLoading] = useState<'to' | 'from' | null>(null);
    // T-3.1: 行选择状态
    const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
    // 推送弹窗状态
    const [syncModalOpen, setSyncModalOpen] = useState(false);
    const [syncTargetDataset, setSyncTargetDataset] = useState<string>('');
    // T-3.4: 推送分组预览
    const [pushGroups, setPushGroups] = useState<Record<string, { name: string; count: number }>>({});
    const [pushNoKbCount, setPushNoKbCount] = useState(0);
    const [pushTotalCount, setPushTotalCount] = useState(0);
    // 拉取弹窗状态
    const [pullModalOpen, setPullModalOpen] = useState(false);
    const [pullTargetDataset, setPullTargetDataset] = useState<string>('');

    // T-3.4: 打开推送弹窗时计算分组预览
    const openSyncModal = () => {
        const scope = selectedRowKeys.length > 0
            ? qaList.filter(q => selectedRowKeys.includes(q.id))
            : qaList.filter(q => q.status === 'active');
        const groups: Record<string, { name: string; count: number }> = {};
        let noKb = 0;
        for (const qa of scope) {
            if (qa.ragflow_dataset_id) {
                const key = qa.ragflow_dataset_id;
                if (!groups[key]) {
                    groups[key] = { name: qa.ragflow_dataset_name || key, count: 0 };
                }
                groups[key].count++;
            } else {
                noKb++;
            }
        }
        setPushGroups(groups);
        setPushNoKbCount(noKb);
        setPushTotalCount(scope.length);
        setSyncTargetDataset('');
        setSyncModalOpen(true);
    };

    // T-3.6: 推送确认（V3 分组路由 + 勾选推送）
    const handleSyncConfirm = async () => {
        if (pushNoKbCount > 0 && !syncTargetDataset) {
            message.warning('存在无所属知识库的QA，请选择目标知识库');
            return;
        }
        const qaIds = selectedRowKeys.length > 0 ? selectedRowKeys : undefined;
        const datasetIdParam = syncTargetDataset || undefined;
        setSyncLoading('to');
        try {
            const res = await qaService.syncToRagflow(datasetIdParam, qaIds);
            message.success(res.data?.message || '推送完成');
            setSyncModalOpen(false);
            setSelectedRowKeys([]);
            loadData();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '推送失败');
        } finally { setSyncLoading(null); }
    };

    // QA 反向同步：弹窗确认后执行
    const handlePullConfirm = async () => {
        setSyncLoading('from');
        try {
            // pullTargetDataset 为空表示全部知识库
            const res = await qaService.syncFromRagflow(pullTargetDataset || undefined);
            message.success(res.data?.message || '拉取完成');
            setPullModalOpen(false);
            loadData();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '拉取失败');
        } finally { setSyncLoading(null); }
    };

    const loadData = async () => {
        try {
            const res = await qaService.list({ page, page_size: pageSize, keyword, dataset_id: datasetId, status: statusFilter, source: sourceFilter });
            setQaList(res.data.items || []);
            setTotal(res.data.total || 0);
        } catch { }
    };

    // 加载团队绑定的知识库列表
    const loadDatasets = async () => {
        try {
            const res = await documentService.getMyDatasets();
            setDatasets(res.data?.items || []);
        } catch { setDatasets([]); }
    };

    useEffect(() => { loadData(); }, [page, pageSize, keyword, datasetId, statusFilter, sourceFilter]);
    useEffect(() => { loadDatasets(); }, []);

    // T-15.4: 状态切换
    const handleStatusChange = async (qaId: string, newStatus: string) => {
        try {
            await qaService.changeStatus(qaId, newStatus);
            message.success('状态已更新');
            loadData();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '操作失败');
        }
    };

    const handleSave = async () => {
        const values = await form.validateFields();
        try {
            if (editItem) {
                await qaService.update(editItem.id, values);
            } else {
                await qaService.create(values);
            }
            message.success('操作成功');
            setModalOpen(false);
            form.resetFields();
            setEditItem(null);
            setEditorTab('edit');
            loadData();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '操作失败');
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await qaService.delete(id);
            message.success('已删除');
            loadData();
        } catch { }
    };

    const showVersions = async (id: string) => {
        try {
            const res = await qaService.getVersions(id);
            setVersions(res.data.items || []);
            setVersionDrawer(true);
        } catch { }
    };

    const handleDownloadTemplate = async () => {
        try {
            const res = await qaService.downloadTemplate();
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const a = document.createElement('a');
            a.href = url;
            a.download = 'qa_template.xlsx';
            a.click();
        } catch { }
    };

    // Open modal prefilled (used by Ticket->QA flow)
    const openWithPrefill = (question?: string, answer?: string) => {
        setEditItem(null);
        form.resetFields();
        if (question || answer) {
            form.setFieldsValue({ question: question || '', answer: answer || '' });
        }
        setEditorTab('edit');
        setModalOpen(true);
    };
    // Expose on window for cross-page access
    useEffect(() => {
        (window as any).__qaPageOpenWithPrefill = openWithPrefill;
        return () => { delete (window as any).__qaPageOpenWithPrefill; };
    }, []);

    // T-15.3: 状态标签颜色映射
    const STATUS_MAP: Record<string, { color: string; label: string }> = {
        active: { color: 'green', label: '启用' },
        pending_review: { color: 'orange', label: '待审核' },
        disabled: { color: 'default', label: '禁用' },
    };

    // T-15.4: 状态操作菜单
    const getStatusMenuItems = (record: any): MenuProps['items'] => {
        const items: MenuProps['items'] = [];
        if (record.status !== 'active') items.push({ key: 'active', label: '启用' });
        if (record.status !== 'disabled') items.push({ key: 'disabled', label: '禁用' });
        if (record.status !== 'pending_review') items.push({ key: 'pending_review', label: '设为待审核' });
        return items;
    };

    const columns = [
        { title: '问题', dataIndex: 'question', ellipsis: true },
        {
            title: '答案', dataIndex: 'answer', ellipsis: true, width: 250,
            render: (v: string) => <span style={{ color: 'var(--text-secondary)' }}>{v}</span>
        },
        {
            title: '状态', dataIndex: 'status', width: 90,
            render: (v: string) => {
                const s = STATUS_MAP[v] || { color: 'default', label: v };
                return <Tag color={s.color}>{s.label}</Tag>;
            },
        },
        {
            title: '来源', dataIndex: 'source', width: 90,
            render: (v: string) => {
                const map: Record<string, string> = { manual: '手动', transfer: '转人工', ragflow_sync: '同步', import: '导入' };
                return map[v] || v;
            },
        },
        {
            title: '所属知识库', dataIndex: 'ragflow_dataset_name', width: 120, ellipsis: true,
            render: (v: string) => v ? <Tag>{v}</Tag> : <Tag color="default">无</Tag>,
        },
        { title: '版本', dataIndex: 'version', width: 60 },
        {
            title: '更新时间', dataIndex: 'updated_at', width: 160,
            render: (v: string) => formatTime(v),
        },
        {
            title: '操作', width: 200,
            render: (_: any, r: any) => (
                <Space size="small">
                    <Button type="link" size="small" icon={<EditOutlined />}
                        onClick={() => { setEditItem(r); form.setFieldsValue(r); setEditorTab('edit'); setModalOpen(true); }} />
                    <Button type="link" size="small" icon={<HistoryOutlined />}
                        onClick={() => showVersions(r.id)}>版本</Button>
                    <Popconfirm title="确认删除?" onConfirm={() => handleDelete(r.id)}>
                        <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                    <Dropdown menu={{ items: getStatusMenuItems(r), onClick: ({ key }) => handleStatusChange(r.id, key) }}>
                        <Button type="link" size="small" icon={<MoreOutlined />} />
                    </Dropdown>
                </Space>
            ),
        },
    ];

    const answerValue = Form.useWatch('answer', form) || '';

    return (
        <div className="fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
                <Space>
                    <Input.Search
                        placeholder="搜索Q&A..."
                        prefix={<SearchOutlined />}
                        value={keyword}
                        onChange={e => setKeyword(e.target.value)}
                        onSearch={loadData}
                        style={{ width: 240 }}
                        allowClear
                    />
                    <Select
                        placeholder="知识库筛选"
                        allowClear
                        value={datasetId}
                        onChange={v => { setDatasetId(v); setPage(1); }}
                        style={{ width: 180 }}
                        options={[
                            { value: '__none__', label: '无' },
                            ...datasets.map(ds => ({
                                value: ds.ragflow_dataset_id,
                                label: ds.ragflow_dataset_name,
                            })),
                        ]}
                    />
                    <Select
                        placeholder="状态筛选"
                        allowClear
                        value={statusFilter}
                        onChange={v => { setStatusFilter(v); setPage(1); }}
                        style={{ width: 120 }}
                        options={[
                            { value: 'active', label: '启用' },
                            { value: 'pending_review', label: '待审核' },
                            { value: 'disabled', label: '禁用' },
                        ]}
                    />
                    <Select
                        placeholder="来源筛选"
                        allowClear
                        value={sourceFilter}
                        onChange={v => { setSourceFilter(v); setPage(1); }}
                        style={{ width: 120 }}
                        options={[
                            { value: 'manual', label: '手动' },
                            { value: 'transfer', label: '转人工' },
                            { value: 'ragflow_sync', label: '同步' },
                            { value: 'import', label: '导入' },
                        ]}
                    />
                    <Button icon={<ReloadOutlined />} onClick={loadData} title="刷新" />
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>共 {total} 条</span>
                </Space>
                <Space>
                    <Button
                        icon={<SyncOutlined spin={syncLoading === 'to'} />}
                        onClick={openSyncModal}
                        loading={syncLoading === 'to'}
                        disabled={!!syncLoading}
                    >{selectedRowKeys.length > 0 ? `推送选中(${selectedRowKeys.length}条)` : '推送到RAGFlow'}</Button>
                    <Button
                        icon={<SyncOutlined spin={syncLoading === 'from'} />}
                        onClick={() => setPullModalOpen(true)}
                        loading={syncLoading === 'from'}
                        disabled={!!syncLoading}
                    >从RAGFlow拉取</Button>
                    <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>下载模板</Button>
                    <Button icon={<ImportOutlined />} onClick={() => setImportModalOpen(true)}>导入</Button>
                    <Button type="primary" icon={<PlusOutlined />}
                        onClick={() => openWithPrefill()}>
                        新增Q&A
                    </Button>
                </Space>
            </div>

            <Table columns={columns} dataSource={qaList} rowKey="id"
                rowSelection={{
                    selectedRowKeys,
                    onChange: (keys) => setSelectedRowKeys(keys as string[]),
                    preserveSelectedRowKeys: true,
                }}
                pagination={{
                    current: page, total, pageSize,
                    showSizeChanger: true,
                    onChange: (p, ps) => { setPage(p); setPageSize(ps); },
                }}
            />

            {/* 新增/编辑弹窗 - 带Markdown预览 */}
            <Modal title={editItem ? '编辑Q&A' : '新增Q&A'} open={modalOpen}
                onOk={handleSave} onCancel={() => { setModalOpen(false); setEditItem(null); setEditorTab('edit'); }} width={720}>
                <Form form={form} layout="vertical">
                    <Form.Item name="question" label="问题" rules={[{ required: true, message: '请输入问题' }]}>
                        <Input.TextArea rows={2} placeholder="用户可能会问的问题" />
                    </Form.Item>
                    <Form.Item label={
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            <span>答案</span>
                            <div className="qa-editor-tabs">
                                <button type="button" className={`qa-editor-tab ${editorTab === 'edit' ? 'active' : ''}`}
                                    onClick={() => setEditorTab('edit')}>编辑</button>
                                <button type="button" className={`qa-editor-tab ${editorTab === 'preview' ? 'active' : ''}`}
                                    onClick={() => setEditorTab('preview')}>预览</button>
                            </div>
                        </div>
                    }>
                        {editorTab === 'edit' ? (
                            <Form.Item name="answer" noStyle rules={[{ required: true, message: '请输入答案' }]}>
                                <Input.TextArea rows={8} placeholder="标准答案（支持 Markdown 格式：**加粗**、- 列表、```代码```）" />
                            </Form.Item>
                        ) : (
                            <div style={{
                                minHeight: 200, padding: 16, border: '1px solid var(--border)',
                                borderRadius: 8, background: 'var(--bg-elevated)',
                            }}>
                                {answerValue ? (
                                    <div className="md-content">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{answerValue}</ReactMarkdown>
                                    </div>
                                ) : (
                                    <span style={{ color: 'var(--text-muted)' }}>暂无内容</span>
                                )}
                            </div>
                        )}
                    </Form.Item>
                </Form>
            </Modal>

            {/* 推送到RAGFlow弹窗（V3 分组预览） */}
            <Modal
                title="推送到 RAGFlow"
                open={syncModalOpen}
                onOk={handleSyncConfirm}
                onCancel={() => { setSyncModalOpen(false); setSyncTargetDataset(''); }}
                confirmLoading={syncLoading === 'to'}
                okButtonProps={{ disabled: pushNoKbCount > 0 && !syncTargetDataset }}
                okText="确认推送"
            >
                {pushTotalCount === 0 ? (
                    <p style={{ color: 'var(--text-muted)' }}>当前无符合条件的待推送 QA</p>
                ) : (
                    <>
                        <p style={{ marginBottom: 8, fontWeight: 500 }}>推送预览（共 {pushTotalCount} 条）：</p>
                        <div style={{ marginBottom: 12, padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 6 }}>
                            {Object.entries(pushGroups).map(([id, g]) => (
                                <div key={id} style={{ fontSize: 13, padding: '2px 0' }}>
                                    <Tag color="blue">{g.name}</Tag> {g.count} 条（已有归属，自动推送）
                                </div>
                            ))}
                            {pushNoKbCount > 0 && (
                                <div style={{ fontSize: 13, padding: '2px 0' }}>
                                    <Tag color="orange">无归属</Tag> {pushNoKbCount} 条 → 需选择目标知识库
                                </div>
                            )}
                        </div>
                        {pushNoKbCount > 0 && (
                            <>
                                <p style={{ marginBottom: 8 }}>目标知识库（无归属的QA推送到此）：</p>
                                <Select
                                    style={{ width: '100%' }}
                                    placeholder="请选择知识库"
                                    value={syncTargetDataset || undefined}
                                    onChange={setSyncTargetDataset}
                                    options={datasets.map(d => ({
                                        value: d.ragflow_dataset_id,
                                        label: d.ragflow_dataset_name,
                                    }))}
                                />
                            </>
                        )}
                        <p style={{ marginTop: 10, color: 'var(--text-muted)', fontSize: 12 }}>
                            已修改的同步QA也将一并推送更新。已有归属的QA只能推到原知识库。
                        </p>
                    </>
                )}
            </Modal>

            {/* 从RAGFlow拉取弹窗 */}
            <Modal
                title="从 RAGFlow 拉取"
                open={pullModalOpen}
                onOk={handlePullConfirm}
                onCancel={() => { setPullModalOpen(false); setPullTargetDataset(''); }}
                confirmLoading={syncLoading === 'from'}
                okText="确认拉取"
            >
                <p style={{ marginBottom: 12 }}>选择知识库：</p>
                <Select
                    style={{ width: '100%' }}
                    placeholder="全部知识库"
                    allowClear
                    value={pullTargetDataset || undefined}
                    onChange={(v) => setPullTargetDataset(v || '')}
                    options={datasets.map(d => ({
                        value: d.ragflow_dataset_id,
                        label: d.ragflow_dataset_name,
                    }))}
                />
                <p style={{ marginTop: 10, color: 'var(--text-muted)', fontSize: 12 }}>
                    不选择则拉取团队全部知识库。差异同步：新增、更新答案、删除已不存在的 QA。
                </p>
            </Modal>

            {/* 导入弹窗 */}
            <Modal title="导入Q&A" open={importModalOpen} onCancel={() => setImportModalOpen(false)} footer={null}>
                <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
                    请先下载模板，按格式填写后上传Excel文件。
                </p>
                <Upload.Dragger
                    name="file"
                    action="/api/v1/qa-pairs/import"
                    headers={{ Authorization: `Bearer ${localStorage.getItem('token') || ''}` }}
                    accept=".xlsx,.xls"
                    onChange={(info) => {
                        if (info.file.status === 'done') {
                            message.success(`导入成功，共${info.file.response?.count || 0}条`);
                            setImportModalOpen(false);
                            loadData();
                        }
                    }}
                >
                    <p style={{ color: 'var(--text-primary)' }}>点击或拖拽Excel文件到此处</p>
                </Upload.Dragger>
            </Modal>

            {/* 版本历史Drawer */}
            <Drawer title="版本历史" open={versionDrawer} onClose={() => setVersionDrawer(false)} width={400}>
                {versions.length > 0 ? (
                    <Timeline
                        items={versions.map((v: any) => ({
                            color: 'blue',
                            children: (
                                <div>
                                    <div style={{ fontWeight: 600 }}>v{v.version}</div>
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{formatTime(v.updated_at)}</div>
                                    {v.question && <div style={{ marginTop: 4, fontSize: 13 }}>Q: {v.question}</div>}
                                    {v.answer && <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>A: {v.answer?.slice(0, 100)}</div>}
                                </div>
                            ),
                        }))}
                    />
                ) : (
                    <p style={{ color: 'var(--text-muted)' }}>暂无版本记录</p>
                )}
            </Drawer>
        </div>
    );
}
