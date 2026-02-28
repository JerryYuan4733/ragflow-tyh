import { useState, useEffect, useCallback } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Dropdown } from 'antd';
import { useAuthStore } from '../stores/authStore';
import { useThemeStore } from '../stores/themeStore';
import TeamSwitcher from '../components/TeamSwitcher';
import api from '../services/api';

const NAV_TABS = [
    { key: '/chat', icon: '💬', label: '智能对话' },
    { key: '/docs', icon: '📁', label: '文档管理' },
    { key: '/qa', icon: '❓', label: 'Q&A管理' },
    { key: '/tickets', icon: '🎫', label: '工单管理' },
    { key: '/stats', icon: '📊', label: '统计分析' },
    { key: '/feedback', icon: '💬', label: '意见反馈' },
    { key: '/teams', icon: '🏢', label: '团队管理' },
    { key: '/settings', icon: '⚙️', label: '系统设置' },
];

// FR-38: 轮播间隔（毫秒）
const NOTICE_CAROUSEL_INTERVAL = 5000;

export default function MainLayout() {
    const navigate = useNavigate();
    const location = useLocation();
    const { user, clearAuth } = useAuthStore();
    const { isDark, toggleTheme } = useThemeStore();

    const activeTab = NAV_TABS.find(t => location.pathname.startsWith(t.key))?.key || '/chat';

    // FR-38: 动态公告栏
    const [notices, setNotices] = useState<any[]>([]);
    const [noticeIdx, setNoticeIdx] = useState(0);

    const loadNotices = useCallback(async () => {
        try {
            const res = await api.get('/announcements/active');
            setNotices(res.data.items || []);
        } catch { setNotices([]); }
    }, []);

    // 挂载时加载公告
    useEffect(() => { loadNotices(); }, [loadNotices]);

    // 多条轮播
    useEffect(() => {
        if (notices.length <= 1) return;
        const timer = setInterval(() => {
            setNoticeIdx(prev => (prev + 1) % notices.length);
        }, NOTICE_CAROUSEL_INTERVAL);
        return () => clearInterval(timer);
    }, [notices.length]);

    return (
        <div id="app">
            {/* ===== FR-38: 动态公告栏 ===== */}
            {notices.length > 0 && (
                <div className="notice-bar">
                    <span className="badge">公告</span>
                    {notices[noticeIdx % notices.length]?.title}：{notices[noticeIdx % notices.length]?.content}
                </div>
            )}

            {/* ===== 顶部导航 ===== */}
            <nav className="topnav">
                <div className="logo">🤖 AI知识库</div>
                <div className="nav-tabs">
                    {NAV_TABS.filter(tab => {
                        // FR-37: 团队管理仅 IT 管理员可见
                        if (tab.key === '/teams') return user?.role === 'it_admin';
                        return true;
                    }).map(tab => (
                        <button
                            key={tab.key}
                            className={`nav-tab ${activeTab === tab.key ? 'active' : ''}`}
                            onClick={() => navigate(tab.key)}
                        >
                            {tab.icon} {tab.label}
                        </button>
                    ))}
                </div>
                <div className="user-info">
                    {/* 团队切换 */}
                    <TeamSwitcher />
                    {/* 主题切换 */}
                    <button
                        className="theme-toggle"
                        onClick={toggleTheme}
                        title="切换深色/浅色模式"
                    >
                        {isDark ? '🌙' : '☀️'}
                    </button>
                    {/* 角色 */}
                    <span style={{ fontSize: 13, color: 'var(--text2)' }}>
                        {user?.role === 'it_admin' ? 'IT管理员' : user?.role === 'kb_admin' ? '知识管理员' : '普通用户'}
                    </span>
                    {/* 头像 */}
                    <Dropdown menu={{
                        items: [{
                            key: 'logout', label: '退出登录',
                            onClick: () => { clearAuth(); navigate('/login'); }
                        }]
                    }}>
                        <div className="avatar">
                            {user?.displayName?.[0] || user?.username?.[0] || 'U'}
                        </div>
                    </Dropdown>
                </div>
            </nav>

            {/* ===== 内容区 ===== */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', width: '100%' }}>
                <Outlet />
            </div>
        </div>
    );
}
