import { useState, useEffect } from 'react';
import dayjs from 'dayjs';
import { Table, Form, Input, InputNumber, Slider, Button, Tag, Select, Switch, Modal, Space, Spin, Popconfirm, DatePicker, Collapse, message } from 'antd';
import api from '../../services/api';
import { useAuthStore } from '../../stores/authStore';
import { formatTime } from '../../utils/timeFormat';

const SETTING_MENUS = [
    { key: 'users', icon: '👥', label: '用户管理' },
    { key: 'roles', icon: '🔐', label: '角色权限' },
    { key: 'ragflow', icon: '🔌', label: 'RAGFlow连接' },
    { key: 'kb', icon: '📚', label: '知识库配置' },
    { key: 'parse', icon: '📄', label: '文档解析' },
    { key: 'chat', icon: '🤖', label: '对话配置' },
    { key: 'audit', icon: '📋', label: '审计日志' },
    { key: 'announcements', icon: '📢', label: '公告管理' },
    { key: 'help', icon: '❓', label: '帮助中心' },
];

export default function SettingsPage() {
    const user = useAuthStore(s => s.user);
    const isIT = user?.role === 'it_admin';
    const [activeMenu, setActiveMenu] = useState('users');

    const renderContent = () => {
        switch (activeMenu) {
            case 'users': return <UserManagement />;
            case 'roles': return <RolesPermissions />;
            case 'ragflow': return <RAGFlowConnection isIT={isIT} />;
            case 'kb': return <KnowledgeBaseConfig isIT={isIT} />;
            case 'parse': return <ParseConfig isIT={isIT} />;
            case 'chat': return <ChatConfig isIT={isIT} />;
            case 'audit': return <AuditLogs />;
            case 'announcements': return <Announcements />;
            case 'help': return <HelpCenter />;
            default: return null;
        }
    };

    return (
        <div className="admin-layout" style={{ flex: 1 }}>
            <div className="admin-sidebar">
                {SETTING_MENUS.filter(m => {
                    // FR-38: 公告管理仅 IT 管理员可见
                    if (m.key === 'announcements') return isIT;
                    return true;
                }).map(m => (
                    <div
                        key={m.key}
                        className={`menu-item ${activeMenu === m.key ? 'active' : ''}`}
                        onClick={() => setActiveMenu(m.key)}
                    >
                        {m.icon} {m.label}
                    </div>
                ))}
            </div>
            <div className="admin-content">
                {renderContent()}
            </div>
        </div>
    );
}

// ========== 用户管理 ==========
function UserManagement() {
    const [users, setUsers] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [loading, setLoading] = useState(false);
    const [modalOpen, setModalOpen] = useState(false);
    const [editUser, setEditUser] = useState<any>(null);
    const [form] = Form.useForm();
    const [teams, setTeams] = useState<{ value: string; label: string }[]>([]);
    const [resetPwdOpen, setResetPwdOpen] = useState(false);
    const [resetUserId, setResetUserId] = useState('');
    const [newPassword, setNewPassword] = useState('');

    const loadUsers = async () => {
        setLoading(true);
        try {
            const res = await api.get('/users', { params: { page, page_size: pageSize } });
            setUsers(res.data.items || []);
            setTotal(res.data.total || 0);
        } catch { } finally { setLoading(false); }
    };

    const loadTeams = async () => {
        try {
            const res = await api.get('/teams');
            const items = res.data.items || res.data || [];
            setTeams(items.map((t: any) => ({ value: t.id, label: t.name || t.id })));
        } catch {
            setTeams([
                { value: 'team-default', label: '默认团队' },
                { value: 'team-sales', label: '销售团队' },
                { value: 'team-support', label: '客服团队' },
                { value: 'team-tech', label: '技术团队' },
            ]);
        }
    };

    useEffect(() => { loadUsers(); loadTeams(); }, [page, pageSize]);

    const handleSave = async () => {
        const values = await form.validateFields();
        try {
            if (editUser) {
                await api.put(`/users/${editUser.id}`, values);
                message.success('更新成功');
            } else {
                await api.post('/users', values);
                message.success('创建成功');
            }
            setModalOpen(false); form.resetFields(); setEditUser(null); loadUsers();
        } catch (e: any) { message.error(e?.response?.data?.detail || '操作失败'); }
    };

    const handleToggle = async (id: string) => {
        await api.put(`/users/${id}/toggle`);
        message.success('操作成功');
        loadUsers();
    };

    const handleResetPassword = async () => {
        if (!newPassword.trim()) { message.error('请输入新密码'); return; }
        try {
            await api.put(`/users/${resetUserId}/reset-password`, { password: newPassword });
            message.success('密码已重置');
            setResetPwdOpen(false); setNewPassword('');
        } catch (e: any) { message.error(e?.response?.data?.detail || '重置失败'); }
    };

    const ROLE_MAP: Record<string, { color: string; text: string }> = {
        user: { color: 'default', text: '普通用户' },
        kb_admin: { color: 'blue', text: '知识库管理员' },
        it_admin: { color: 'purple', text: 'IT管理员' },
    };

    return (
        <div className="fade-in">
            <div className="admin-header">
                <h2>用户管理</h2>
                <button className="btn btn-primary" onClick={() => { setEditUser(null); form.resetFields(); setModalOpen(true); }}>+ 新增用户</button>
            </div>
            <Table
                columns={[
                    { title: '用户名', dataIndex: 'username' },
                    { title: '姓名', dataIndex: 'display_name' },
                    { title: '角色', dataIndex: 'role', render: (r: string) => <Tag color={ROLE_MAP[r]?.color}>{ROLE_MAP[r]?.text}</Tag> },
                    { title: '活跃团队', dataIndex: 'active_team_name' },
                    { title: '状态', dataIndex: 'is_active', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '在线' : '离线'}</Tag> },
                    { title: '最后登录', dataIndex: 'last_login_at', width: 180 },
                    {
                        title: '操作', width: 200,
                        render: (_: any, r: any) => (
                            <Space>
                                <Button type="link" size="small" onClick={() => { setEditUser(r); form.setFieldsValue(r); setModalOpen(true); }}>编辑</Button>
                                <Button type="link" size="small" onClick={() => { setResetUserId(r.id); setNewPassword(''); setResetPwdOpen(true); }}>重置密码</Button>
                                <Button type="link" size="small" danger={r.is_active} onClick={() => handleToggle(r.id)}>{r.is_active ? '禁用' : '启用'}</Button>
                            </Space>
                        ),
                    },
                ]}
                dataSource={users} rowKey="id" loading={loading}
                pagination={{
                    current: page, total, pageSize,
                    showSizeChanger: true,
                    onChange: (p: number, ps: number) => { setPage(p); setPageSize(ps); },
                }}
            />
            <Modal title={editUser ? '编辑用户' : '新增用户'} open={modalOpen}
                onOk={handleSave} onCancel={() => { setModalOpen(false); setEditUser(null); }}>
                <Form form={form} layout="vertical">
                    <Form.Item name="username" label="用户名" rules={[{ required: !editUser }]}><Input disabled={!!editUser} /></Form.Item>
                    {!editUser && <Form.Item name="password" label="密码" rules={[{ required: true }]}><Input.Password /></Form.Item>}
                    <Form.Item name="display_name" label="姓名" rules={[{ required: true }]}><Input /></Form.Item>
                    <Form.Item name="role" label="角色" rules={[{ required: true }]}>
                        <Select options={[
                            { value: 'user', label: '普通用户' },
                            { value: 'kb_admin', label: '知识库管理员' },
                            { value: 'it_admin', label: 'IT管理员' },
                        ]} />
                    </Form.Item>
                    <Form.Item name="team_ids" label="所属团队"><Select mode="multiple" placeholder="选择团队（可多选）" options={teams} showSearch /></Form.Item>
                    <Form.Item name="job_number" label="工号"><Input /></Form.Item>
                </Form>
            </Modal>
            <Modal title="重置密码" open={resetPwdOpen}
                onOk={handleResetPassword} onCancel={() => { setResetPwdOpen(false); setNewPassword(''); }}>
                <p style={{ color: 'var(--text2)', marginBottom: 12 }}>请输入新密码（至少6个字符）：</p>
                <Input.Password value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="新密码" />
            </Modal>
        </div>
    );
}

// ========== 角色权限 ==========
function RolesPermissions() {
    return (
        <div className="fade-in">
            <div className="admin-header"><h2>角色权限</h2></div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                {[
                    { role: 'IT管理员', desc: '拥有所有系统权限，包括用户管理、系统设置、效果测试', perms: ['全部权限'] },
                    { role: '知识库管理员', desc: '管理文档、Q&A、工单及统计分析', perms: ['文档管理', 'Q&A管理', '工单管理', '统计分析'] },
                    { role: '普通用户', desc: '使用智能对话进行知识查询', perms: ['智能对话', '提交工单'] },
                ].map(r => (
                    <div key={r.role} style={{
                        background: 'var(--card)', border: '1px solid var(--border)',
                        borderRadius: 'var(--radius)', padding: 20,
                    }}>
                        <h3 style={{ marginBottom: 8 }}>{r.role}</h3>
                        <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 12 }}>{r.desc}</p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {r.perms.map(p => <Tag key={p} color="blue">{p}</Tag>)}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ========== RAGFlow 连接配置 ==========
function RAGFlowConnection({ isIT }: { isIT: boolean }) {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [data, setData] = useState<any>(null);
    const [baseUrl, setBaseUrl] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [showKey, setShowKey] = useState(false);

    const loadConfig = async () => {
        setLoading(true);
        try {
            const res = await api.get('/settings/ragflow-connection');
            setData(res.data);
            setBaseUrl(res.data.ragflow_base_url || '');
            setApiKey(res.data.ragflow_api_key_full || '');
        } catch { } finally { setLoading(false); }
    };

    useEffect(() => { loadConfig(); }, []);

    const handleTest = async () => {
        setTesting(true); setTestResult(null);
        try {
            const res = await api.post('/settings/ragflow-connection/test', {
                ragflow_base_url: baseUrl, ragflow_api_key: apiKey,
            });
            setTestResult(res.data);
        } catch (e: any) {
            setTestResult({ success: false, message: e?.response?.data?.detail || '测试失败' });
        } finally { setTesting(false); }
    };

    const handleSave = async () => {
        if (!baseUrl.trim() || !apiKey.trim()) { message.warning('API地址和KEY不能为空'); return; }
        setSaving(true);
        try {
            await api.put('/settings/ragflow-connection', {
                ragflow_base_url: baseUrl, ragflow_api_key: apiKey,
            });
            message.success('RAGFlow 连接配置已保存，已立即生效');
            setTestResult(null);
            loadConfig();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '保存失败');
        } finally { setSaving(false); }
    };

    if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;

    return (
        <div className="fade-in">
            <div className="admin-header"><h2>🔌 RAGFlow 连接配置</h2></div>

            {/* 当前连接状态 */}
            <div style={{
                background: 'linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%)',
                borderRadius: 12, padding: 24, marginBottom: 24, color: '#fff',
            }}>
                <div style={{ fontSize: 14, opacity: 0.85, marginBottom: 12 }}>📡 当前连接状态</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    <div>
                        <div style={{ fontSize: 12, opacity: 0.7 }}>API 地址</div>
                        <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'monospace', wordBreak: 'break-all' }}>
                            {data?.current_client_url || '—'}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: 12, opacity: 0.7 }}>API Key</div>
                        <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'monospace' }}>
                            {data?.ragflow_api_key_masked || '—'}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: 12, opacity: 0.7 }}>配置来源</div>
                        <Tag color={data?.config_source === 'database' ? 'green' : 'orange'} style={{ marginTop: 4 }}>
                            {data?.config_source === 'database' ? '✅ 数据库（动态）' : '⚙️ 环境变量（默认）'}
                        </Tag>
                    </div>
                </div>
            </div>

            {/* 修改配置 */}
            <div style={{
                background: 'var(--card)', border: '1px solid var(--border)',
                borderRadius: 12, padding: 24, marginBottom: 24,
            }}>
                <h3 style={{ marginBottom: 16 }}>⚙️ 修改连接配置</h3>

                <div style={{ marginBottom: 16 }}>
                    <label style={{ fontSize: 14, fontWeight: 600, display: 'block', marginBottom: 8 }}>
                        RAGFlow API 地址
                    </label>
                    <Input
                        value={baseUrl} onChange={e => setBaseUrl(e.target.value)}
                        placeholder="例如: http://172.30.2.29/api/v1"
                        disabled={!isIT}
                        style={{ fontFamily: 'monospace' }}
                    />
                    <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>
                        RAGFlow 服务的 API 地址，通常以 /api/v1 结尾
                    </div>
                </div>

                <div style={{ marginBottom: 16 }}>
                    <label style={{ fontSize: 14, fontWeight: 600, display: 'block', marginBottom: 8 }}>
                        RAGFlow API Key
                    </label>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <Input
                            type={showKey ? 'text' : 'password'}
                            value={apiKey} onChange={e => setApiKey(e.target.value)}
                            placeholder="ragflow-xxxx..."
                            disabled={!isIT}
                            style={{ flex: 1, fontFamily: 'monospace' }}
                        />
                        <Button onClick={() => setShowKey(!showKey)}>
                            {showKey ? '🙈 隐藏' : '👁 显示'}
                        </Button>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>
                        在 RAGFlow 管理界面的「系统」→「API Key 管理」中创建
                    </div>
                </div>

                {/* 测试结果 */}
                {testResult && (
                    <div style={{
                        padding: 12, borderRadius: 8, marginBottom: 16,
                        background: testResult.success ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                        border: `1px solid ${testResult.success ? '#10b981' : '#ef4444'}`,
                        color: testResult.success ? '#10b981' : '#ef4444',
                        fontSize: 14, fontWeight: 600,
                    }}>
                        {testResult.success ? '✅' : '❌'} {testResult.message}
                    </div>
                )}

                <Space>
                    {isIT && (
                        <>
                            <Button onClick={handleTest} loading={testing}
                                style={{ background: '#6366f1', color: '#fff', border: 'none' }}>
                                🔍 测试连接
                            </Button>
                            <Button type="primary" onClick={handleSave} loading={saving}>
                                💾 保存配置
                            </Button>
                        </>
                    )}
                    <Button onClick={loadConfig}>🔄 刷新</Button>
                </Space>
                {!isIT && <p style={{ color: 'var(--text3)', marginTop: 12 }}>⚠️ 仅IT管理员可修改连接配置</p>}
            </div>

            {/* 配置说明 */}
            <div style={{
                background: 'var(--card)', border: '1px solid var(--border)',
                borderRadius: 12, padding: 24,
            }}>
                <h3 style={{ marginBottom: 12 }}>💡 配置说明</h3>
                <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 2 }}>
                    <p>1. <strong>API 地址</strong>：RAGFlow 系统的 HTTP API 接口地址，格式为 <code>http://IP:端口/api/v1</code></p>
                    <p>2. <strong>API Key</strong>：用于认证的密钥，在 RAGFlow 管理界面中生成</p>
                    <p>3. 修改后点击「测试连接」验证配置是否正确</p>
                    <p>4. 确认连接成功后点击「保存配置」，配置会<strong>立即生效</strong>，无需重启服务</p>
                    <p>5. 配置保存到数据库后，会覆盖环境变量中的默认值，并在服务重启后自动加载</p>
                </div>
            </div>
        </div>
    );
}

// ========== 知识库配置 ==========
function KnowledgeBaseConfig({ isIT }: { isIT: boolean }) {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [data, setData] = useState<any>(null);
    const [selectedAssistant, setSelectedAssistant] = useState<string>('');

    const loadConfig = async () => {
        setLoading(true);
        try {
            const res = await api.get('/settings/knowledge-base');
            setData(res.data);
            setSelectedAssistant(res.data.current?.assistant_id || '');
        } catch (e: any) {
            message.error('加载知识库配置失败');
        } finally { setLoading(false); }
    };

    useEffect(() => { loadConfig(); }, []);

    const handleSave = async () => {
        if (!selectedAssistant) { message.warning('请选择助手'); return; }
        setSaving(true);
        try {
            await api.put('/settings/knowledge-base', { assistant_id: selectedAssistant });
            message.success('知识库配置已更新');
            loadConfig();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '保存失败');
        } finally { setSaving(false); }
    };

    // 找到选中助手对应的知识库
    const selectedAsst = data?.available_assistants?.find((a: any) => a.id === selectedAssistant);
    const linkedDatasets = selectedAsst?.dataset_ids || [];
    const datasetMap = Object.fromEntries((data?.available_datasets || []).map((d: any) => [d.id, d.name]));

    if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;

    return (
        <div className="fade-in">
            <div className="admin-header"><h2>📚 知识库配置</h2></div>

            {/* 当前连接状态 */}
            <div style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: 12, padding: 24, marginBottom: 24, color: '#fff',
            }}>
                <div style={{ fontSize: 14, opacity: 0.85, marginBottom: 12 }}>📡 当前连接</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    <div>
                        <div style={{ fontSize: 12, opacity: 0.7 }}>助手名称</div>
                        <div style={{ fontSize: 18, fontWeight: 700 }}>{data?.current?.assistant_name || '—'}</div>
                    </div>
                    <div>
                        <div style={{ fontSize: 12, opacity: 0.7 }}>AI 模型</div>
                        <div style={{ fontSize: 18, fontWeight: 700 }}>{data?.current?.model_name || '—'}</div>
                    </div>
                    <div>
                        <div style={{ fontSize: 12, opacity: 0.7 }}>助手 ID</div>
                        <div style={{ fontSize: 12, fontFamily: 'monospace', opacity: 0.8 }}>{data?.current?.assistant_id || '—'}</div>
                    </div>
                    <div>
                        <div style={{ fontSize: 12, opacity: 0.7 }}>配置来源</div>
                        <Tag color={data?.config_source === 'database' ? 'green' : 'orange'} style={{ marginTop: 4 }}>
                            {data?.config_source === 'database' ? '✅ 数据库（动态）' : '⚙️ 环境变量（默认）'}
                        </Tag>
                    </div>
                </div>

                {/* 关联知识库 */}
                {data?.current?.dataset_ids?.length > 0 && (
                    <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                        <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 8 }}>关联知识库</div>
                        <Space wrap>
                            {data.current.dataset_ids.map((id: string) => (
                                <Tag key={id} color="#ffffff40" style={{ color: '#fff', border: '1px solid rgba(255,255,255,0.4)' }}>
                                    📄 {datasetMap[id] || id}
                                </Tag>
                            ))}
                        </Space>
                    </div>
                )}
            </div>

            {/* 切换助手 */}
            <div style={{
                background: 'var(--card)', border: '1px solid var(--border)',
                borderRadius: 12, padding: 24,
            }}>
                <h3 style={{ marginBottom: 16 }}>🔄 切换助手</h3>

                <div style={{ marginBottom: 16 }}>
                    <label style={{ fontSize: 14, fontWeight: 600, display: 'block', marginBottom: 8 }}>选择 RAGFlow 助手</label>
                    <Select
                        value={selectedAssistant}
                        onChange={setSelectedAssistant}
                        style={{ width: '100%' }}
                        disabled={!isIT}
                        options={(data?.available_assistants || []).map((a: any) => ({
                            value: a.id,
                            label: `${a.name}  (${a.dataset_ids?.length || 0} 个知识库)`,
                        }))}
                        placeholder="选择助手"
                    />
                </div>

                {/* 选中助手关联的知识库 */}
                {linkedDatasets.length > 0 && (
                    <div style={{ marginBottom: 16, padding: 12, background: 'var(--bg2)', borderRadius: 8 }}>
                        <div style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 8 }}>该助手关联的知识库：</div>
                        <Space wrap>
                            {linkedDatasets.map((id: string) => (
                                <Tag key={id} color="blue">📄 {datasetMap[id] || id}</Tag>
                            ))}
                        </Space>
                    </div>
                )}

                <Space>
                    {isIT && <Button type="primary" onClick={handleSave} loading={saving}>保存配置</Button>}
                    <Button onClick={loadConfig}>🔄 刷新</Button>
                </Space>
                {!isIT && <p style={{ color: 'var(--text3)', marginTop: 12 }}>⚠️ 仅IT管理员可修改知识库配置</p>}
            </div>

            {/* 可用知识库列表 */}
            <div style={{ marginTop: 24, background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: 24 }}>
                <h3 style={{ marginBottom: 16 }}>📋 RAGFlow 知识库列表</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 12 }}>
                    {(data?.available_datasets || []).map((ds: any) => (
                        <div key={ds.id} style={{
                            padding: 16, borderRadius: 8, border: '1px solid var(--border)',
                            background: data?.current?.dataset_ids?.includes(ds.id) ? 'rgba(99, 102, 241, 0.08)' : 'var(--bg2)',
                        }}>
                            <div style={{ fontWeight: 600, marginBottom: 4 }}>📄 {ds.name}</div>
                            <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'monospace' }}>{ds.id}</div>
                            {data?.current?.dataset_ids?.includes(ds.id) && (
                                <Tag color="purple" style={{ marginTop: 8 }}>当前使用中</Tag>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// ========== 默认解析模式配置 ==========
function DefaultParseModeConfig({ isIT }: { isIT: boolean }) {
    const [mode, setMode] = useState<string>('auto');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        api.get('/settings/parse-mode').then(res => {
            if (res.data?.parse_mode) setMode(res.data.parse_mode);
        }).catch(() => {});
    }, []);

    const handleSave = async (newMode: string) => {
        setSaving(true);
        try {
            await api.put('/settings/parse-mode', { parse_mode: newMode });
            setMode(newMode);
            message.success('默认解析模式已更新');
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '更新失败');
        } finally { setSaving(false); }
    };

    return (
        <div style={{
            background: 'var(--card)', border: '1px solid var(--border)',
            borderRadius: 12, padding: 20, marginBottom: 16,
        }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                    <span style={{ fontSize: 15, fontWeight: 600 }}>🚀 默认解析模式</span>
                    <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '4px 0 0' }}>
                        控制文档上传后是否自动触发解析。用户可在上传弹窗中临时覆盖。
                    </p>
                </div>
                <Select
                    value={mode}
                    onChange={v => handleSave(v)}
                    disabled={!isIT || saving}
                    style={{ width: 160 }}
                    options={[
                        { value: 'auto', label: '自动解析' },
                        { value: 'manual', label: '仅上传' },
                    ]}
                />
            </div>
        </div>
    );
}

// ========== 文档解析配置 ==========
function ParseConfig({ isIT }: { isIT: boolean }) {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [items, setItems] = useState<any[]>([]);
    const [options, setOptions] = useState<any[]>([]);
    const [configSource, setConfigSource] = useState('');
    const [localConfig, setLocalConfig] = useState<Record<string, string>>({});
    const [schema, setSchema] = useState<Record<string, any>>({});
    const [parserConfigs, setParserConfigs] = useState<Record<string, any>>({});
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [drawerMethod, setDrawerMethod] = useState('');
    const [drawerExt, setDrawerExt] = useState('');

    const loadConfig = async () => {
        setLoading(true);
        try {
            const res = await api.get('/settings/parse-config');
            setItems(res.data.items || []);
            setOptions(res.data.options || []);
            setConfigSource(res.data.config_source || 'default');
            setSchema(res.data.parser_config_schema || {});
            setParserConfigs(res.data.parser_configs || {});
            const cfg: Record<string, string> = {};
            (res.data.items || []).forEach((item: any) => {
                cfg[item.extension] = item.chunk_method;
            });
            setLocalConfig(cfg);
        } catch { } finally { setLoading(false); }
    };

    useEffect(() => { loadConfig(); }, []);

    const handleChange = (ext: string, method: string) => {
        setLocalConfig(prev => ({ ...prev, [ext]: method }));
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await api.put('/settings/parse-config', {
                config: localConfig,
                parser_configs: parserConfigs,
            });
            message.success('解析配置已保存，新上传的文档将使用新配置');
            loadConfig();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '保存失败');
        } finally { setSaving(false); }
    };

    const getMethodLabel = (value: string) => {
        const opt = options.find((o: any) => o.value === value);
        return opt ? opt.label : value;
    };

    const getMethodDesc = (value: string) => {
        const opt = options.find((o: any) => o.value === value);
        return opt ? opt.desc : '';
    };

    const openDetail = (ext: string) => {
        const method = localConfig[ext];
        setDrawerMethod(method);
        setDrawerExt(ext);
        setDrawerOpen(true);
    };

    const updateParserParam = (method: string, key: string, value: any) => {
        setParserConfigs(prev => ({
            ...prev,
            [method]: { ...(prev[method] || {}), [key]: value },
        }));
    };

    // group 类型嵌套参数更新
    const updateNestedParam = (method: string, groupKey: string, childKey: string, value: any) => {
        setParserConfigs(prev => ({
            ...prev,
            [method]: {
                ...(prev[method] || {}),
                [groupKey]: {
                    ...(prev[method]?.[groupKey] || {}),
                    [childKey]: value,
                },
            },
        }));
    };

    // 渲染单个参数控件
    const renderParamControl = (param: any, values: any, method: string, groupKey?: string) => {
        const val = groupKey
            ? (values?.[groupKey]?.[param.key] ?? param.default)
            : (values?.[param.key] ?? param.default);
        const onChange = (v: any) => groupKey
            ? updateNestedParam(method, groupKey, param.key, v)
            : updateParserParam(method, param.key, v);

        switch (param.type) {
            case 'number':
                return (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <Slider min={param.min} max={param.max} step={param.step}
                            value={val} onChange={onChange} disabled={!isIT} style={{ flex: 1 }} />
                        <InputNumber min={param.min} max={param.max} step={param.step}
                            value={val} onChange={(v) => onChange(v ?? param.default)}
                            disabled={!isIT} style={{ width: 90 }} />
                    </div>
                );
            case 'text':
                return <Input value={val} onChange={(e) => onChange(e.target.value)}
                    disabled={!isIT} placeholder={param.default} />;
            case 'textarea':
                return <Input.TextArea rows={4} value={val} onChange={(e) => onChange(e.target.value)}
                    disabled={!isIT} placeholder={param.default || '请输入...'} />;
            case 'switch':
                return null; // switch 在标题行右侧渲染
            case 'select':
                return <Select value={val} onChange={onChange} disabled={!isIT} style={{ width: '100%' }}
                    options={(param.options || []).map((o: any) => ({ value: o.value, label: o.label }))} />;
            case 'tags':
                return <Select mode="tags" value={val || []} onChange={onChange} disabled={!isIT}
                    style={{ width: '100%' }} placeholder="输入后按回车添加" />;
            default:
                return null;
        }
    };

    // 渲染单个参数卡片
    const renderParamCard = (param: any, values: any, method: string, groupKey?: string) => {
        const val = groupKey
            ? (values?.[groupKey]?.[param.key] ?? param.default)
            : (values?.[param.key] ?? param.default);
        const onChange = (v: any) => groupKey
            ? updateNestedParam(method, groupKey, param.key, v)
            : updateParserParam(method, param.key, v);

        if (param.type === 'group') {
            // group 类型：折叠面板
            return (
                <Collapse ghost key={param.key} style={{ marginBottom: 0 }}
                    items={[{
                        key: param.key,
                        label: <span style={{ fontWeight: 700, fontSize: 14 }}>{param.label}</span>,
                        children: (
                            <div style={{ display: 'grid', gap: 16 }}>
                                {(param.children || []).map((child: any) =>
                                    renderParamCard(child, values, method, param.key)
                                )}
                            </div>
                        ),
                    }]}
                />
            );
        }

        return (
            <div key={`${groupKey || ''}_${param.key}`} style={{
                padding: 16, background: 'var(--bg2)',
                borderRadius: 10, border: '1px solid var(--border)',
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div>
                        <span style={{ fontWeight: 700, fontSize: 14 }}>{param.label}</span>
                        <span style={{ fontSize: 11, color: 'var(--text3)', marginLeft: 8 }}>({param.key})</span>
                    </div>
                    {param.type === 'switch' && (
                        <Switch checked={val} onChange={onChange} disabled={!isIT} />
                    )}
                </div>
                {param.desc && (
                    <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: param.type !== 'switch' ? 10 : 0, lineHeight: 1.6 }}>
                        {param.desc}
                    </div>
                )}
                {renderParamControl(param, values, method, groupKey)}
            </div>
        );
    };

    // 按文件类型分组
    const groups = [
        { title: '📊 表格类', desc: '适合结构化数据', exts: ['.xlsx', '.xls', '.csv'] },
        { title: '📝 文档类', desc: '适合文字内容', exts: ['.docx', '.doc', '.md', '.txt'] },
        { title: '📕 PDF 文档', desc: '适合排版复杂的文件', exts: ['.pdf'] },
        { title: '📽️ 演示文稿', desc: '幻灯片类文件', exts: ['.pptx', '.ppt'] },
        { title: '🌐 其他格式', desc: '网页、数据等', exts: ['.html', '.json', '.eml'] },
    ];

    const currentSchema = schema[drawerMethod] || { params: [] };
    const currentValues = parserConfigs[drawerMethod] || {};
    const drawerLabel = items.find(i => i.extension === drawerExt)?.file_type_label || drawerExt;

    if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;

    return (
        <div className="fade-in">
            <div className="admin-header">
                <h2>📄 文档解析配置</h2>
                <Tag color={configSource === 'database' ? 'green' : 'orange'}>
                    {configSource === 'database' ? '✅ 自定义配置' : '⚙️ 默认配置'}
                </Tag>
            </div>

            <div style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: 12, padding: 20, marginBottom: 24, color: '#fff',
            }}>
                <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>💡 什么是解析方式？</div>
                <div style={{ fontSize: 13, opacity: 0.9, lineHeight: 1.8 }}>
                    上传文档后，系统会根据文件类型自动选择解析方式，将文档拆分为小块知识。
                    不同解析方式适合不同类型的文档，选择合适的方式可以显著提升AI回答质量。
                    <strong> 点击「详情」可以查看和调整每种解析方式的详细参数。</strong>
                </div>
            </div>

            {/* 默认解析模式 */}
            <DefaultParseModeConfig isIT={isIT} />

            {groups.map(group => {
                const groupItems = group.exts.filter(ext => localConfig[ext] !== undefined);
                if (groupItems.length === 0) return null;
                return (
                    <div key={group.title} style={{
                        background: 'var(--card)', border: '1px solid var(--border)',
                        borderRadius: 12, padding: 20, marginBottom: 16,
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                            <span style={{ fontSize: 16, fontWeight: 700 }}>{group.title}</span>
                            <span style={{ fontSize: 12, color: 'var(--text3)' }}>{group.desc}</span>
                        </div>
                        <div style={{ display: 'grid', gap: 12 }}>
                            {groupItems.map(ext => {
                                const item = items.find((i: any) => i.extension === ext);
                                const label = item?.file_type_label || ext;
                                const method = localConfig[ext];
                                const methodParams = schema[method]?.params || [];
                                return (
                                    <div key={ext} style={{
                                        display: 'flex', alignItems: 'center', gap: 16,
                                        padding: '12px 16px', background: 'var(--bg2)',
                                        borderRadius: 8, border: '1px solid var(--border)',
                                    }}>
                                        <div style={{ minWidth: 180 }}>
                                            <div style={{ fontWeight: 600, fontSize: 14 }}>{label}</div>
                                        </div>
                                        <Select
                                            value={method}
                                            onChange={(val) => handleChange(ext, val)}
                                            disabled={!isIT}
                                            style={{ width: 200 }}
                                            options={options.map((o: any) => ({
                                                value: o.value,
                                                label: o.label,
                                            }))}
                                        />
                                        <span style={{ fontSize: 12, color: 'var(--text3)', flex: 1 }}>
                                            {getMethodDesc(method)}
                                        </span>
                                        <Button
                                            type="link" size="small"
                                            onClick={() => openDetail(ext)}
                                            disabled={methodParams.length === 0}
                                        >
                                            {methodParams.length > 0 ? '⚙️ 详情' : '—'}
                                        </Button>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                );
            })}

            <Space style={{ marginTop: 8 }}>
                {isIT && <Button type="primary" onClick={handleSave} loading={saving}>💾 保存配置</Button>}
                <Button onClick={loadConfig}>🔄 刷新</Button>
            </Space>
            {!isIT && <p style={{ color: 'var(--text3)', marginTop: 12 }}>⚠️ 仅IT管理员可修改解析配置</p>}

            {/* ===== 详情抽屉 ===== */}
            <Modal
                title={<span>⚙️ 解析参数 - {drawerLabel}（{getMethodLabel(drawerMethod)}）</span>}
                open={drawerOpen}
                onCancel={() => setDrawerOpen(false)}
                footer={null}
                width={600}
            >
                <div style={{
                    padding: '12px 0', marginBottom: 16, borderBottom: '1px solid var(--border)',
                }}>
                    <Tag color="blue" style={{ fontSize: 13, padding: '4px 12px' }}>{getMethodLabel(drawerMethod)}</Tag>
                    <span style={{ fontSize: 13, color: 'var(--text3)', marginLeft: 8 }}>{getMethodDesc(drawerMethod)}</span>
                </div>

                {currentSchema.params.length === 0 ? (
                    <div style={{ padding: 32, textAlign: 'center', color: 'var(--text3)' }}>
                        此解析方式没有可配置的参数
                    </div>
                ) : (() => {
                    const basicParams = currentSchema.params.filter((p: any) => (p.level || 'basic') === 'basic');
                    const advancedParams = currentSchema.params.filter((p: any) => p.level === 'advanced');
                    return (
                        <div>
                            {/* 基础参数 - 始终展示 */}
                            {basicParams.length > 0 && (
                                <div style={{ display: 'grid', gap: 16 }}>
                                    {basicParams.map((param: any) => renderParamCard(param, currentValues, drawerMethod))}
                                </div>
                            )}
                            {/* 高级参数 - 折叠展示 */}
                            {advancedParams.length > 0 && (
                                <Collapse ghost style={{ marginTop: 16 }}
                                    items={[{
                                        key: 'advanced',
                                        label: <span style={{ fontWeight: 600, fontSize: 14 }}>🔧 高级设置</span>,
                                        children: (
                                            <div style={{ display: 'grid', gap: 16 }}>
                                                {advancedParams.map((param: any) => renderParamCard(param, currentValues, drawerMethod))}
                                            </div>
                                        ),
                                    }]}
                                />
                            )}
                        </div>
                    );
                })()}

                {isIT && currentSchema.params.length > 0 && (
                    <div style={{ marginTop: 20, textAlign: 'right' }}>
                        <Button type="primary" onClick={() => { setDrawerOpen(false); handleSave(); }} loading={saving}>
                            💾 保存并关闭
                        </Button>
                    </div>
                )}
            </Modal>
        </div>
    );
}

// ========== 对话配置 ==========
function ChatConfig({ isIT }: { isIT: boolean }) {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        api.get('/settings/chat-config').then(r => form.setFieldsValue(r.data)).catch(() => { });
    }, []);

    const handleSave = async () => {
        setLoading(true);
        try {
            await api.put('/settings/chat-config', form.getFieldsValue());
            message.success('配置已保存');
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '保存失败');
        } finally { setLoading(false); }
    };

    return (
        <div className="fade-in">
            <div className="admin-header"><h2>对话配置</h2></div>
            <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
                <Form.Item name="system_prompt" label="系统提示词 (Prompt 模板)"
                    help="定义AI角色和回答规则，支持变量 {{company_name}}、{{product_name}}">
                    <Input.TextArea rows={6} disabled={!isIT}
                        placeholder="你是{{company_name}}的智能客服助手，专门回答关于{{product_name}}的问题。请基于知识库回答，如不确定请明确告知用户。" />
                </Form.Item>
                <Form.Item name="temperature" label="Temperature (创造性)"><Slider min={0} max={1} step={0.1} disabled={!isIT} /></Form.Item>
                <Form.Item name="top_p" label="Top P (多样性)"><Slider min={0} max={1} step={0.1} disabled={!isIT} /></Form.Item>
                <Form.Item name="max_tokens" label="Max Tokens (最大长度)"><InputNumber min={256} max={8192} step={256} disabled={!isIT} style={{ width: '100%' }} /></Form.Item>
                <Form.Item name="similarity_threshold" label="相似度阈值"><Slider min={0} max={1} step={0.05} disabled={!isIT} /></Form.Item>
                <Form.Item name="top_n" label="检索数量 (Top N)"><InputNumber min={1} max={20} disabled={!isIT} style={{ width: '100%' }} /></Form.Item>
                {isIT && <Button type="primary" onClick={handleSave} loading={loading}>保存配置</Button>}
                {!isIT && <p style={{ color: 'var(--text3)' }}>⚠️ 仅IT管理员可修改设置</p>}
            </Form>
        </div>
    );
}

// ========== 审计日志 ==========
function AuditLogs() {
    const [logs, setLogs] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);

    useEffect(() => {
        api.get('/settings/audit-logs', { params: { page, page_size: pageSize } })
            .then(res => { setLogs(res.data.items || []); setTotal(res.data.total || 0); })
            .catch(() => { });
    }, [page, pageSize]);

    return (
        <div className="fade-in">
            <div className="admin-header"><h2>审计日志</h2></div>
            <Table
                columns={[
                    { title: '用户', dataIndex: 'user_id', width: 120 },
                    { title: '操作', dataIndex: 'action', width: 100 },
                    { title: '资源', dataIndex: 'resource_type', width: 100 },
                    { title: '详情', dataIndex: 'detail', ellipsis: true },
                    { title: 'IP', dataIndex: 'ip_address', width: 130 },
                    {
                        title: '时间', dataIndex: 'created_at', width: 180,
                        render: (v: string) => formatTime(v),
                    },
                ]}
                dataSource={logs} rowKey="id"
                pagination={{
                    current: page, total, pageSize,
                    showSizeChanger: true,
                    onChange: (p, ps) => { setPage(p); setPageSize(ps); },
                }}
            />
        </div>
    );
}

// ========== 公告管理 ==========
function Announcements() {
    const [items, setItems] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [modalOpen, setModalOpen] = useState(false);
    const [editItem, setEditItem] = useState<any>(null);
    const [form] = Form.useForm();

    const loadData = async () => {
        try {
            const res = await api.get('/announcements', { params: { page, page_size: pageSize } });
            setItems(res.data.items || []); setTotal(res.data.total || 0);
        } catch { }
    };

    useEffect(() => { loadData(); }, [page, pageSize]);

    // FR-38: Switch 快捷开关
    const handleToggle = async (record: any) => {
        try {
            await api.put(`/announcements/${record.id}`, { is_active: !record.is_active });
            loadData();
        } catch { message.error('操作失败'); }
    };

    // FR-38: 删除
    const handleDelete = async (id: string) => {
        try {
            await api.delete(`/announcements/${id}`);
            message.success('已删除');
            loadData();
        } catch { message.error('删除失败'); }
    };

    const handleSave = async () => {
        const values = await form.validateFields();
        // FR-38: 序列化 scheduled_at 为 ISO 字符串
        const payload = {
            ...values,
            is_active: values.is_active ?? true,
            scheduled_at: values.scheduled_at ? dayjs(values.scheduled_at).format('YYYY-MM-DDTHH:mm:ss') : null,
        };
        if (editItem) { await api.put(`/announcements/${editItem.id}`, payload); }
        else { await api.post('/announcements', payload); }
        message.success('操作成功');
        setModalOpen(false); form.resetFields(); setEditItem(null); loadData();
    };

    return (
        <div className="fade-in">
            <div className="admin-header">
                <h2>公告管理</h2>
                <button className="btn btn-primary" onClick={() => { setEditItem(null); form.resetFields(); setModalOpen(true); }}>+ 新增公告</button>
            </div>
            <Table
                columns={[
                    { title: '标题', dataIndex: 'title', ellipsis: true },
                    {
                        title: '状态', width: 90,
                        render: (_: any, r: any) => {
                            if (!r.is_active) return <Tag color="default">已禁用</Tag>;
                            if (r.scheduled_at && new Date(r.scheduled_at) > new Date())
                                return <Tag color="orange">待发布</Tag>;
                            return <Tag color="green">已启用</Tag>;
                        },
                    },
                    {
                        title: '开关', width: 70,
                        render: (_: any, r: any) => <Switch size="small" checked={r.is_active} onChange={() => handleToggle(r)} />,
                    },
                    {
                        title: '定时发布', dataIndex: 'scheduled_at', width: 180,
                        render: (v: string) => v ? formatTime(v) : '-',
                    },
                    {
                        title: '创建时间', dataIndex: 'created_at', width: 180,
                        render: (v: string) => formatTime(v),
                    },
                    {
                        title: '操作', width: 140,
                        render: (_: any, r: any) => (
                            <Space>
                                <Button type="link" size="small" onClick={() => {
                                    setEditItem(r);
                                    form.setFieldsValue({
                                        ...r,
                                        scheduled_at: r.scheduled_at ? dayjs(r.scheduled_at) : null,
                                    });
                                    setModalOpen(true);
                                }}>编辑</Button>
                                <Popconfirm title="确认删除该公告？" onConfirm={() => handleDelete(r.id)}>
                                    <Button type="link" size="small" danger>删除</Button>
                                </Popconfirm>
                            </Space>
                        ),
                    },
                ]}
                dataSource={items} rowKey="id"
                pagination={{
                    current: page, total, pageSize,
                    showSizeChanger: true,
                    onChange: (p: number, ps: number) => { setPage(p); setPageSize(ps); },
                }}
            />
            <Modal title={editItem ? '编辑公告' : '新增公告'} open={modalOpen}
                onOk={handleSave} onCancel={() => { setModalOpen(false); setEditItem(null); form.resetFields(); }}>
                <Form form={form} layout="vertical" initialValues={{ is_active: true }}>
                    <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
                    <Form.Item name="content" label="内容" rules={[{ required: true }]}><Input.TextArea rows={5} /></Form.Item>
                    <Form.Item name="is_active" label="启用" valuePropName="checked"><Switch /></Form.Item>
                    <Form.Item name="scheduled_at" label="定时发布">
                        <DatePicker showTime format="YYYY-MM-DD HH:mm:ss" style={{ width: '100%' }} placeholder="留空表示立即生效" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}

// ========== 帮助中心 ==========
function HelpCenter() {
    return (
        <div className="fade-in">
            <div className="admin-header"><h2>帮助中心</h2></div>
            <div style={{ display: 'grid', gap: 16 }}>
                {[
                    { q: '如何上传文档？', a: '进入文档管理页面，点击右上角"批量上传"按钮，支持PDF、Word、Excel、PPT格式。' },
                    { q: '如何创建Q&A对？', a: '进入Q&A管理页面，点击"新增问答对"按钮填写问题和答案，或使用"批量导入"通过Excel导入。' },
                    { q: '如何处理工单？', a: '工单来自用户反馈"👎无用"时自动生成，进入工单管理页面查看和处理。' },
                ].map(item => (
                    <div key={item.q} style={{
                        background: 'var(--card)', border: '1px solid var(--border)',
                        borderRadius: 'var(--radius)', padding: 16,
                    }}>
                        <h4 style={{ marginBottom: 8 }}>❓ {item.q}</h4>
                        <p style={{ fontSize: 14, color: 'var(--text2)' }}>{item.a}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}
