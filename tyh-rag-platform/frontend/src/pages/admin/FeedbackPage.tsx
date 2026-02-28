import { useState, useEffect } from 'react';
import { Table, Tag, Rate, Empty } from 'antd';
import { MessageOutlined } from '@ant-design/icons';
import api from '../../services/api';
import { formatTime } from '../../utils/timeFormat';

export default function FeedbackPage() {
    const [feedbacks, setFeedbacks] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [loading, setLoading] = useState(false);

    const loadFeedbacks = async () => {
        setLoading(true);
        try {
            const res = await api.get('/system-feedback', { params: { page, page_size: pageSize } });
            setFeedbacks(res.data.items || []);
            setTotal(res.data.total || 0);
        } catch { }
        setLoading(false);
    };

    useEffect(() => { loadFeedbacks(); }, [page, pageSize]);

    const categoryColor: Record<string, string> = {
        '功能建议': 'blue',
        'Bug反馈': 'red',
        '体验评价': 'green',
    };

    const columns = [
        {
            title: '分类', dataIndex: 'category', width: 120,
            render: (v: string) => v ? <Tag color={categoryColor[v] || 'default'}>{v}</Tag> : '-',
        },
        {
            title: '评分', dataIndex: 'rating', width: 160,
            render: (v: number) => v > 0 ? <Rate disabled value={v} style={{ fontSize: 14 }} /> : <span style={{ color: 'var(--text-muted)' }}>未评分</span>,
        },
        {
            title: '反馈内容', dataIndex: 'content', ellipsis: true,
            render: (v: string) => <span style={{ color: 'var(--text-primary)' }}>{v}</span>,
        },
        {
            title: '提交人', dataIndex: 'user_id', width: 120,
            render: (v: string) => <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{v}</span>,
        },
        {
            title: '提交时间', dataIndex: 'created_at', width: 180,
            render: (v: string) => formatTime(v),
        },
    ];

    return (
        <div className="fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <MessageOutlined style={{ fontSize: 22, color: 'var(--primary)' }} />
                    <h2 style={{ margin: 0 }}>意见反馈</h2>
                    <Tag color="blue">{total} 条</Tag>
                </div>
            </div>

            {/* 统计卡片 */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
                {['功能建议', 'Bug反馈', '体验评价'].map(cat => {
                    const count = feedbacks.filter(f => f.category === cat).length;
                    const avgRating = feedbacks.filter(f => f.category === cat && f.rating > 0);
                    const avg = avgRating.length > 0
                        ? (avgRating.reduce((s, f) => s + f.rating, 0) / avgRating.length).toFixed(1)
                        : '-';
                    return (
                        <div key={cat} style={{
                            padding: '16px 20px',
                            background: 'var(--bg-card)',
                            borderRadius: 12,
                            border: '1px solid var(--border)',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Tag color={categoryColor[cat]}>{cat}</Tag>
                                <span style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)' }}>{count}</span>
                            </div>
                            <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                                平均评分: {avg}
                            </div>
                        </div>
                    );
                })}
            </div>

            <Table
                columns={columns}
                dataSource={feedbacks}
                rowKey="id"
                loading={loading}
                pagination={{
                    current: page, total, pageSize,
                    showSizeChanger: true,
                    onChange: (p, ps) => { setPage(p); setPageSize(ps); },
                    showTotal: (t) => `共 ${t} 条反馈`,
                }}
                locale={{ emptyText: <Empty description="暂无反馈" /> }}
            />
        </div>
    );
}
