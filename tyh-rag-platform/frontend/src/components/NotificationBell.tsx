import { useState, useEffect } from 'react';
import { Badge, Dropdown, Button, List, Empty } from 'antd';
import { BellOutlined } from '@ant-design/icons';
import api from '../services/api';
import { formatTime } from '../utils/timeFormat';

interface NotificationItem {
    id: string;
    type: string;
    title: string;
    content?: string;
    ticket_id?: string;
    created_at: string;
}

export default function NotificationBell() {
    const [notifications, setNotifications] = useState<NotificationItem[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);

    const loadNotifications = async () => {
        try {
            const res = await api.get('/notifications');
            setNotifications(res.data.items || []);
            setUnreadCount(res.data.unread_count || 0);
        } catch { }
    };

    useEffect(() => {
        loadNotifications();
        const timer = setInterval(loadNotifications, 60000); // 60秒轮询
        return () => clearInterval(timer);
    }, []);

    const markRead = async (ids: string[]) => {
        try {
            await api.put('/notifications/read', ids);
            loadNotifications();
        } catch { }
    };

    const markAllRead = () => {
        if (notifications.length > 0) {
            markRead(notifications.map(n => n.id));
        }
    };

    const dropdownContent = (
        <div style={{
            width: 360, maxHeight: 400, overflow: 'auto',
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 12, padding: 0, boxShadow: 'var(--shadow)',
        }}>
            <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '12px 16px', borderBottom: '1px solid var(--border)',
            }}>
                <span style={{ fontWeight: 600 }}>通知</span>
                {unreadCount > 0 && (
                    <Button type="link" size="small" onClick={markAllRead}>
                        全部已读
                    </Button>
                )}
            </div>
            {notifications.length > 0 ? (
                <List
                    dataSource={notifications}
                    renderItem={item => (
                        <List.Item
                            onClick={() => markRead([item.id])}
                            style={{
                                padding: '10px 16px', cursor: 'pointer',
                                transition: 'background 0.2s',
                            }}
                        >
                            <div>
                                <div style={{ fontWeight: 500, fontSize: 13 }}>{item.title}</div>
                                {item.content && (
                                    <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 2 }}>
                                        {item.content}
                                    </div>
                                )}
                                <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 4 }}>
                                    {formatTime(item.created_at)}
                                </div>
                            </div>
                        </List.Item>
                    )}
                />
            ) : (
                <Empty description="暂无通知" style={{ padding: 24 }} />
            )}
        </div>
    );

    return (
        <Dropdown
            trigger={['click']}
            dropdownRender={() => dropdownContent}
            placement="bottomRight"
        >
            <Badge count={unreadCount} size="small" offset={[-2, 2]}>
                <Button
                    type="text"
                    icon={<BellOutlined style={{ fontSize: 18 }} />}
                    style={{ color: 'var(--text-secondary)' }}
                />
            </Badge>
        </Dropdown>
    );
}
