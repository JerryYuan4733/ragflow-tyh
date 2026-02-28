/**
 * API 响应通用类型定义
 */

/** 分页响应 */
export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    page_size: number;
}

/** API 错误响应 */
export interface ApiError {
    detail: string;
    code?: string;
}

/** 用户角色 */
export type UserRole = 'user' | 'kb_admin' | 'it_admin';

/** 工单状态 */
export type TicketStatus = 'pending' | 'processing' | 'resolved' | 'verified';

/** 反馈类型 */
export type FeedbackType = 'like' | 'dislike';

/** 文档状态 */
export type DocumentStatus = 'uploading' | 'parsing' | 'active' | 'expired' | 'archived';
