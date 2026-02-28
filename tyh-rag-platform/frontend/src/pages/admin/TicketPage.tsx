import { useState, useEffect } from 'react';
import { Table, Button, Tag, Space, Select, Card, Row, Col, Statistic, Drawer, Timeline, Descriptions, Empty, Modal, Form, Input, Checkbox, message } from 'antd';
import {
    ClockCircleOutlined, CheckCircleOutlined, SyncOutlined,
    SafetyCertificateOutlined, UserOutlined,
    PlusOutlined,
} from '@ant-design/icons';
import { ticketService } from '../../services/ticketService';
import { qaService } from '../../services/qaService';
import { useAuthStore } from '../../stores/authStore';
import { formatTime } from '../../utils/timeFormat';

export default function TicketPage() {
    const user = useAuthStore(s => s.user);
    const [tickets, setTickets] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [statusFilter, setStatusFilter] = useState<string | undefined>();
    const [detailDrawer, setDetailDrawer] = useState(false);
    const [currentTicket, setCurrentTicket] = useState<any>(null);
    const [stats, setStats] = useState({ pending: 0, processing: 0, resolved: 0, verified: 0 });
    // Resolve note modal
    const [resolveModalOpen, setResolveModalOpen] = useState(false);
    const [resolveId, setResolveId] = useState('');
    const [resolveNote, setResolveNote] = useState('');
    // T-16.1: 解决弹窗关联 QA 编辑
    const [resolveQA, setResolveQA] = useState<{ id?: string; question?: string; answer?: string; version?: number } | null>(null);
    const [resolveQAQuestion, setResolveQAQuestion] = useState('');
    const [resolveQAAnswer, setResolveQAAnswer] = useState('');
    const [approveQA, setApproveQA] = useState(true);
    // Create QA modal
    const [qaModalOpen, setQaModalOpen] = useState(false);
    const [qaForm] = Form.useForm();

    const loadTickets = async () => {
        try {
            const res = await ticketService.list({ page, page_size: pageSize, status: statusFilter });
            setTickets(res.data.items || []);
            setTotal(res.data.total || 0);
        } catch { }
    };

    const loadStats = async () => {
        try {
            const all = await ticketService.list({ page: 1 });
            const items = all.data.items || [];
            setStats({
                pending: items.filter((t: any) => t.status === 'pending').length,
                processing: items.filter((t: any) => t.status === 'processing').length,
                resolved: items.filter((t: any) => t.status === 'resolved').length,
                verified: items.filter((t: any) => t.status === 'verified').length,
            });
        } catch { }
    };

    useEffect(() => { loadTickets(); loadStats(); }, [page, pageSize, statusFilter]);

    const handleAssign = async (id: string) => {
        try {
            await ticketService.assign(id, user?.id || '');
            message.success('已认领');
            loadTickets(); loadStats();
        } catch { }
    };

    const handleResolveOpen = async (id: string) => {
        setResolveId(id);
        setResolveNote('');
        setResolveQA(null);
        setResolveQAQuestion('');
        setResolveQAAnswer('');
        setApproveQA(true);
        // T-16.1: 加载关联 QA 数据
        try {
            const res = await ticketService.get(id);
            if (res.data?.qa) {
                setResolveQA(res.data.qa);
                setResolveQAQuestion(res.data.qa.question || '');
                setResolveQAAnswer(res.data.qa.answer || '');
            }
        } catch { /* 无关联 QA */ }
        setResolveModalOpen(true);
    };

    const handleResolveSubmit = async () => {
        try {
            // T-16.3: 提交时携带 QA 修改内容 + 审核标记
            const qaData: { qa_question?: string; qa_answer?: string; approve_qa?: boolean } = {};
            if (resolveQA) {
                if (resolveQAQuestion !== resolveQA.question) qaData.qa_question = resolveQAQuestion;
                if (resolveQAAnswer !== resolveQA.answer) qaData.qa_answer = resolveQAAnswer;
                if (approveQA) qaData.approve_qa = true;
            }
            await ticketService.resolve(resolveId, resolveNote || '已处理', Object.keys(qaData).length > 0 ? qaData : undefined);
            message.success('已解决');
            setResolveModalOpen(false);
            loadTickets(); loadStats();
        } catch { }
    };

    const handleVerify = async (id: string) => {
        try {
            await ticketService.verify(id);
            message.success('已验证');
            loadTickets(); loadStats();
        } catch { }
    };

    const handleReopen = async (id: string) => {
        try {
            await ticketService.reopen(id, '重新处理');
            message.success('已重开');
            loadTickets(); loadStats();
        } catch { }
    };

    const showDetail = async (ticket: any) => {
        try {
            const res = await ticketService.get(ticket.id);
            setCurrentTicket(res.data);
        } catch {
            setCurrentTicket(ticket);
        }
        setDetailDrawer(true);
    };

    // Create QA from ticket (knowledge correction)
    const openCreateQA = () => {
        qaForm.resetFields();
        if (currentTicket) {
            qaForm.setFieldsValue({
                question: currentTicket.original_question || currentTicket.title || '',
                answer: '',
            });
        }
        setQaModalOpen(true);
    };

    const handleQASave = async () => {
        const values = await qaForm.validateFields();
        try {
            await qaService.create(values);
            message.success('Q&A已创建，知识修正完成');
            setQaModalOpen(false);
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '创建失败');
        }
    };

    const statusTag = (status: string) => {
        const map: Record<string, { color: string; icon: any; text: string }> = {
            pending: { color: 'warning', icon: <ClockCircleOutlined />, text: '待处理' },
            processing: { color: 'processing', icon: <SyncOutlined spin />, text: '处理中' },
            resolved: { color: 'success', icon: <CheckCircleOutlined />, text: '已解决' },
            verified: { color: 'cyan', icon: <SafetyCertificateOutlined />, text: '已验证' },
        };
        const s = map[status] || { color: 'default', icon: null, text: status };
        return <Tag color={s.color} icon={s.icon}>{s.text}</Tag>;
    };

    const columns = [
        {
            title: '工单标题', dataIndex: 'title', ellipsis: true,
            render: (v: string, r: any) => (
                <a onClick={() => showDetail(r)} style={{ color: 'var(--accent-blue)' }}>{v}</a>
            )
        },
        {
            title: '来源', dataIndex: 'source', width: 80,
            render: (v: string) => <Tag>{v === 'auto' ? '自动' : '手动'}</Tag>
        },
        { title: '状态', dataIndex: 'status', width: 100, render: statusTag },
        {
            title: '处理人', dataIndex: 'assigned_to_name', width: 100,
            render: (v: string) => v ? <span><UserOutlined style={{ marginRight: 4 }} />{v}</span> : <span style={{ color: 'var(--text-muted)' }}>未分配</span>
        },
        {
            title: '创建时间', dataIndex: 'created_at', width: 180,
            render: (v: string) => formatTime(v),
        },
        {
            title: '操作', width: 200,
            render: (_: any, r: any) => (
                <Space size="small">
                    {r.status === 'pending' && <Button size="small" style={{ background: '#6366f1', color: '#fff', border: 'none' }} onClick={() => handleAssign(r.id)}>认领</Button>}
                    {r.status === 'processing' && <Button size="small" style={{ background: '#10b981', color: '#fff', border: 'none' }} onClick={() => handleResolveOpen(r.id)}>解决</Button>}
                    {r.status === 'resolved' && <Button size="small" style={{ background: '#3b82f6', color: '#fff', border: 'none' }} onClick={() => handleVerify(r.id)}>验证</Button>}
                    {r.status === 'resolved' && <Button size="small" style={{ background: '#ef4444', color: '#fff', border: 'none' }} onClick={() => handleReopen(r.id)}>重开</Button>}
                </Space>
            ),
        },
    ];

    return (
        <div className="fade-in">
            {/* 顶部统计卡片 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
                {[
                    { title: '待处理', value: stats.pending, color: '#f9e2af', icon: <ClockCircleOutlined /> },
                    { title: '处理中', value: stats.processing, color: '#89b4fa', icon: <SyncOutlined /> },
                    { title: '已解决', value: stats.resolved, color: '#a6e3a1', icon: <CheckCircleOutlined /> },
                    { title: '已验证', value: stats.verified, color: '#94e2d5', icon: <SafetyCertificateOutlined /> },
                ].map((s, i) => (
                    <Col key={i} span={6}>
                        <Card style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 12, cursor: 'pointer' }}
                            onClick={() => setStatusFilter(['pending', 'processing', 'resolved', 'verified'][i])}>
                            <Statistic
                                title={<span style={{ color: 'var(--text-secondary)' }}>{s.title}</span>}
                                value={s.value}
                                prefix={<span style={{ color: s.color }}>{s.icon}</span>}
                                valueStyle={{ color: 'var(--text-primary)', fontWeight: 700 }}
                            />
                        </Card>
                    </Col>
                ))}
            </Row>

            {/* 筛选 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                <Select value={statusFilter} onChange={setStatusFilter} allowClear
                    placeholder="筛选状态" style={{ width: 160 }}
                    options={[
                        { value: 'pending', label: '待处理' },
                        { value: 'processing', label: '处理中' },
                        { value: 'resolved', label: '已解决' },
                        { value: 'verified', label: '已验证' },
                    ]}
                />
            </div>

            <Table columns={columns} dataSource={tickets} rowKey="id"
                pagination={{
                    current: page, total, pageSize,
                    showSizeChanger: true,
                    onChange: (p, ps) => { setPage(p); setPageSize(ps); },
                }}
            />

            {/* 工单详情Drawer */}
            <Drawer title="工单详情" open={detailDrawer} onClose={() => setDetailDrawer(false)} width={500}
                extra={
                    currentTicket && (currentTicket.status === 'processing' || currentTicket.status === 'resolved') && (
                        <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openCreateQA}>
                            新建Q&A修正
                        </Button>
                    )
                }
            >
                {currentTicket ? (
                    <div>
                        <Descriptions column={1} bordered size="small">
                            <Descriptions.Item label="标题">{currentTicket.title}</Descriptions.Item>
                            <Descriptions.Item label="状态">{statusTag(currentTicket.status)}</Descriptions.Item>
                            <Descriptions.Item label="来源">{currentTicket.source === 'auto' ? '自动创建' : '手动创建'}</Descriptions.Item>
                            <Descriptions.Item label="处理人">{currentTicket.assigned_to_name || '未分配'}</Descriptions.Item>
                            <Descriptions.Item label="描述">{currentTicket.description || '-'}</Descriptions.Item>
                            <Descriptions.Item label="创建时间">{formatTime(currentTicket.created_at)}</Descriptions.Item>
                            {currentTicket.resolved_at && <Descriptions.Item label="解决时间">{formatTime(currentTicket.resolved_at)}</Descriptions.Item>}
                            {currentTicket.resolution && <Descriptions.Item label="解决备注">{currentTicket.resolution}</Descriptions.Item>}
                            {currentTicket.qa && (
                                <Descriptions.Item label="关联QA">
                                    <Tag color={currentTicket.qa.status === 'active' ? 'green' : currentTicket.qa.status === 'pending_review' ? 'orange' : 'default'}>
                                        {currentTicket.qa.status === 'active' ? '启用' : currentTicket.qa.status === 'pending_review' ? '待审核' : '禁用'}
                                    </Tag>
                                    <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 4 }}>v{currentTicket.qa.version}</span>
                                </Descriptions.Item>
                            )}
                        </Descriptions>

                        {/* 原始提问+AI回答 */}
                        {currentTicket.original_question && (
                            <div style={{ marginTop: 16 }}>
                                <h4>💬 原始对话</h4>
                                <div style={{ padding: 12, background: 'var(--bg-elevated)', borderRadius: 8, marginTop: 8 }}>
                                    <div style={{ fontWeight: 500, marginBottom: 8 }}>
                                        <UserOutlined /> 用户提问:
                                    </div>
                                    <p style={{ color: 'var(--text-secondary)' }}>{currentTicket.original_question}</p>
                                    {currentTicket.original_answer && (
                                        <>
                                            <div style={{ fontWeight: 500, marginTop: 12, marginBottom: 8 }}>
                                                🤖 AI回答:
                                            </div>
                                            <p style={{ color: 'var(--text-secondary)' }}>{currentTicket.original_answer}</p>
                                        </>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* 知识修正提示 */}
                        {(currentTicket.status === 'processing' || currentTicket.status === 'resolved') && (
                            <div style={{
                                marginTop: 16, padding: 12, borderRadius: 8,
                                background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
                            }}>
                                <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>
                                    💡 <strong>知识修正</strong>：如需修正AI回答，可点击右上角「新建Q&A修正」按钮，以Q&A问答对形式录入正确答案。
                                </p>
                            </div>
                        )}

                        {/* 操作记录 */}
                        {currentTicket.logs && currentTicket.logs.length > 0 && (
                            <div style={{ marginTop: 16 }}>
                                <h4>📋 操作记录</h4>
                                <Timeline style={{ marginTop: 12 }}
                                    items={currentTicket.logs.map((log: any) => ({
                                        color: 'blue',
                                        children: (
                                            <div>
                                                <span style={{ fontWeight: 500 }}>{log.action}</span>
                                                <span style={{ color: 'var(--text-muted)', marginLeft: 8, fontSize: 12 }}>{formatTime(log.created_at)}</span>
                                                {log.detail && <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{log.detail}</div>}
                                            </div>
                                        ),
                                    }))}
                                />
                            </div>
                        )}
                    </div>
                ) : <Empty />}
            </Drawer>

            {/* 解决弹窗（含 QA 编辑） */}
            <Modal title="解决工单" open={resolveModalOpen}
                onOk={handleResolveSubmit} onCancel={() => setResolveModalOpen(false)}
                okText="标记已解决" cancelText="取消" width={640}>
                <p style={{ color: 'var(--text-secondary)', marginBottom: 12, fontSize: 13 }}>
                    请输入解决备注（可选）：
                </p>
                <Input.TextArea
                    value={resolveNote}
                    onChange={e => setResolveNote(e.target.value)}
                    placeholder="描述解决方案..."
                    rows={2}
                />
                {/* T-16.2: 关联 QA 编辑区 */}
                {resolveQA && (
                    <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                        <h4 style={{ marginBottom: 8, fontSize: 14 }}>📝 编辑关联 QA（v{resolveQA.version}）</h4>
                        <div style={{ marginBottom: 8 }}>
                            <label style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>问题</label>
                            <Input.TextArea
                                value={resolveQAQuestion}
                                onChange={e => setResolveQAQuestion(e.target.value)}
                                rows={2}
                            />
                        </div>
                        <div>
                            <label style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>答案</label>
                            <Input.TextArea
                                value={resolveQAAnswer}
                                onChange={e => setResolveQAAnswer(e.target.value)}
                                rows={4}
                            />
                        </div>
                        <div style={{ marginTop: 8 }}>
                            <Checkbox checked={approveQA} onChange={e => setApproveQA(e.target.checked)}>
                                <span style={{ fontSize: 13 }}>标记 QA 为已审核（状态→启用）</span>
                            </Checkbox>
                        </div>
                        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, marginBottom: 0 }}>
                            勾选后 QA 状态将自动改为「启用」并同步到 RAGFlow 知识库
                        </p>
                    </div>
                )}
            </Modal>

            {/* 快速创建Q&A弹窗 (知识修正闭环) */}
            <Modal title="📝 新建Q&A修正" open={qaModalOpen}
                onOk={handleQASave} onCancel={() => setQaModalOpen(false)}
                okText="创建Q&A" cancelText="取消" width={640}>
                <p style={{ color: 'var(--text-secondary)', marginBottom: 12, fontSize: 13 }}>
                    以Q&A形式录入正确答案，修正后将直接生效。
                </p>
                <Form form={qaForm} layout="vertical">
                    <Form.Item name="question" label="问题" rules={[{ required: true }]}>
                        <Input.TextArea rows={2} placeholder="用户的原始问题" />
                    </Form.Item>
                    <Form.Item name="answer" label="正确答案" rules={[{ required: true }]}>
                        <Input.TextArea rows={6} placeholder="请输入正确的标准答案" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
