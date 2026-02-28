/**
 * Ticket + Feedback API 服务层 (T-039)
 */
import api from './api';

export const ticketService = {
    list: (params?: { page?: number; page_size?: number; status?: string }) =>
        api.get('/tickets', { params }),

    get: (id: string) => api.get(`/tickets/${id}`),

    assign: (id: string, assigneeId: string) =>
        api.put(`/tickets/${id}/assign`, { assignee_id: assigneeId }),

    resolve: (id: string, resolution: string, qaData?: { qa_question?: string; qa_answer?: string }) =>
        api.put(`/tickets/${id}/resolve`, { resolution, ...qaData }),

    verify: (id: string) => api.put(`/tickets/${id}/verify`),

    reopen: (id: string, reason: string) =>
        api.put(`/tickets/${id}/reopen`, { reason }),
};

export const feedbackService = {
    submit: (data: {
        message_id: string;
        session_id: string;
        type: 'like' | 'dislike';
        reason_category?: string;
        reason_custom?: string;
    }) => api.post('/feedbacks', data),

    transferHuman: (sessionId: string) =>
        api.post('/feedbacks/transfer', { session_id: sessionId }),
};

export const favoriteService = {
    list: () => api.get('/favorites'),
    add: (messageId: string) => api.post('/favorites', { message_id: messageId }),
    remove: (id: string) => api.delete(`/favorites/${id}`),
};
