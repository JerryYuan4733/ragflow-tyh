/**
 * Document API 服务层 (T-038)
 */
import api from './api';

export const documentService = {
    /** 文档列表 */
    list: (params?: { page?: number; page_size?: number; keyword?: string; category?: string; dataset_id?: string }) =>
        api.get('/documents', { params }),

    /** 获取文档详情 */
    get: (id: string) => api.get(`/documents/${id}`),

    /** 上传文档 */
    upload: (formData: FormData) =>
        api.post('/documents', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        }),

    /** 更新元数据 */
    update: (id: string, data: any) => api.put(`/documents/${id}`, data),

    /** 替换版本 */
    replace: (id: string, formData: FormData) =>
        api.post(`/documents/${id}/replace`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        }),

    /** 删除 */
    delete: (id: string) => api.delete(`/documents/${id}`),

    /** 版本历史 */
    getVersions: (id: string) => api.get(`/documents/${id}/versions`),

    /** 获取当前团队绑定的知识库列表 */
    getMyDatasets: () => api.get('/documents/my-datasets'),

    /** 全量同步 RAGFlow 文档 */
    sync: () => api.post('/documents/sync'),

    /** 手动触发单文档解析 */
    parse: (id: string) => api.post(`/documents/${id}/parse`),

    /** 批量触发文档解析 */
    batchParse: (ids: string[]) => api.post('/documents/batch-parse', { document_ids: ids }),

    /** 一键清理异常文档记录 */
    cleanupOrphans: (datasetId?: string) =>
        api.delete('/documents/cleanup-orphans', { params: { dataset_id: datasetId } }),

    /** 实时查询单文档状态 */
    getStatus: (id: string) => api.get(`/documents/${id}/status`),

    /** 删除文档分类 */
    deleteCategory: (path: string) =>
        api.delete('/documents/categories', { data: { path } }),

    /** 批量修改文档分类 */
    batchUpdateCategory: (documentIds: string[], categoryPath: string) =>
        api.put('/documents/batch-category', { document_ids: documentIds, category_path: categoryPath }),

    /** 获取默认解析模式 */
    getParseMode: () => api.get('/settings/parse-mode'),

    /** 更新默认解析模式（IT管理员） */
    updateParseMode: (parseMode: string) => api.put('/settings/parse-mode', { parse_mode: parseMode }),
};
