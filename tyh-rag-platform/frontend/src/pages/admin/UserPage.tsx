import { useState, useEffect } from 'react';
import { Table, Button, Tag, Space, Modal, Form, Input, Select, message } from 'antd';
import { PlusOutlined, EditOutlined, KeyOutlined } from '@ant-design/icons';
import api from '../../services/api';

export default function UserPage() {
    const [users, setUsers] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [loading, setLoading] = useState(false);
    const [modalOpen, setModalOpen] = useState(false);
    const [editUser, setEditUser] = useState<any>(null);
    const [form] = Form.useForm();
    // Team options
    const [teams, setTeams] = useState<{ value: string; label: string }[]>([]);
    // Password reset modal
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
            // Fallback teams
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
            setModalOpen(false);
            form.resetFields();
            setEditUser(null);
            loadUsers();
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '操作失败');
        }
    };

    const handleToggle = async (id: string) => {
        await api.put(`/users/${id}/toggle`);
        message.success('操作成功');
        loadUsers();
    };

    const handleResetPassword = async () => {
        if (!newPassword.trim()) {
            message.error('请输入新密码');
            return;
        }
        try {
            await api.put(`/users/${resetUserId}/reset-password`, { password: newPassword });
            message.success('密码已重置');
            setResetPwdOpen(false);
            setNewPassword('');
        } catch (e: any) {
            message.error(e?.response?.data?.detail || '重置失败');
        }
    };

    const ROLE_MAP: Record<string, { color: string; text: string }> = {
        user: { color: 'default', text: '普通用户' },
        kb_admin: { color: 'blue', text: '知识库管理员' },
        it_admin: { color: 'purple', text: 'IT管理员' },
    };

    const columns = [
        { title: '用户名', dataIndex: 'username', key: 'username' },
        { title: '姓名', dataIndex: 'display_name', key: 'display_name' },
        {
            title: '角色', dataIndex: 'role', key: 'role',
            render: (r: string) => <Tag color={ROLE_MAP[r]?.color}>{ROLE_MAP[r]?.text}</Tag>
        },
        { title: '活跃团队', dataIndex: 'active_team_name', key: 'active_team_name' },
        {
            title: '状态', dataIndex: 'is_active', key: 'is_active',
            render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '启用' : '禁用'}</Tag>
        },
        { title: '上次登录', dataIndex: 'last_login_at', key: 'last_login_at', width: 180 },
        {
            title: '操作', key: 'action', width: 220,
            render: (_: any, r: any) => (
                <Space>
                    <Button type="link" size="small" icon={<EditOutlined />}
                        onClick={() => { setEditUser(r); form.setFieldsValue(r); setModalOpen(true); }}>编辑</Button>
                    <Button type="link" size="small" icon={<KeyOutlined />}
                        onClick={() => { setResetUserId(r.id); setNewPassword(''); setResetPwdOpen(true); }}>重置密码</Button>
                    <Button type="link" size="small" danger={r.is_active}
                        onClick={() => handleToggle(r.id)}>{r.is_active ? '禁用' : '启用'}</Button>
                </Space>
            ),
        },
    ];

    return (
        <div className="fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                <h2 style={{ fontWeight: 700 }}>用户管理</h2>
                <Button type="primary" icon={<PlusOutlined />}
                    onClick={() => { setEditUser(null); form.resetFields(); setModalOpen(true); }}>新增用户</Button>
            </div>
            <Table columns={columns} dataSource={users} rowKey="id" loading={loading}
                pagination={{
                    current: page, total, pageSize,
                    showSizeChanger: true,
                    onChange: (p: number, ps: number) => { setPage(p); setPageSize(ps); },
                }} />

            {/* 新增/编辑用户 */}
            <Modal title={editUser ? '编辑用户' : '新增用户'} open={modalOpen}
                onOk={handleSave} onCancel={() => { setModalOpen(false); setEditUser(null); }}>
                <Form form={form} layout="vertical">
                    <Form.Item name="username" label="用户名" rules={[{ required: !editUser }]}>
                        <Input disabled={!!editUser} />
                    </Form.Item>
                    {!editUser && (
                        <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                            <Input.Password />
                        </Form.Item>
                    )}
                    <Form.Item name="display_name" label="姓名" rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item name="role" label="角色" rules={[{ required: true }]}>
                        <Select options={[
                            { value: 'user', label: '普通用户' },
                            { value: 'kb_admin', label: '知识库管理员' },
                            { value: 'it_admin', label: 'IT管理员' },
                        ]} />
                    </Form.Item>
                    <Form.Item name="team_ids" label="所属团队" rules={[{ required: !editUser }]}>
                        <Select mode="multiple" placeholder="选择团队（可多选）" options={teams} showSearch
                            filterOption={(input, option) =>
                                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                            } />
                    </Form.Item>
                    <Form.Item name="job_number" label="工号">
                        <Input />
                    </Form.Item>
                </Form>
            </Modal>

            {/* 重置密码弹窗 */}
            <Modal title="重置密码" open={resetPwdOpen}
                onOk={handleResetPassword} onCancel={() => { setResetPwdOpen(false); setNewPassword(''); }}
                okText="确认重置" cancelText="取消">
                <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                    请输入新密码（至少6个字符）：
                </p>
                <Input.Password
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    placeholder="新密码"
                />
            </Modal>
        </div>
    );
}
