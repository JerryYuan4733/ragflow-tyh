/**
 * Chat API 服务层 (T-038)
 */
import api from './api';

export interface ChatSession {
    id: string;
    title: string;
    created_at: string;
}

export const chatService = {
    /** 会话列表 */
    listSessions: () => api.get('/chat/sessions'),

    /** 创建会话 */
    createSession: (title: string) => api.post('/chat/sessions', { title }),

    /** 删除会话 */
    deleteSession: (id: string) => api.delete(`/chat/sessions/${id}`),

    /** 历史消息 */
    getMessages: (sessionId: string) => api.get(`/chat/sessions/${sessionId}/messages`),

    /** SSE流式发送 (返回EventSource URL) */
    getStreamUrl: (sessionId: string) => `/api/v1/chat/sessions/${sessionId}/messages`,

    /** 推荐问题 */
    getSuggestions: () => api.get('/chat/suggestions'),

    /** 搜索消息 */
    searchMessages: (keyword: string) => api.get('/chat/search', { params: { keyword } }),

    /** 反馈 Toggle (赞/踩/取消) */
    submitFeedback: (messageId: string, sessionId: string, type: 'like' | 'dislike', reasonCategory?: string) =>
        api.post('/feedbacks', {
            message_id: messageId,
            session_id: sessionId,
            type,
            reason_category: reasonCategory,
        }),

    /** 收藏 Toggle */
    toggleFavorite: (messageId: string) =>
        api.post('/favorites/toggle', { message_id: messageId }),

    /** 转人工 */
    transferToHuman: (messageId: string) =>
        api.post('/feedbacks/transfer', { message_id: messageId }),
};
