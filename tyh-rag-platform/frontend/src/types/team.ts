/**
 * 团队管理相关类型定义
 */

/** 团队基本信息 */
export interface Team {
    id: string;
    name: string;
    description?: string;
    member_count: number;
    has_assistant: boolean;
    dataset_count: number;
    created_at: string;
    updated_at: string;
}

/** 团队成员 */
export interface TeamMember {
    user_id: string;
    username: string;
    display_name: string;
    role: string;
    is_default: boolean;
    joined_at: string;
}

/** 团队配置（助手绑定） */
export interface TeamConfig {
    team_id: string;
    ragflow_assistant_id?: string;
    ragflow_assistant_name?: string;
}

/** 团队知识库绑定 */
export interface TeamDataset {
    id: string;
    ragflow_dataset_id: string;
    ragflow_dataset_name?: string;
    document_count: number;
    chunk_count: number;
}

/** RAGFlow 助手（代理接口返回） */
export interface RagflowAssistant {
    id: string;
    name: string;
}

/** RAGFlow 知识库（代理接口返回） */
export interface RagflowDataset {
    id: string;
    name: string;
    description?: string;
    document_count: number;
    chunk_count: number;
}

/** 用户所属团队条目 */
export interface MyTeamItem {
    team_id: string;
    team_name: string;
    is_default: boolean;
    is_active: boolean;
}

/** 用户团队列表响应 */
export interface MyTeamsResponse {
    items: MyTeamItem[];
    active_team_id?: string;
}
