/**
 * Q&A API 服务层 (T-038)
 */
import api from './api';

export const qaService = {
    list: (params?: { page?: number; page_size?: number; keyword?: string; dataset_id?: string; status?: string; source?: string }) =>
        api.get('/qa-pairs', { params }),

    changeStatus: (id: string, status: string) =>
        api.put(`/qa-pairs/${id}/status`, { status }),

    create: (data: { question: string; answer: string }) =>
        api.post('/qa-pairs', data),

    update: (id: string, data: any) => api.put(`/qa-pairs/${id}`, data),

    delete: (id: string) => api.delete(`/qa-pairs/${id}`),

    import: (formData: FormData) =>
        api.post('/qa-pairs/import', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        }),

    downloadTemplate: () =>
        api.get('/qa-pairs/template', { responseType: 'blob' }),

    getVersions: (id: string) => api.get(`/qa-pairs/${id}/versions`),

    /** 正向同步 V3：将 QA 推送到 RAGFlow（支持分组路由 + 勾选推送） */
    syncToRagflow: (datasetId?: string, qaIds?: string[]) =>
        api.post('/qa-pairs/sync-to-ragflow', {
            dataset_id: datasetId,
            qa_ids: qaIds?.length ? qaIds : undefined,
        }),

    /** 反向同步：从 RAGFlow 知识库拉取 QA */
    syncFromRagflow: (datasetId?: string) =>
        api.post('/qa-pairs/sync-from-ragflow', { dataset_id: datasetId }),
};
