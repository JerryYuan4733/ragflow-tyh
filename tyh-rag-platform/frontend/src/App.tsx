import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import LoginPage from './pages/LoginPage';
import MainLayout from './pages/MainLayout';
import ChatPage from './pages/ChatPage';
import DocumentPage from './pages/admin/DocumentPage';
import QAPage from './pages/admin/QAPage';
import TicketPage from './pages/admin/TicketPage';
import StatsPage from './pages/admin/StatsPage';
import SettingsPage from './pages/admin/SettingsPage';
import FeedbackPage from './pages/admin/FeedbackPage';
import TeamPage from './pages/admin/TeamPage';
import HelpPage from './pages/HelpPage';
import { useAuthStore } from './stores/authStore';
import { useThemeStore } from './stores/themeStore';
import './App.css';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore(s => s.token);
  return token ? <>{children}</> : <Navigate to="/login" />;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { token, user, isLoading } = useAuthStore();
  if (!token) return <Navigate to="/login" />;
  // 等待用户信息恢复完成再检查权限
  if (isLoading) return null;
  if (user?.role === 'user') return <Navigate to="/chat" />;
  return <>{children}</>;
}

// FR-37: 仅 IT 管理员可访问的路由守卫
function ITAdminRoute({ children }: { children: React.ReactNode }) {
  const { token, user, isLoading } = useAuthStore();
  if (!token) return <Navigate to="/login" />;
  if (isLoading) return null;
  if (user?.role !== 'it_admin') return <Navigate to="/chat" />;
  return <>{children}</>;
}

export default function App() {
  const isDark = useThemeStore(s => s.isDark);
  const restoreUser = useAuthStore(s => s.restoreUser);

  // 启动时恢复用户信息
  useEffect(() => {
    restoreUser();
  }, [restoreUser]);

  // Set initial data-theme attribute on mount
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#6366f1',
          borderRadius: 10,
          fontFamily: "'Inter', 'Noto Sans SC', system-ui, -apple-system, sans-serif",
          colorBgContainer: isDark ? '#1a1d2e' : '#ffffff',
          colorBgElevated: isDark ? '#22263a' : '#ffffff',
          colorBgLayout: isDark ? '#0d0f1a' : '#f4f6fb',
          colorBorder: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.06)',
          colorBorderSecondary: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)',
          colorText: isDark ? '#e8eaf0' : '#1a1a2e',
          colorTextSecondary: isDark ? '#a0a3b5' : '#52526b',
          colorTextTertiary: isDark ? '#636580' : '#9e9eb8',
          colorBgTextHover: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
          fontSize: 14,
          boxShadow: isDark ? '0 4px 20px rgba(0,0,0,0.3)' : '0 4px 20px rgba(0,0,0,0.08)',
        },
        components: {
          Table: {
            borderRadius: 14,
            headerBg: isDark ? '#141726' : '#f4f6fb',
            rowHoverBg: isDark ? '#22263a' : '#f8f9fd',
          },
          Card: {
            borderRadiusLG: 14,
          },
          Button: {
            borderRadius: 10,
            fontWeight: 600,
          },
          Input: {
            borderRadius: 10,
          },
          Select: {
            borderRadius: 10,
          },
          Modal: {
            borderRadiusLG: 20,
          },
          Tag: {
            borderRadiusSM: 999,
          },
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<PrivateRoute><MainLayout /></PrivateRoute>}>
            <Route index element={<Navigate to="/chat" />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="help" element={<HelpPage />} />
            <Route path="docs" element={<AdminRoute><DocumentPage /></AdminRoute>} />
            <Route path="qa" element={<AdminRoute><QAPage /></AdminRoute>} />
            <Route path="tickets" element={<AdminRoute><TicketPage /></AdminRoute>} />
            <Route path="stats" element={<AdminRoute><StatsPage /></AdminRoute>} />
            <Route path="settings" element={<AdminRoute><SettingsPage /></AdminRoute>} />
            <Route path="feedback" element={<AdminRoute><FeedbackPage /></AdminRoute>} />
            <Route path="teams" element={<ITAdminRoute><TeamPage /></ITAdminRoute>} />
          </Route>
          <Route path="*" element={<Navigate to="/chat" />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

