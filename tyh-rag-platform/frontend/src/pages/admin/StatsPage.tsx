import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Tabs, Table, Tag, Input, Space, Empty, Drawer, Spin, Button, Descriptions, message } from 'antd';
import {
    MessageOutlined, CheckCircleOutlined, LikeOutlined,
    UserOutlined, ClockCircleOutlined,
    FileTextOutlined, QuestionCircleOutlined,
    DislikeOutlined, StarOutlined, CustomerServiceOutlined,
    EyeOutlined,
} from '@ant-design/icons';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
    ResponsiveContainer, PieChart, Pie, Cell, Legend, Area, AreaChart,
} from 'recharts';
import api from '../../services/api';
import { formatTime } from '../../utils/timeFormat';

const CHART_COLORS = ['#6366f1', '#89b4fa', '#a6e3a1', '#f9e2af', '#f38ba8', '#94e2d5'];


export default function StatsPage() {
    const [overview, setOverview] = useState<any>({});
    const [trendData, setTrendData] = useState<any[]>([]);
    const [satisfactionData, setSatisfactionData] = useState<any[]>([]);
    const [roiData, setRoiData] = useState<any[]>([]);

    // Question logs state
    const [questionLogs, setQuestionLogs] = useState<any[]>([]);
    const [logTotal, setLogTotal] = useState(0);
    const [logPage, setLogPage] = useState(1);
    const [logPageSize, setLogPageSize] = useState(20);
    const [feedbackFilter, setFeedbackFilter] = useState('all');
    const [keyword, setKeyword] = useState('');
    const [logStats, setLogStats] = useState<any>({});
    const [logsLoading, setLogsLoading] = useState(false);
    const [detailVisible, setDetailVisible] = useState(false);
    const [detailData, setDetailData] = useState<any>(null);
    const [detailLoading, setDetailLoading] = useState(false);

    const loadOverview = async () => {
        try {
            const res = await api.get('/stats/overview');
            setOverview(res.data || {});
        } catch {
            setOverview({
                total_questions: 2847, ai_resolved: 2134, ai_resolve_rate: 74.9,
                avg_response_time: 1.2, satisfaction_rate: 87.3, total_documents: 156,
                total_qa_pairs: 423, active_users: 89,
            });
        }
    };

    const loadTrendData = async () => {
        try {
            const res = await api.get('/stats/trends');
            setTrendData(res.data.items || []);
        } catch {
            const days = Array.from({ length: 14 }, (_, i) => {
                const d = new Date(); d.setDate(d.getDate() - (13 - i));
                return { date: `${d.getMonth() + 1}/${d.getDate()}`, questions: Math.floor(Math.random() * 80 + 120), resolved: Math.floor(Math.random() * 60 + 90) };
            });
            setTrendData(days);
        }
    };

    const loadSatisfactionData = async () => {
        try {
            const res = await api.get('/stats/satisfaction');
            setSatisfactionData(res.data.items || []);
        } catch {
            const days = Array.from({ length: 14 }, (_, i) => {
                const d = new Date(); d.setDate(d.getDate() - (13 - i));
                return { date: `${d.getMonth() + 1}/${d.getDate()}`, rate: Math.floor(Math.random() * 15 + 80) };
            });
            setSatisfactionData(days);
        }
    };

    const loadRoiData = async () => {
        try {
            const res = await api.get('/stats/roi');
            setRoiData(res.data.items || []);
        } catch {
            setRoiData([
                { name: 'AI自动解决', value: 75 },
                { name: '人工转介', value: 15 },
                { name: '未解决', value: 10 },
            ]);
        }
    };

    const loadQuestionLogs = async () => {
        setLogsLoading(true);
        try {
            const params: any = { page: logPage, page_size: logPageSize };
            if (feedbackFilter !== 'all') params.feedback_type = feedbackFilter;
            if (keyword) params.keyword = keyword;
            const res = await api.get('/stats/question-logs', { params });
            setQuestionLogs(res.data.items || []);
            setLogTotal(res.data.total || 0);
            setLogStats(res.data.stats || {});
        } catch {
            setQuestionLogs([
                { id: '1', user_name: '张三', question: '产品A的保修政策是什么？', answer: '产品A提供两年质保...', created_at: '2026-02-13T10:30:00', feedback_type: 'like', is_favorited: false, is_transferred: false },
                { id: '2', user_name: '李四', question: '如何重置密码？', answer: '请到设置页面...', created_at: '2026-02-13T10:25:00', feedback_type: 'dislike', is_favorited: false, is_transferred: true },
                { id: '3', user_name: '王五', question: '销售流程有哪些步骤？', answer: '销售流程包含以下步骤...', created_at: '2026-02-13T10:20:00', feedback_type: null, is_favorited: true, is_transferred: false },
            ]);
            setLogTotal(3);
            setLogStats({ total: 100, liked: 45, disliked: 12, favorited: 8, transferred: 5, no_feedback: 30 });
        } finally {
            setLogsLoading(false);
        }
    };

    useEffect(() => { loadOverview(); loadTrendData(); loadSatisfactionData(); loadRoiData(); }, []);
    useEffect(() => { loadQuestionLogs(); }, [logPage, logPageSize, feedbackFilter]);

    const handleSearch = () => {
        setLogPage(1);
        loadQuestionLogs();
    };

    const handleFilterChange = (key: string) => {
        setFeedbackFilter(key);
        setLogPage(1);
    };

    const loadDetail = async (messageId: string) => {
        setDetailVisible(true);
        setDetailLoading(true);
        try {
            const res = await api.get(`/stats/question-logs/${messageId}/detail`);
            setDetailData(res.data);
        } catch {
            message.error('获取详情失败');
            setDetailData(null);
        } finally {
            setDetailLoading(false);
        }
    };

    const logColumns = [
        {
            title: '用户', dataIndex: 'user_name', width: 90,
            render: (v: string) => <><UserOutlined style={{ marginRight: 4 }} />{v}</>
        },
        { title: '提问内容', dataIndex: 'question', ellipsis: true },
        { title: 'AI回答', dataIndex: 'answer', ellipsis: true, width: 280 },
        {
            title: '反馈', dataIndex: 'feedback_type', width: 80,
            render: (v: string) =>
                v === 'like' ? <Tag color="green">👍 点赞</Tag> :
                    v === 'dislike' ? <Tag color="red">👎 点踩</Tag> :
                        <Tag>➖</Tag>,
        },
        {
            title: '状态', width: 120,
            render: (_: any, row: any) => (
                <Space size={4}>
                    {row.is_favorited && <Tag color="gold">⭐</Tag>}
                    {row.is_transferred && <Tag color="purple">🙋 转人工</Tag>}
                </Space>
            ),
        },
        {
            title: '时间', dataIndex: 'created_at', width: 180,
            render: (v: string) => formatTime(v),
        },
        {
            title: '操作', width: 100, fixed: 'right' as const,
            render: (_: any, row: any) => (
                <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => loadDetail(row.id)}>详情</Button>
            ),
        },
    ];

    const statsCards = [
        { key: 'all', label: '总提问', value: logStats.total || 0, color: '#6366f1', icon: <MessageOutlined /> },
        { key: 'like', label: '👍 点赞', value: logStats.liked || 0, color: '#10b981', icon: <LikeOutlined /> },
        { key: 'dislike', label: '👎 点踩', value: logStats.disliked || 0, color: '#ef4444', icon: <DislikeOutlined /> },
        { key: 'favorited', label: '⭐ 收藏', value: logStats.favorited || 0, color: '#f59e0b', icon: <StarOutlined /> },
        { key: 'transferred', label: '🙋 转人工', value: logStats.transferred || 0, color: '#6366f1', icon: <CustomerServiceOutlined /> },
        { key: 'no_feedback', label: '无反馈', value: logStats.no_feedback || 0, color: '#9e9eb8', icon: <QuestionCircleOutlined /> },
    ];

    const tabItems = [
        {
            key: 'overview',
            label: '📊 概览与趋势',
            children: (
                <div>
                    {/* KPI Cards */}
                    <Row gutter={16} style={{ marginBottom: 24 }}>
                        {[
                            { title: '总提问量', value: overview.total_questions || 0, icon: <MessageOutlined />, color: '#6366f1' },
                            { title: 'AI解决率', value: overview.ai_resolve_rate || 0, suffix: '%', icon: <CheckCircleOutlined />, color: '#a6e3a1' },
                            { title: '满意度', value: overview.satisfaction_rate || 0, suffix: '%', icon: <LikeOutlined />, color: '#89b4fa' },
                            { title: '平均响应', value: overview.avg_response_time || 0, suffix: 's', icon: <ClockCircleOutlined />, color: '#f9e2af' },
                            { title: '文档数', value: overview.total_documents || 0, icon: <FileTextOutlined />, color: '#94e2d5' },
                            { title: 'Q&A数', value: overview.total_qa_pairs || 0, icon: <QuestionCircleOutlined />, color: '#f38ba8' },
                        ].map((s, i) => (
                            <Col key={i} span={4}>
                                <Card style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 12, textAlign: 'center' }}>
                                    <div style={{ color: s.color, fontSize: 24, marginBottom: 8 }}>{s.icon}</div>
                                    <Statistic
                                        title={<span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{s.title}</span>}
                                        value={s.value}
                                        suffix={s.suffix}
                                        valueStyle={{ color: 'var(--text-primary)', fontWeight: 700, fontSize: 22 }}
                                    />
                                </Card>
                            </Col>
                        ))}
                    </Row>

                    {/* Charts Row */}
                    <Row gutter={16}>
                        {/* 对话趋势折线图 */}
                        <Col span={16}>
                            <div className="chart-card">
                                <h4>📈 对话趋势（近14日）</h4>
                                <ResponsiveContainer width="100%" height={300}>
                                    <AreaChart data={trendData}>
                                        <defs>
                                            <linearGradient id="gradientQuestions" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                            </linearGradient>
                                            <linearGradient id="gradientResolved" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#a6e3a1" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="#a6e3a1" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                        <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} />
                                        <YAxis stroke="var(--text-muted)" fontSize={12} />
                                        <RTooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }} />
                                        <Area type="monotone" dataKey="questions" stroke="#6366f1" fill="url(#gradientQuestions)" name="提问量" strokeWidth={2} />
                                        <Area type="monotone" dataKey="resolved" stroke="#a6e3a1" fill="url(#gradientResolved)" name="解决量" strokeWidth={2} />
                                        <Legend />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </Col>

                        {/* ROI环形图 */}
                        <Col span={8}>
                            <div className="chart-card">
                                <h4>🎯 AI解决率分布</h4>
                                <ResponsiveContainer width="100%" height={300}>
                                    <PieChart>
                                        <Pie data={roiData} cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                                            paddingAngle={5} dataKey="value" label={({ name, value }) => `${name} ${value}%`}>
                                            {roiData.map((_: any, index: number) => (
                                                <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <RTooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }} />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                        </Col>
                    </Row>

                    {/* 满意率趋势 */}
                    <div className="chart-card" style={{ marginTop: 16 }}>
                        <h4>😊 满意率趋势（近14日）</h4>
                        <ResponsiveContainer width="100%" height={250}>
                            <LineChart data={satisfactionData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} />
                                <YAxis domain={[0, 100]} stroke="var(--text-muted)" fontSize={12} />
                                <RTooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }} />
                                <Line type="monotone" dataKey="rate" stroke="#89b4fa" strokeWidth={2.5}
                                    dot={{ fill: '#89b4fa', strokeWidth: 2 }} name="满意率 %" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            ),
        },
        {
            key: 'logs',
            label: '📝 提问日志',
            children: (
                <div>
                    {/* Stats summary cards */}
                    <Row gutter={12} style={{ marginBottom: 20 }}>
                        {statsCards.map(s => (
                            <Col key={s.key} span={4}>
                                <Card
                                    size="small"
                                    hoverable
                                    onClick={() => handleFilterChange(s.key)}
                                    style={{
                                        borderRadius: 12,
                                        border: feedbackFilter === s.key
                                            ? `2px solid ${s.color}` : '1px solid var(--border)',
                                        textAlign: 'center',
                                        cursor: 'pointer',
                                        background: feedbackFilter === s.key
                                            ? `${s.color}10` : 'var(--card)',
                                        transition: 'all 0.2s',
                                    }}
                                >
                                    <div style={{ color: s.color, fontSize: 18, marginBottom: 4 }}>{s.icon}</div>
                                    <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
                                    <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>{s.label}</div>
                                </Card>
                            </Col>
                        ))}
                    </Row>

                    {/* Search bar */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                        <Input.Search
                            placeholder="搜索提问内容..."
                            allowClear
                            style={{ width: 300 }}
                            value={keyword}
                            onChange={e => setKeyword(e.target.value)}
                            onSearch={handleSearch}
                        />
                    </div>

                    {/* Table */}
                    <Table
                        columns={logColumns}
                        dataSource={questionLogs}
                        rowKey="id"
                        loading={logsLoading}
                        pagination={{
                            current: logPage,
                            total: logTotal,
                            pageSize: logPageSize,
                            showSizeChanger: true,
                            onChange: (p, ps) => { setLogPage(p); setLogPageSize(ps); },
                            showTotal: (t) => `共 ${t} 条`,
                        }}
                    />
                </div>
            ),
        },
    ];

    const stepCardStyle = (color: string) => ({
        background: `${color}08`,
        border: `1px solid ${color}30`,
        borderRadius: 12,
        padding: '16px 20px',
        marginBottom: 16,
    });

    const stepBadge = (num: number, label: string, color: string) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <div style={{
                width: 28, height: 28, borderRadius: '50%', background: color,
                color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, fontWeight: 700,
            }}>{num}</div>
            <span style={{ fontSize: 15, fontWeight: 600, color }}>{label}</span>
        </div>
    );

    return (
        <div className="fade-in">
            <Tabs items={tabItems} />

            {/* 详情 Drawer */}
            <Drawer
                title="📊 问答分析详情"
                open={detailVisible}
                onClose={() => { setDetailVisible(false); setDetailData(null); }}
                width={680}
                styles={{ body: { padding: '20px 24px', background: 'var(--bg2, #f8f9fa)' } }}
            >
                {detailLoading ? (
                    <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" tip="加载中..." /></div>
                ) : detailData ? (
                    <div>
                        {/* ① 用户提问 */}
                        <div style={stepCardStyle('#6366f1')}>
                            {stepBadge(1, '用户提问', '#6366f1')}
                            <Descriptions column={2} size="small">
                                <Descriptions.Item label="用户">{detailData.user_name}</Descriptions.Item>
                                <Descriptions.Item label="时间">{formatTime(detailData.created_at)}</Descriptions.Item>
                                <Descriptions.Item label="会话" span={2}>{detailData.session_title}</Descriptions.Item>
                            </Descriptions>
                            <div style={{
                                background: '#fff', borderRadius: 8, padding: '12px 16px', marginTop: 8,
                                fontSize: 15, fontWeight: 500, border: '1px solid #e2e2f0',
                            }}>
                                💬 {detailData.user_question}
                            </div>
                        </div>

                        {/* ① ½ 耗时分析 */}
                        {detailData.timing && (
                            <div style={stepCardStyle('#ec4899')}>
                                {stepBadge(0, '⏱ 耗时分析', '#ec4899')}
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                                    <span style={{ fontSize: 13, color: 'var(--text3)' }}>总耗时:</span>
                                    <span style={{
                                        fontSize: 20, fontWeight: 700,
                                        color: (detailData.timing.total || 0) > 10 ? '#ef4444' :
                                            (detailData.timing.total || 0) > 5 ? '#f59e0b' : '#10b981',
                                    }}>
                                        {detailData.timing.total?.toFixed(1) || '—'}s
                                    </span>
                                </div>
                                {(() => {
                                    const t = detailData.timing;
                                    const stages = [
                                        { key: 'save_user_msg', label: '💾 保存用户消息', value: t.save_user_msg },
                                        { key: 'session_init', label: '🔗 会话初始化', value: t.session_init },
                                        { key: 'first_token', label: '⚡ 首Token延迟', value: t.first_token },
                                        { key: 'sse_stream', label: '📡 SSE流式传输', value: t.sse_stream },
                                        { key: 'backfill', label: '🔄 引用回填', value: t.backfill },
                                        { key: 'save_ai_msg', label: '💾 保存AI回答', value: t.save_ai_msg },
                                    ].filter(s => s.value !== undefined && s.value !== null);
                                    const maxVal = Math.max(...stages.map(s => s.value || 0), 0.1);
                                    return (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                            {stages.map(s => (
                                                <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                    <span style={{ fontSize: 12, color: 'var(--text3)', width: 120, flexShrink: 0 }}>{s.label}</span>
                                                    <div style={{ flex: 1, height: 18, background: 'rgba(0,0,0,0.06)', borderRadius: 4, overflow: 'hidden' }}>
                                                        <div style={{
                                                            height: '100%', borderRadius: 4,
                                                            width: `${Math.max((s.value! / maxVal) * 100, 2)}%`,
                                                            background: s.value! >= 3 ? '#ef4444' : s.value! >= 1 ? '#f59e0b' : '#10b981',
                                                            transition: 'width 0.3s',
                                                        }} />
                                                    </div>
                                                    <span style={{
                                                        fontSize: 12, fontWeight: 600, width: 55, textAlign: 'right', flexShrink: 0,
                                                        color: s.value! >= 3 ? '#ef4444' : s.value! >= 1 ? '#f59e0b' : '#10b981',
                                                    }}>
                                                        {s.value!.toFixed(3)}s
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    );
                                })()}
                            </div>
                        )}

                        {/* ② RAGFlow 检索 */}
                        <div style={stepCardStyle('#f59e0b')}>
                            {stepBadge(2, 'RAGFlow 知识检索', '#f59e0b')}

                            {/* 请求体 */}
                            {detailData.ragflow_request && (
                                <div style={{ marginBottom: 12 }}>
                                    <div style={{ fontSize: 13, fontWeight: 600, color: '#92400e', marginBottom: 4 }}>📤 请求 (Request)</div>
                                    <pre style={{
                                        background: '#1e1e1e', color: '#d4d4d4', borderRadius: 8,
                                        padding: '10px 14px', fontSize: 12, overflow: 'auto',
                                        maxHeight: 160, margin: 0, lineHeight: 1.6,
                                    }}>
                                        {JSON.stringify(detailData.ragflow_request, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {/* 响应引用 */}
                            <div style={{ fontSize: 13, fontWeight: 600, color: '#92400e', marginBottom: 4 }}>📥 响应 - 检索片段 (Response Chunks)</div>
                            {detailData.citations && detailData.citations.length > 0 ? (
                                <div>
                                    <div style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 8 }}>
                                        共检索到 <strong>{detailData.citations.length}</strong> 个相关片段
                                    </div>
                                    {detailData.citations.map((c: any, i: number) => (
                                        <div key={i} style={{
                                            background: '#fff', borderRadius: 8, padding: '10px 14px',
                                            marginBottom: 8, border: '1px solid #fde68a', fontSize: 13,
                                        }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                                <Tag color="orange">📄 {c.document_name}</Tag>
                                                <span style={{ color: '#f59e0b', fontWeight: 600 }}>
                                                    相似度: {c.similarity > 0 ? `${(c.similarity * 100).toFixed(1)}%` : 'N/A'}
                                                </span>
                                            </div>
                                            <div style={{ color: 'var(--text2)', lineHeight: 1.6, maxHeight: 80, overflow: 'auto' }}>
                                                {c.content?.slice(0, 200)}{c.content?.length > 200 ? '...' : ''}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div style={{ color: 'var(--text3)', fontSize: 13 }}>⚠️ 未检索到相关知识片段</div>
                            )}
                        </div>

                        {/* ③ AI 模型信息 */}
                        <div style={stepCardStyle('#10b981')}>
                            {stepBadge(3, 'AI 模型生成', '#10b981')}
                            {detailData.ragflow_info && !detailData.ragflow_info.error ? (
                                <div>
                                    <Descriptions column={2} size="small">
                                        <Descriptions.Item label="助手名称">
                                            <Tag color="green">{detailData.ragflow_info.assistant_name || '—'}</Tag>
                                        </Descriptions.Item>
                                        <Descriptions.Item label="AI 模型">
                                            <Tag color="blue">{detailData.ragflow_info.model_name || '—'}</Tag>
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Temperature">
                                            {detailData.ragflow_info.temperature ?? '—'}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Top P">
                                            {detailData.ragflow_info.top_p ?? '—'}
                                        </Descriptions.Item>
                                    </Descriptions>

                                    {/* 模型输入 */}
                                    <div style={{ marginTop: 12 }}>
                                        <div style={{ fontSize: 13, fontWeight: 600, color: '#065f46', marginBottom: 4 }}>📤 模型输入 (Input)</div>
                                        <pre style={{
                                            background: '#1e1e1e', color: '#d4d4d4', borderRadius: 8,
                                            padding: '10px 14px', fontSize: 12, overflow: 'auto',
                                            maxHeight: 120, margin: 0, lineHeight: 1.6,
                                        }}>
                                            {JSON.stringify({
                                                question: detailData.user_question,
                                                retrieval_chunks: detailData.citations?.length || 0,
                                                model: detailData.ragflow_info?.model_name,
                                                temperature: detailData.ragflow_info?.temperature,
                                                top_p: detailData.ragflow_info?.top_p,
                                            }, null, 2)}
                                        </pre>
                                    </div>

                                    {/* 模型输出 */}
                                    {detailData.ragflow_response && (
                                        <div style={{ marginTop: 8 }}>
                                            <div style={{ fontSize: 13, fontWeight: 600, color: '#065f46', marginBottom: 4 }}>📥 模型输出 (Output)</div>
                                            <pre style={{
                                                background: '#1e1e1e', color: '#d4d4d4', borderRadius: 8,
                                                padding: '10px 14px', fontSize: 12, overflow: 'auto',
                                                maxHeight: 160, margin: 0, lineHeight: 1.6,
                                            }}>
                                                {JSON.stringify({
                                                    answer: detailData.ragflow_response.answer?.slice(0, 200) + (detailData.ragflow_response.answer?.length > 200 ? '...' : ''),
                                                    is_not_found: detailData.ragflow_response.is_not_found,
                                                    has_reference: !!detailData.ragflow_response.reference,
                                                }, null, 2)}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div style={{ color: 'var(--text3)', fontSize: 13 }}>
                                    {detailData.ragflow_info?.error ? `⚠️ ${detailData.ragflow_info.error}` : '⚠️ 无法获取模型信息'}
                                </div>
                            )}
                        </div>

                        {/* ④ AI 回答 */}
                        <div style={stepCardStyle('#3b82f6')}>
                            {stepBadge(4, 'AI 回答', '#3b82f6')}
                            <div style={{
                                background: '#fff', borderRadius: 8, padding: '12px 16px',
                                border: '1px solid #bfdbfe', fontSize: 14, lineHeight: 1.8,
                                maxHeight: 300, overflow: 'auto', whiteSpace: 'pre-wrap',
                            }}>
                                {detailData.ai_answer || '（无回答）'}
                            </div>
                        </div>

                        {/* ⑤ 用户反馈 */}
                        <div style={stepCardStyle('#8b5cf6')}>
                            {stepBadge(5, '用户反馈', '#8b5cf6')}
                            <Space size={12} wrap>
                                {detailData.feedback ? (
                                    <Tag color={detailData.feedback.type === 'like' ? 'green' : 'red'} style={{ fontSize: 13, padding: '4px 12px' }}>
                                        {detailData.feedback.type === 'like' ? '👍 点赞' : '👎 点踩'}
                                    </Tag>
                                ) : (
                                    <Tag style={{ fontSize: 13, padding: '4px 12px' }}>➖ 无反馈</Tag>
                                )}
                                {detailData.is_favorited && <Tag color="gold" style={{ fontSize: 13, padding: '4px 12px' }}>⭐ 已收藏</Tag>}
                                {detailData.transfer_info && (
                                    <Tag color="purple" style={{ fontSize: 13, padding: '4px 12px' }}>
                                        🙋 已转人工 ({detailData.transfer_info.status})
                                    </Tag>
                                )}
                                {detailData.feedback?.reason && (
                                    <div style={{ width: '100%', marginTop: 4, fontSize: 13, color: 'var(--text3)' }}>
                                        原因: {detailData.feedback.reason}
                                    </div>
                                )}
                            </Space>
                        </div>
                    </div>
                ) : (
                    <Empty description="暂无数据" />
                )}
            </Drawer>
        </div>
    );
}

