import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { useAuthStore } from '../stores/authStore';
import api from '../services/api';

export default function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const setAuth = useAuthStore(s => s.setAuth);

    const handleLogin = async () => {
        if (!username || !password) {
            message.warning('请输入用户名和密码');
            return;
        }
        setLoading(true);
        try {
            const res = await api.post('/auth/login', { username, password });
            const data = res.data;
            setAuth(data.access_token, {
                id: data.user_id,
                username: data.username,
                displayName: data.display_name,
                role: data.role,
                activeTeamId: data.active_team_id,
                activeTeamName: data.active_team_name,
            });
            message.success(`欢迎回来，${data.display_name}！`);
            navigate('/chat');
        } catch (err: any) {
            message.error(err?.response?.data?.detail || '登录失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-box fade-in">
                <div style={{ textAlign: 'center', marginBottom: 16, fontSize: 48 }}>🤖</div>
                <h1>AI 知识库</h1>
                <p className="sub">智能问答 · 知识管理 · 运营闭环</p>

                <div className="form-group">
                    <label>用户名</label>
                    <input
                        type="text"
                        placeholder="请输入用户名"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleLogin()}
                    />
                </div>
                <div className="form-group">
                    <label>密码</label>
                    <input
                        type="password"
                        placeholder="请输入密码"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleLogin()}
                    />
                </div>
                <button className="login-btn" onClick={handleLogin} disabled={loading}>
                    {loading ? '登录中...' : '登 录'}
                </button>

                <p style={{ textAlign: 'center', marginTop: 24, color: 'var(--text3)', fontSize: 12 }}>
                    默认管理员 admin / admin123
                </p>
            </div>
        </div>
    );
}
