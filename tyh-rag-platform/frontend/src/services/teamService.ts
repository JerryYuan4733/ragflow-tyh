/**
 * 团队管理 API 服务层
 */

import api from './api';
import type {
    Team, TeamMember, TeamConfig, TeamDataset,
    RagflowAssistant, RagflowDataset,
    MyTeamsResponse,
} from '../types/team';
import type { PaginatedResponse } from '../types/api';

// ==================== 团队 CRUD ====================

/** 获取团队列表 */
export async function listTeams(params?: {
    page?: number;
    page_size?: number;
    keyword?: string;
}): Promise<PaginatedResponse<Team>> {
    const res = await api.get('/teams', { params });
    return res.data;
}

/** 获取单个团队详情 */
export async function getTeam(teamId: string): Promise<Team> {
    const res = await api.get(`/teams/${teamId}`);
    return res.data;
}

/** 创建团队 */
export async function createTeam(data: {
    name: string;
    description?: string;
}): Promise<Team> {
    const res = await api.post('/teams', data);
    return res.data;
}

/** 编辑团队 */
export async function updateTeam(teamId: string, data: {
    name?: string;
    description?: string;
}): Promise<Team> {
    const res = await api.put(`/teams/${teamId}`, data);
    return res.data;
}

/** 删除团队 */
export async function deleteTeam(teamId: string): Promise<void> {
    await api.delete(`/teams/${teamId}`);
}

// ==================== 成员管理 ====================

/** 获取团队成员列表 */
export async function listMembers(teamId: string): Promise<{
    items: TeamMember[];
    total: number;
}> {
    const res = await api.get(`/teams/${teamId}/members`);
    return res.data;
}

/** 添加团队成员 */
export async function addMembers(teamId: string, data: {
    user_ids: string[];
    set_default?: boolean;
}): Promise<{ message: string; added: number }> {
    const res = await api.post(`/teams/${teamId}/members`, data);
    return res.data;
}

/** 移除团队成员 */
export async function removeMember(teamId: string, userId: string): Promise<void> {
    await api.delete(`/teams/${teamId}/members/${userId}`);
}

// ==================== 团队配置 ====================

/** 获取团队配置 */
export async function getTeamConfig(teamId: string): Promise<TeamConfig> {
    const res = await api.get(`/teams/${teamId}/config`);
    return res.data;
}

/** 绑定助手 */
export async function bindAssistant(teamId: string, data: {
    ragflow_assistant_id: string;
}): Promise<TeamConfig> {
    const res = await api.put(`/teams/${teamId}/config`, data);
    return res.data;
}

// ==================== 知识库绑定 ====================

/** 获取团队知识库列表 */
export async function listTeamDatasets(teamId: string): Promise<{
    items: TeamDataset[];
    total: number;
}> {
    const res = await api.get(`/teams/${teamId}/datasets`);
    return res.data;
}

/** 设置团队知识库（全量替换） */
export async function setTeamDatasets(teamId: string, data: {
    dataset_ids: string[];
}): Promise<{ items: TeamDataset[]; total: number }> {
    const res = await api.put(`/teams/${teamId}/datasets`, data);
    return res.data;
}

// ==================== RAGFlow 代理 ====================

/** 获取 RAGFlow 助手列表 */
export async function listRagflowAssistants(): Promise<{
    items: RagflowAssistant[];
    total: number;
}> {
    const res = await api.get('/ragflow/assistants');
    return res.data;
}

/** 获取 RAGFlow 知识库列表 */
export async function listRagflowDatasets(params?: {
    page?: number;
    page_size?: number;
}): Promise<{
    items: RagflowDataset[];
    total: number;
}> {
    const res = await api.get('/ragflow/datasets', { params });
    return res.data;
}

// ==================== 用户列表（供添加成员使用） ====================

/** 简要用户信息（用于成员选择） */
export interface SimpleUser {
    id: string;
    username: string;
    display_name: string;
    role: string;
}

/** 获取所有用户列表（仅IT管理员） */
export async function listAllUsers(params?: {
    page?: number;
    page_size?: number;
    keyword?: string;
}): Promise<{
    items: SimpleUser[];
    total: number;
}> {
    const res = await api.get('/users', { params: { page_size: 100, ...params } });
    return res.data;
}

// ==================== 团队切换 ====================

/** 获取当前用户所属团队列表 */
export async function getMyTeams(): Promise<MyTeamsResponse> {
    const res = await api.get('/auth/my-teams');
    return res.data;
}

/** 切换活跃团队 */
export async function switchTeam(teamId: string): Promise<{
    message: string;
    active_team_id: string;
    active_team_name: string;
}> {
    const res = await api.post('/auth/switch-team', { team_id: teamId });
    return res.data;
}
