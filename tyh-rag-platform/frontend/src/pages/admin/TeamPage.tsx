/**
 * 团队管理页面 - IT管理员专用
 * 四个Tab: 团队列表 / 成员管理 / 助手配置 / 知识库绑定
 */

import { useState, useEffect, useCallback } from 'react';
import {
    Tabs, Table, Button, Modal, Form, Input, Select, message, Tag,
    Space, Popconfirm, Card, Spin, Descriptions,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
    listTeams, createTeam, updateTeam, deleteTeam,
    listMembers, addMembers, removeMember,
    getTeamConfig, bindAssistant,
    listTeamDatasets, setTeamDatasets,
    listRagflowAssistants, listRagflowDatasets,
    listAllUsers,
} from '../../services/teamService';
import type { SimpleUser } from '../../services/teamService';
import type {
    Team, TeamMember, TeamConfig, TeamDataset,
    RagflowAssistant, RagflowDataset,
} from '../../types/team';

// ==================== 团队列表 Tab ====================

function TeamListTab({ onSelectTeam }: { onSelectTeam: (team: Team) => void }) {
    const [teams, setTeams] = useState<Team[]>([]);
    const [loading, setLoading] = useState(false);
    const [showCreate, setShowCreate] = useState(false);
    const [editingTeam, setEditingTeam] = useState<Team | null>(null);
    const [form] = Form.useForm();

    const fetchTeams = useCallback(async () => {
        setLoading(true);
        try {
            const data = await listTeams({ page: 1, page_size: 100 });
            setTeams(data.items);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchTeams(); }, [fetchTeams]);

    const handleCreate = async (values: { name: string; description?: string }) => {
        try {
            await createTeam(values);
            message.success('团队创建成功');
            setShowCreate(false);
            form.resetFields();
            fetchTeams();
        } catch (e: any) {
            message.error(e.response?.data?.detail || '创建失败');
        }
    };

    const handleUpdate = async (values: { name?: string; description?: string }) => {
        if (!editingTeam) return;
        try {
            await updateTeam(editingTeam.id, values);
            message.success('更新成功');
            setEditingTeam(null);
            fetchTeams();
        } catch (e: any) {
            message.error(e.response?.data?.detail || '更新失败');
        }
    };

    const handleDelete = async (teamId: string) => {
        try {
            await deleteTeam(teamId);
            message.success('删除成功');
            fetchTeams();
        } catch (e: any) {
            message.error(e.response?.data?.detail || '删除失败');
        }
    };

    const columns: ColumnsType<Team> = [
        { title: '团队名称', dataIndex: 'name', key: 'name' },
        { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
        {
            title: '成员数', dataIndex: 'member_count', key: 'member_count', width: 80,
            render: (v: number) => <Tag color="blue">{v}</Tag>,
        },
        {
            title: '助手', key: 'assistant', width: 80,
            render: (_: any, r: Team) => r.has_assistant ? <Tag color="green">已绑定</Tag> : <Tag>未绑定</Tag>,
        },
        {
            title: '知识库', dataIndex: 'dataset_count', key: 'dataset_count', width: 80,
            render: (v: number) => v > 0 ? <Tag color="cyan">{v}个</Tag> : <Tag>无</Tag>,
        },
        {
            title: '操作', key: 'action', width: 220,
            render: (_: any, record: Team) => (
                <Space>
                    <Button size="small" onClick={() => onSelectTeam(record)}>管理</Button>
                    <Button size="small" onClick={() => { setEditingTeam(record); }}>编辑</Button>
                    <Popconfirm title="确定删除该团队？" onConfirm={() => handleDelete(record.id)}>
                        <Button size="small" danger>删除</Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 15, fontWeight: 600 }}>共 {teams.length} 个团队</span>
                <Button type="primary" onClick={() => setShowCreate(true)}>+ 新建团队</Button>
            </div>
            <Table
                columns={columns}
                dataSource={teams}
                rowKey="id"
                loading={loading}
                pagination={false}
                size="middle"
            />

            {/* 新建弹窗 */}
            <Modal
                title="新建团队"
                open={showCreate}
                onCancel={() => { setShowCreate(false); form.resetFields(); }}
                onOk={() => form.submit()}
            >
                <Form form={form} layout="vertical" onFinish={handleCreate}>
                    <Form.Item name="name" label="团队名称" rules={[{ required: true, message: '请输入团队名称' }]}>
                        <Input placeholder="如：华南区销售团队" />
                    </Form.Item>
                    <Form.Item name="description" label="描述">
                        <Input.TextArea rows={3} placeholder="团队描述（选填）" />
                    </Form.Item>
                </Form>
            </Modal>

            {/* 编辑弹窗 */}
            <Modal
                title="编辑团队"
                open={!!editingTeam}
                onCancel={() => setEditingTeam(null)}
                onOk={() => {
                    const nameEl = document.getElementById('edit-team-name') as HTMLInputElement;
                    const descEl = document.getElementById('edit-team-desc') as HTMLTextAreaElement;
                    handleUpdate({ name: nameEl?.value, description: descEl?.value });
                }}
            >
                {editingTeam && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        <div>
                            <label>团队名称</label>
                            <Input id="edit-team-name" defaultValue={editingTeam.name} />
                        </div>
                        <div>
                            <label>描述</label>
                            <Input.TextArea id="edit-team-desc" rows={3} defaultValue={editingTeam.description || ''} />
                        </div>
                    </div>
                )}
            </Modal>
        </>
    );
}

// ==================== 成员管理 Tab ====================

function MembersTab({ teamId, teamName }: { teamId: string; teamName: string }) {
    const [members, setMembers] = useState<TeamMember[]>([]);
    const [loading, setLoading] = useState(false);
    const [showAdd, setShowAdd] = useState(false);
    const [allUsers, setAllUsers] = useState<SimpleUser[]>([]);
    const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
    const [addLoading, setAddLoading] = useState(false);
    const [userSearchKeyword, setUserSearchKeyword] = useState('');

    const fetchMembers = useCallback(async () => {
        setLoading(true);
        try {
            const data = await listMembers(teamId);
            setMembers(data.items);
        } finally {
            setLoading(false);
        }
    }, [teamId]);

    useEffect(() => { fetchMembers(); }, [fetchMembers]);

    /** 打开添加成员弹窗时，加载所有用户 */
    const handleOpenAdd = async () => {
        setShowAdd(true);
        setSelectedUserIds([]);
        setUserSearchKeyword('');
        try {
            const data = await listAllUsers({ page_size: 100 });
            setAllUsers(data.items);
        } catch {
            message.error('获取用户列表失败');
        }
    };

    const handleAdd = async () => {
        if (selectedUserIds.length === 0) {
            message.warning('请至少选择一个用户');
            return;
        }
        setAddLoading(true);
        try {
            const result = await addMembers(teamId, { user_ids: selectedUserIds });
            message.success(result.message);
            setShowAdd(false);
            setSelectedUserIds([]);
            fetchMembers();
        } catch (e: any) {
            message.error(e.response?.data?.detail || '添加失败');
        } finally {
            setAddLoading(false);
        }
    };

    const handleRemove = async (userId: string) => {
        try {
            await removeMember(teamId, userId);
            message.success('已移除');
            fetchMembers();
        } catch (e: any) {
            message.error(e.response?.data?.detail || '移除失败');
        }
    };

    // 已是成员的用户ID集合
    const memberIdSet = new Set(members.map(m => m.user_id));

    // 根据搜索关键词过滤用户列表
    const filteredUsers = allUsers.filter(u => {
        if (userSearchKeyword) {
            const kw = userSearchKeyword.toLowerCase();
            return u.username.toLowerCase().includes(kw)
                || u.display_name.toLowerCase().includes(kw);
        }
        return true;
    });

    const ROLE_MAP: Record<string, string> = { it_admin: 'IT管理员', kb_admin: '知识管理员', user: '普通用户' };

    const columns: ColumnsType<TeamMember> = [
        { title: '用户名', dataIndex: 'username', key: 'username' },
        { title: '姓名', dataIndex: 'display_name', key: 'display_name' },
        {
            title: '角色', dataIndex: 'role', key: 'role',
            render: (v: string) => ROLE_MAP[v] || v,
        },
        {
            title: '默认团队', dataIndex: 'is_default', key: 'is_default', width: 80,
            render: (v: boolean) => v ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
        },
        { title: '加入时间', dataIndex: 'joined_at', key: 'joined_at', width: 180 },
        {
            title: '操作', key: 'action', width: 120,
            render: (_: any, r: TeamMember) =>
                r.role === 'it_admin' ? (
                    <Button size="small" disabled title="IT管理员默认属于所有团队">移除</Button>
                ) : (
                    <Popconfirm title={`确定移除 ${r.display_name}？`} onConfirm={() => handleRemove(r.user_id)}>
                        <Button size="small" danger>移除</Button>
                    </Popconfirm>
                ),
        },
    ];

    // 弹窗中用户选择列表的列定义
    const userColumns: ColumnsType<SimpleUser> = [
        { title: '用户名', dataIndex: 'username', key: 'username' },
        { title: '姓名', dataIndex: 'display_name', key: 'display_name' },
        {
            title: '角色', dataIndex: 'role', key: 'role', width: 100,
            render: (v: string) => ROLE_MAP[v] || v,
        },
        {
            title: '状态', key: 'status', width: 80,
            render: (_: any, r: SimpleUser) =>
                memberIdSet.has(r.id) ? <Tag color="green">已加入</Tag> : <Tag>未加入</Tag>,
        },
    ];

    return (
        <>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 15, fontWeight: 600 }}>
                    {teamName} - 成员管理 ({members.length}人)
                </span>
                <Button type="primary" onClick={handleOpenAdd}>+ 添加成员</Button>
            </div>
            <Table columns={columns} dataSource={members} rowKey="user_id" loading={loading} pagination={false} size="middle" />

            <Modal
                title="添加成员"
                open={showAdd}
                width={640}
                onCancel={() => setShowAdd(false)}
                onOk={handleAdd}
                confirmLoading={addLoading}
                okText={`确定添加 (${selectedUserIds.length})`}
                okButtonProps={{ disabled: selectedUserIds.length === 0 }}
            >
                <Input.Search
                    placeholder="搜索用户名或姓名"
                    value={userSearchKeyword}
                    onChange={e => setUserSearchKeyword(e.target.value)}
                    allowClear
                    style={{ marginBottom: 12 }}
                />
                <Table
                    size="small"
                    columns={userColumns}
                    dataSource={filteredUsers}
                    rowKey="id"
                    pagination={false}
                    scroll={{ y: 320 }}
                    rowSelection={{
                        selectedRowKeys: selectedUserIds,
                        onChange: (keys) => setSelectedUserIds(keys as string[]),
                        getCheckboxProps: (record: SimpleUser) => ({
                            disabled: memberIdSet.has(record.id),
                        }),
                    }}
                />
            </Modal>
        </>
    );
}

// ==================== 助手配置 Tab ====================

function AssistantTab({ teamId, teamName }: { teamId: string; teamName: string }) {
    const [config, setConfig] = useState<TeamConfig | null>(null);
    const [assistants, setAssistants] = useState<RagflowAssistant[]>([]);
    const [selectedId, setSelectedId] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [ragflowError, setRagflowError] = useState('');

    const fetchData = useCallback(async () => {
        setLoading(true);
        setRagflowError('');
        try {
            // 分离请求，避免 RAGFlow 不可用时配置也无法加载
            const cfgData = await getTeamConfig(teamId);
            setConfig(cfgData);
            setSelectedId(cfgData.ragflow_assistant_id || '');
            try {
                const astData = await listRagflowAssistants();
                setAssistants(astData.items);
            } catch (e: any) {
                const detail = e.response?.data?.detail || 'RAGFlow 连接失败';
                setRagflowError(detail);
                setAssistants([]);
            }
        } finally {
            setLoading(false);
        }
    }, [teamId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleBind = async () => {
        if (!selectedId) {
            message.warning('请选择助手');
            return;
        }
        setSaving(true);
        try {
            const result = await bindAssistant(teamId, { ragflow_assistant_id: selectedId });
            setConfig(result);
            message.success('助手绑定成功');
        } catch (e: any) {
            message.error(e.response?.data?.detail || '绑定失败');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <Spin />;

    return (
        <Card title={`${teamName} - 助手配置`} style={{ maxWidth: 600 }}>
            <Descriptions column={1} style={{ marginBottom: 16 }}>
                <Descriptions.Item label="当前助手">
                    {config?.ragflow_assistant_name
                        ? <Tag color="green">{config.ragflow_assistant_name}</Tag>
                        : <Tag>未绑定</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="助手ID">
                    {config?.ragflow_assistant_id || '-'}
                </Descriptions.Item>
            </Descriptions>

            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <Select
                    style={{ flex: 1 }}
                    placeholder="从 RAGFlow 选择助手"
                    value={selectedId || undefined}
                    onChange={setSelectedId}
                    options={assistants.map(a => ({ label: a.name, value: a.id }))}
                    showSearch
                    filterOption={(input, option) =>
                        (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                />
                <Button type="primary" loading={saving} onClick={handleBind}>
                    绑定
                </Button>
            </div>

            {ragflowError && (
                <div style={{ color: '#ff4d4f', marginTop: 12 }}>
                    <p>ℹ️ {ragflowError}</p>
                    <Button size="small" onClick={fetchData}>重试连接</Button>
                </div>
            )}
            {!ragflowError && assistants.length === 0 && !loading && (
                <p style={{ color: '#999', marginTop: 12 }}>
                    未从 RAGFlow 获取到助手列表，请检查 RAGFlow 连接配置。
                </p>
            )}
        </Card>
    );
}

// ==================== 知识库绑定 Tab ====================

function DatasetsTab({ teamId, teamName }: { teamId: string; teamName: string }) {
    const [boundDatasets, setBoundDatasets] = useState<TeamDataset[]>([]);
    const [allDatasets, setAllDatasets] = useState<RagflowDataset[]>([]);
    const [selectedIds, setSelectedIds] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [ragflowError, setRagflowError] = useState('');

    const fetchData = useCallback(async () => {
        setLoading(true);
        setRagflowError('');
        try {
            // 分离请求，避免 RAGFlow 不可用时已绑定数据也无法加载
            const boundData = await listTeamDatasets(teamId);
            setBoundDatasets(boundData.items);
            setSelectedIds(boundData.items.map(d => d.ragflow_dataset_id));
            try {
                const allData = await listRagflowDatasets({ page: 1, page_size: 100 });
                setAllDatasets(allData.items);
            } catch (e: any) {
                const detail = e.response?.data?.detail || 'RAGFlow 连接失败';
                setRagflowError(detail);
                setAllDatasets([]);
            }
        } finally {
            setLoading(false);
        }
    }, [teamId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleSave = async () => {
        setSaving(true);
        try {
            const result = await setTeamDatasets(teamId, { dataset_ids: selectedIds });
            setBoundDatasets(result.items);
            message.success(`已绑定 ${result.total} 个知识库`);
        } catch (e: any) {
            message.error(e.response?.data?.detail || '保存失败');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <Spin />;

    return (
        <Card title={`${teamName} - 知识库绑定`} style={{ maxWidth: 700 }}>
            <p style={{ color: '#666', marginBottom: 12 }}>
                选择要绑定到该团队的 RAGFlow 知识库（可多选）。保存后将全量替换当前绑定。
            </p>

            <Select
                mode="multiple"
                style={{ width: '100%', marginBottom: 16 }}
                placeholder="从 RAGFlow 选择知识库"
                value={selectedIds}
                onChange={setSelectedIds}
                options={allDatasets.map(d => ({
                    label: `${d.name} (${d.document_count}文档, ${d.chunk_count}分片)`,
                    value: d.id,
                }))}
                showSearch
                filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
            />

            <Button type="primary" loading={saving} onClick={handleSave}>
                保存绑定
            </Button>

            {boundDatasets.length > 0 && (
                <div style={{ marginTop: 16 }}>
                    <h4>当前已绑定 ({boundDatasets.length})</h4>
                    <Table
                        size="small"
                        pagination={false}
                        rowKey="id"
                        dataSource={boundDatasets}
                        columns={[
                            { title: '知识库名称', dataIndex: 'ragflow_dataset_name', key: 'name' },
                            { title: '文档数', dataIndex: 'document_count', key: 'doc', width: 80 },
                            { title: '分片数', dataIndex: 'chunk_count', key: 'chunk', width: 80 },
                        ]}
                    />
                </div>
            )}

            {ragflowError && (
                <div style={{ color: '#ff4d4f', marginTop: 12 }}>
                    <p>ℹ️ {ragflowError}</p>
                    <Button size="small" onClick={fetchData}>重试连接</Button>
                </div>
            )}
            {!ragflowError && allDatasets.length === 0 && !loading && (
                <p style={{ color: '#999', marginTop: 12 }}>
                    未从 RAGFlow 获取到知识库列表，请检查 RAGFlow 连接配置。
                </p>
            )}
        </Card>
    );
}

// ==================== 主页面 ====================

export default function TeamPage() {
    const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
    const [activeTab, setActiveTab] = useState('list');

    const handleSelectTeam = (team: Team) => {
        setSelectedTeam(team);
        setActiveTab('members');
    };

    const handleBackToList = () => {
        setSelectedTeam(null);
        setActiveTab('list');
    };

    return (
        <div style={{ padding: '20px 24px', width: '100%', overflow: 'auto' }}>
            <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
                <h2 style={{ margin: 0 }}>🏢 团队管理</h2>
                {selectedTeam && (
                    <>
                        <span style={{ color: '#999' }}>/</span>
                        <span style={{ fontWeight: 600 }}>{selectedTeam.name}</span>
                        <Button size="small" onClick={handleBackToList}>← 返回列表</Button>
                    </>
                )}
            </div>

            {!selectedTeam ? (
                <TeamListTab onSelectTeam={handleSelectTeam} />
            ) : (
                <Tabs
                    activeKey={activeTab}
                    onChange={setActiveTab}
                    items={[
                        {
                            key: 'members',
                            label: '👥 成员管理',
                            children: <MembersTab teamId={selectedTeam.id} teamName={selectedTeam.name} />,
                        },
                        {
                            key: 'assistant',
                            label: '🤖 助手配置',
                            children: <AssistantTab teamId={selectedTeam.id} teamName={selectedTeam.name} />,
                        },
                        {
                            key: 'datasets',
                            label: '📚 知识库绑定',
                            children: <DatasetsTab teamId={selectedTeam.id} teamName={selectedTeam.name} />,
                        },
                    ]}
                />
            )}
        </div>
    );
}
