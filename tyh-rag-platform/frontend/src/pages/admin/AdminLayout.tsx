import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Avatar, Dropdown } from 'antd';
import {
    FileTextOutlined, QuestionCircleOutlined,
    AlertOutlined, TeamOutlined, LogoutOutlined, MessageOutlined,
    BarChartOutlined, SettingOutlined, BulbOutlined, BulbFilled,
} from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { useThemeStore } from '../../stores/themeStore';
import NotificationBell from '../../components/NotificationBell';

const { Sider, Content, Header } = Layout;

export default function AdminLayout() {
    const [collapsed, setCollapsed] = useState(false);
    const { isDark: darkMode, toggleTheme } = useThemeStore();
    const navigate = useNavigate();
    const location = useLocation();
    const { user, clearAuth } = useAuthStore();

    const menuItems = [
        { key: '/admin', icon: <BarChartOutlined />, label: '数据概览' },
        { key: '/admin/documents', icon: <FileTextOutlined />, label: '文档管理' },
        { key: '/admin/qa', icon: <QuestionCircleOutlined />, label: 'Q&A管理' },
        { key: '/admin/tickets', icon: <AlertOutlined />, label: '工单管理' },
        ...(user?.role === 'it_admin' ? [
            { key: '/admin/users', icon: <TeamOutlined />, label: '用户管理' },
        ] : []),
        { key: '/admin/settings', icon: <SettingOutlined />, label: '系统设置' },
    ];

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sider
                collapsible
                collapsed={collapsed}
                onCollapse={setCollapsed}
                style={{
                    background: 'var(--bg-card)',
                    borderRight: '1px solid var(--border)',
                }}
            >
                <div style={{
                    padding: '16px', textAlign: 'center',
                    borderBottom: '1px solid var(--border)',
                }}>
                    <span style={{
                        fontSize: collapsed ? 16 : 18, fontWeight: 700,
                        background: 'linear-gradient(135deg, #6366f1, #89b4fa)',
                        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                    }}>
                        {collapsed ? 'KB' : 'AI 知识库管理'}
                    </span>
                </div>
                <Menu
                    mode="inline"
                    selectedKeys={[location.pathname]}
                    items={menuItems}
                    onClick={({ key }) => navigate(key)}
                    style={{ background: 'transparent', border: 'none' }}
                />
            </Sider>
            <Layout>
                <Header style={{
                    background: 'var(--bg-card)',
                    padding: '0 24px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderBottom: '1px solid var(--border)',
                    height: 56,
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <Button
                            type="text"
                            icon={<MessageOutlined />}
                            onClick={() => navigate('/chat')}
                            style={{ color: 'var(--text-secondary)' }}
                        >
                            返回对话
                        </Button>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        {/* 主题切换 (T-031) */}
                        <Button
                            type="text"
                            icon={darkMode ? <BulbFilled style={{ color: '#f9e2af' }} /> : <BulbOutlined />}
                            onClick={toggleTheme}
                            style={{ color: 'var(--text-secondary)' }}
                        />

                        <NotificationBell />
                        <Dropdown menu={{
                            items: [
                                {
                                    key: 'logout', icon: <LogoutOutlined />, label: '退出登录',
                                    onClick: () => { clearAuth(); navigate('/login'); }
                                },
                            ]
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                <Avatar style={{ background: '#6366f1' }} size="small">
                                    {user?.displayName?.[0] || 'A'}
                                </Avatar>
                                <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                                    {user?.displayName}
                                </span>
                            </div>
                        </Dropdown>
                    </div>
                </Header>
                <Content style={{ padding: 24, overflow: 'auto' }}>
                    <Outlet />
                </Content>
            </Layout>
        </Layout>
    );
}
