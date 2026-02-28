import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuthStore } from '../stores/authStore';
import { useChatStore } from '../stores/chatStore';
import { chatService } from '../services/chatService';
import api from '../services/api';
import { formatTime } from '../utils/timeFormat';

export default function ChatPage() {
    const { token } = useAuthStore();
    const navigate = useNavigate();
    const {
        sessions, currentSessionId, messages,
        setSessions, setCurrentSession, addMessage,
        setMessages, setIsStreaming, setStreamingContent,
        streamingContent,
    } = useChatStore();

    const [inputText, setInputText] = useState('');
    const [isStreaming, setLocalStreaming] = useState(false);
    const [messagesLoading, setMessagesLoading] = useState(false);
    const [searchText, setSearchText] = useState('');
    const [showFeedbackModal, setShowFeedbackModal] = useState(false);
    const [feedbackReason, setFeedbackReason] = useState('');
    const [feedbackMsgId, setFeedbackMsgId] = useState('');
    const [showFavoritesModal, setShowFavoritesModal] = useState(false);
    const [favorites, setFavorites] = useState<any[]>([]);
    const [showSystemFeedbackModal, setShowSystemFeedbackModal] = useState(false);
    const [sysFeedbackCategory, setSysFeedbackCategory] = useState('功能建议');
    const [sysFeedbackContent, setSysFeedbackContent] = useState('');
    const [sysFeedbackRating, setSysFeedbackRating] = useState(0);
    const [showSearchModal, setShowSearchModal] = useState(false);
    const [searchKeyword, setSearchKeyword] = useState('');
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [searchLoading, setSearchLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    // tempId → realId 映射（SSE done 事件后替换）
    const idMapRef = useRef<Map<string, string>>(new Map());
    const [showTransferModal, setShowTransferModal] = useState(false);
    const [transferMsgId, setTransferMsgId] = useState('');
    const [transferLoading, setTransferLoading] = useState(false);

    useEffect(() => {
        loadSessions();
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, streamingContent]);

    const loadSessions = async () => {
        try {
            const res = await chatService.listSessions();
            setSessions(res.data?.items || []);
        } catch { }
    };

    const createSession = async () => {
        try {
            const res = await chatService.createSession('新会话');
            const s = res.data;
            setSessions([s, ...sessions]);
            setCurrentSession(s.id);
            setMessages([]);
        } catch {
            // Fallback: local session
            const id = `local-${Date.now()}`;
            setSessions([{ id, title: '新会话', created_at: new Date().toISOString() }, ...sessions]);
            setCurrentSession(id);
            setMessages([]);
        }
    };

    const selectSession = async (sid: string) => {
        setCurrentSession(sid);
        setMessagesLoading(true);
        try {
            const res = await chatService.getMessages(sid);
            // T-11.8: 从消息历史恢复交互状态
            const items = (res.data?.items || []).map((m: any) => ({
                id: m.id,
                role: m.role,
                content: m.content,
                citations: m.citations,
                created_at: m.created_at,
                feedbackType: m.feedback_type || null,
                isFavorited: !!m.is_favorited,
                isTransferred: !!m.is_transferred,
            }));
            setMessages(items);
        } catch (e) {
            console.error('加载会话消息失败:', e);
            setMessages([]);
        } finally {
            setMessagesLoading(false);
        }
    };

    const sendMessage = async (content?: string) => {
        const text = (content || inputText).trim();
        if (!text || isStreaming) return;
        setInputText('');
        setLocalStreaming(true);
        setIsStreaming(true);

        let sessionId = currentSessionId;
        if (!sessionId) {
            try {
                const res = await chatService.createSession(text.slice(0, 20));
                sessionId = res.data.id;
                setSessions([res.data, ...sessions]);
                setCurrentSession(sessionId);
            } catch {
                sessionId = `local-${Date.now()}`;
                setSessions([{ id: sessionId, title: text.slice(0, 20), created_at: new Date().toISOString() }, ...sessions]);
                setCurrentSession(sessionId);
            }
        }

        const userTempId = `user-${Date.now()}`;
        const aiTempId = `ai-${Date.now()}`;
        addMessage({ id: userTempId, role: 'user', content: text, _isStreaming: false });

        try {
            const response = await fetch(
                `/api/v1/chat/sessions/${sessionId}/messages`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                    body: JSON.stringify({ content: text }),
                }
            );
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let fullContent = '';
            let citations: any = null;
            let buffer = ''; // 缓冲区：处理跨 chunk 的不完整 SSE 行

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        // 流结束时处理缓冲区中剩余的数据
                        if (buffer.trim()) {
                            const line = buffer.trim();
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    if (data.content) fullContent += data.content;
                                    if (data.citations) citations = data.citations;
                                } catch { /* 忽略解析错误 */ }
                            }
                        }
                        break;
                    }
                    // 使用 stream: true 确保多字节字符不被截断
                    const chunk = decoder.decode(value, { stream: true });
                    buffer += chunk;

                    // 按换行符分割，但保留最后一个可能不完整的行
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || ''; // 最后一行可能不完整，放回缓冲区

                    for (const line of lines) {
                        const trimmedLine = line.trim();
                        if (trimmedLine.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(trimmedLine.slice(6));
                                if (data.type === 'done') {
                                    // T-10.1~10.3: 解析真实 ID 并替换
                                    if (data.user_message_id) idMapRef.current.set(userTempId, data.user_message_id);
                                    if (data.ai_message_id) idMapRef.current.set(aiTempId, data.ai_message_id);
                                    if (data.citations) citations = data.citations;
                                } else if (data.type === 'replace') {
                                    fullContent = data.content;
                                    setStreamingContent(fullContent);
                                } else if (data.content) {
                                    fullContent += data.content;
                                    setStreamingContent(fullContent);
                                }
                                if (data.type !== 'done' && data.citations) citations = data.citations;
                            } catch { /* 忽略解析错误 */ }
                        }
                    }
                }
            }

            // 添加 AI 消息
            addMessage({ id: aiTempId, role: 'assistant', content: fullContent || '抱歉，暂时无法回答。', citations, _isStreaming: false });

            // T-10.3: 用真实 ID 替换临时 ID
            const realUserMsgId = idMapRef.current.get(userTempId);
            const realAiMsgId = idMapRef.current.get(aiTempId);
            if (realUserMsgId || realAiMsgId) {
                setMessages((useChatStore.getState().messages).map((m: any) => {
                    if (m.id === userTempId && realUserMsgId) return { ...m, id: realUserMsgId };
                    if (m.id === aiTempId && realAiMsgId) return { ...m, id: realAiMsgId };
                    return m;
                }));
                idMapRef.current.delete(userTempId);
                idMapRef.current.delete(aiTempId);
            }
        } catch {
            addMessage({ id: aiTempId, role: 'assistant', content: '网络错误，请稍后重试。', _isStreaming: false });
        } finally {
            setLocalStreaming(false);
            setIsStreaming(false);
            setStreamingContent('');
        }
    };

    // T-11.5: 反馈 Toggle（乐观更新）
    const handleFeedbackToggle = async (msgId: string, type: 'like' | 'dislike') => {
        if (!currentSessionId) return;
        const msgs = useChatStore.getState().messages;
        const msg = msgs.find((m: any) => m.id === msgId);
        if (!msg) return;

        // 计算乐观状态
        const newType = msg.feedbackType === type ? null : type;
        // 乐观更新
        setMessages(msgs.map((m: any) => m.id === msgId ? { ...m, feedbackType: newType } : m));

        try {
            const res = await chatService.submitFeedback(msgId, currentSessionId, type);
            // 服务端返回的最终状态
            const serverType = res.data?.type || null;
            setMessages(useChatStore.getState().messages.map((m: any) =>
                m.id === msgId ? { ...m, feedbackType: serverType } : m
            ));
            // T-12.4: 3 踩弹窗建议转人工
            if (res.data?.suggest_transfer) {
                setTransferMsgId(msgId);
                setShowTransferModal(true);
            }
        } catch {
            // 回滚
            setMessages(useChatStore.getState().messages.map((m: any) =>
                m.id === msgId ? { ...m, feedbackType: msg.feedbackType } : m
            ));
            message.error('反馈失败，请重试');
        }
    };

    // 踩反馈弹窗（填写原因）
    const handleFeedback = (msgId: string) => {
        setFeedbackMsgId(msgId);
        setShowFeedbackModal(true);
    };

    const submitFeedback = async () => {
        if (!currentSessionId) return;
        try {
            const res = await chatService.submitFeedback(feedbackMsgId, currentSessionId, 'dislike', feedbackReason || undefined);
            const serverType = res.data?.type || null;
            setMessages(useChatStore.getState().messages.map((m: any) =>
                m.id === feedbackMsgId ? { ...m, feedbackType: serverType } : m
            ));
            message.success('感谢反馈！');
            if (res.data?.suggest_transfer) {
                setTransferMsgId(feedbackMsgId);
                setShowTransferModal(true);
            }
        } catch {
            message.error('反馈提交失败，请重试');
        }
        setShowFeedbackModal(false);
        setFeedbackReason('');
    };

    // T-11.7: 收藏 Toggle（乐观更新）
    const handleFavorite = async (msgId: string) => {
        const msgs = useChatStore.getState().messages;
        const msg = msgs.find((m: any) => m.id === msgId);
        if (!msg) return;
        const newFav = !msg.isFavorited;
        setMessages(msgs.map((m: any) => m.id === msgId ? { ...m, isFavorited: newFav } : m));
        try {
            const res = await chatService.toggleFavorite(msgId);
            setMessages(useChatStore.getState().messages.map((m: any) =>
                m.id === msgId ? { ...m, isFavorited: res.data?.is_favorited ?? newFav } : m
            ));
        } catch {
            setMessages(useChatStore.getState().messages.map((m: any) =>
                m.id === msgId ? { ...m, isFavorited: msg.isFavorited } : m
            ));
            message.error('操作失败，请重试');
        }
    };

    // T-12.3: 转人工
    const handleTransfer = async (msgId: string) => {
        setTransferLoading(true);
        try {
            await chatService.transferToHuman(msgId);
            setMessages(useChatStore.getState().messages.map((m: any) =>
                m.id === msgId ? { ...m, isTransferred: true } : m
            ));
            message.success('🙋 已转人工，工单已生成');
        } catch (err: any) {
            const status = err?.response?.status;
            const detail = err?.response?.data?.detail;
            if (status === 409) {
                if (typeof detail === 'string') {
                    message.warning(detail);
                } else if (detail?.message) {
                    message.warning(detail.message);
                }
                // 已转人工时也标记状态
                setMessages(useChatStore.getState().messages.map((m: any) =>
                    m.id === msgId ? { ...m, isTransferred: true } : m
                ));
            } else {
                message.error('转人工失败，请重试');
            }
        } finally {
            setTransferLoading(false);
            setShowTransferModal(false);
        }
    };

    // ===== 我的收藏 =====
    const loadFavorites = async () => {
        try {
            const res = await api.get('/favorites');
            const favItems = res.data?.items || [];
            // 加载每个收藏对应的消息内容
            const enriched = [];
            for (const f of favItems) {
                enriched.push({ ...f });
            }
            setFavorites(enriched);
        } catch {
            setFavorites([]);
        }
        setShowFavoritesModal(true);
    };

    const removeFavorite = async (favId: string) => {
        try {
            await api.delete(`/favorites/${favId}`);
            setFavorites(prev => prev.filter(f => f.id !== favId));
            message.success('已取消收藏');
        } catch {
            message.error('操作失败');
        }
    };

    // ===== 意见反馈 =====
    const submitSystemFeedback = async () => {
        if (!sysFeedbackContent.trim()) {
            message.warning('请输入反馈内容');
            return;
        }
        try {
            await api.post('/system-feedback', {
                category: sysFeedbackCategory,
                content: sysFeedbackContent,
                rating: sysFeedbackRating,
            });
            message.success('🎉 感谢您的反馈！');
            setShowSystemFeedbackModal(false);
            setSysFeedbackContent('');
            setSysFeedbackRating(0);
        } catch {
            message.error('提交失败，请重试');
        }
    };

    // ===== 分享 =====
    const handleShare = (msgContent: string) => {
        const shareText = `💬 AI知识助手回答:\n${msgContent}\n\n——来自AI知识库系统`;
        navigator.clipboard.writeText(shareText);
        message.success('📋 回答内容已复制，可粘贴分享');
    };


    const filteredSessions = sessions.filter((s: any) =>
        !searchText || (s.title || '').includes(searchText)
    );

    // ===== 搜索历史 =====
    const searchHistory = async () => {
        if (!searchKeyword.trim()) return;
        setSearchLoading(true);
        try {
            const res = await api.get('/chat/search', { params: { keyword: searchKeyword.trim() } });
            setSearchResults(res.data?.items || []);
        } catch {
            setSearchResults([]);
            message.error('搜索失败');
        } finally { setSearchLoading(false); }
    };

    const SUGGESTIONS = [
        { icon: '📦', text: '退货流程是怎样的？' },
        { icon: '🔧', text: '产品保修期是多久？' },
        { icon: '💰', text: '销售提成如何计算？' },
        { icon: '📋', text: '如何处理客户投诉？' },
    ];

    const FEEDBACK_REASONS = ['答案不准确', '答非所问', '信息过时', '文档质量低', '其他'];

    return (
        <div className="chat-layout" style={{ flex: 1 }}>
            {/* ===== Sidebar ===== */}
            <div className="chat-sidebar">
                <button className="new-chat-btn" onClick={createSession}>+ 新建会话</button>
                <h3>历史会话</h3>
                {/* 搜索 */}
                <div style={{ marginBottom: 12, flexShrink: 0 }}>
                    <input
                        type="text"
                        placeholder="搜索会话..."
                        value={searchText}
                        onChange={e => setSearchText(e.target.value)}
                        style={{
                            width: '100%', padding: '8px 12px', background: 'var(--card2)',
                            border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)',
                            fontSize: 13, outline: 'none', fontFamily: 'inherit',
                        }}
                    />
                </div>
                <div className="chat-list">
                    {filteredSessions.map((s: any) => (
                        <div
                            key={s.id}
                            className={`chat-item ${s.id === currentSessionId ? 'active' : ''}`}
                            onClick={() => selectSession(s.id)}
                        >
                            {s.title || '未命名会话'}
                        </div>
                    ))}
                </div>
                {/* 底部工具 */}
                <div style={{ marginTop: 'auto', paddingTop: 16, borderTop: '1px solid var(--border)', flexShrink: 0 }}>
                    <div className="chat-item" onClick={() => { setShowSearchModal(true); setSearchKeyword(''); setSearchResults([]); }}>🔍 搜索历史</div>
                    <div className="chat-item" onClick={loadFavorites}>⭐ 我的收藏</div>
                    <div className="chat-item" onClick={() => navigate('/help')}>❓ 使用帮助</div>
                    <div className="chat-item" onClick={() => setShowSystemFeedbackModal(true)}>💡 意见反馈</div>
                </div>
            </div>

            {/* ===== Main Area ===== */}
            <div className="chat-main">
                <div className="chat-messages">
                    {messagesLoading ? (
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'var(--text3)' }}>
                            <div style={{ textAlign: 'center' }}>
                                <div className="typing-indicator" style={{ marginBottom: 12 }}><span /><span /><span /></div>
                                <div>加载中...</div>
                            </div>
                        </div>
                    ) : currentSessionId && messages.length > 0 ? (
                        <>
                            {messages.map((m: any) => (
                                <div key={m.id} className={`msg ${m.role === 'user' ? 'user' : 'ai'}`}>
                                    <div className="msg-bubble">
                                        {m.role === 'assistant' ? (
                                            <div className="md-content">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                                            </div>
                                        ) : m.content}
                                    </div>
                                    {m.role === 'assistant' && m.citations && (() => {
                                        // 从 citations 中提取引用信息（RAGFlow reference 数据）
                                        const reference = m.citations?.ragflow_response?.reference || m.citations?.reference || m.citations;
                                        const chunks = reference?.chunks || [];
                                        if (chunks.length === 0) {
                                            if (typeof m.citations === 'string') {
                                                return <div className="msg-source">📄 来源：{m.citations}</div>;
                                            }
                                            return null;
                                        }
                                        // 提取文档名称（去重）
                                        const docNames = [...new Set(chunks.map((c: any) => c.doc_name || c.document_name).filter(Boolean))];
                                        return (
                                            <div className="msg-references">
                                                {/* 引用片段列表 */}
                                                <details className="ref-details">
                                                    <summary className="ref-summary">
                                                        📚 参考来源 ({chunks.length} 个片段)
                                                    </summary>
                                                    <div className="ref-chunks">
                                                        {chunks.slice(0, 5).map((chunk: any, idx: number) => (
                                                            <div key={idx} className="ref-chunk">
                                                                <div className="ref-chunk-header">
                                                                    <span className="ref-tag">[{idx + 1}]</span>
                                                                    <span className="ref-doc-name">{chunk.doc_name || chunk.document_name || '未知文档'}</span>
                                                                    {chunk.similarity && (
                                                                        <span className="ref-score">相似度: {(chunk.similarity * 100).toFixed(0)}%</span>
                                                                    )}
                                                                </div>
                                                                <div className="ref-chunk-content">
                                                                    {(chunk.content || chunk.content_with_weight || '').slice(0, 200)}
                                                                    {(chunk.content || chunk.content_with_weight || '').length > 200 && '...'}
                                                                </div>
                                                            </div>
                                                        ))}
                                                        {chunks.length > 5 && (
                                                            <div className="ref-more">还有 {chunks.length - 5} 个引用片段...</div>
                                                        )}
                                                    </div>
                                                </details>
                                                {/* 文档来源汇总 */}
                                                {docNames.length > 0 && (
                                                    <div className="ref-docs">
                                                        📄 引用文档：{docNames.join('、')}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })()}
                                    {m.role === 'assistant' && (
                                        <div className="msg-actions">
                                            <button
                                                onClick={() => handleFeedbackToggle(m.id, 'like')}
                                                title="点赞"
                                                style={m.feedbackType === 'like' ? { background: 'rgba(99,102,241,0.15)', color: '#6366f1', fontWeight: 600 } : {}}
                                                disabled={m._isStreaming}
                                            >{m.feedbackType === 'like' ? '👍 已赞' : '👍 有用'}</button>
                                            <button
                                                onClick={() => m.feedbackType === 'dislike' ? handleFeedbackToggle(m.id, 'dislike') : handleFeedback(m.id)}
                                                title="点踩"
                                                style={m.feedbackType === 'dislike' ? { background: 'rgba(239,68,68,0.15)', color: '#ef4444', fontWeight: 600 } : {}}
                                                disabled={m._isStreaming}
                                            >{m.feedbackType === 'dislike' ? '👎 已踩' : '👎 无用'}</button>
                                            <button onClick={() => { navigator.clipboard.writeText(m.content); message.success('已复制'); }}>📋 复制</button>
                                            <button onClick={() => handleShare(m.content)}>🔗 分享</button>
                                            <button
                                                onClick={() => handleFavorite(m.id)}
                                                disabled={m._isStreaming}
                                                style={m.isFavorited ? { background: 'rgba(234,179,8,0.15)', color: '#d97706', fontWeight: 600 } : {}}
                                            >{m.isFavorited ? '⭐ 已收藏' : '☆ 收藏'}</button>
                                            <button
                                                onClick={() => handleTransfer(m.id)}
                                                disabled={m._isStreaming || m.isTransferred || transferLoading}
                                                style={m.isTransferred ? { opacity: 0.5 } : {}}
                                            >{m.isTransferred ? '✅ 已转人工' : transferLoading ? '⏳ 转接中...' : '🙋 转人工'}</button>
                                        </div>
                                    )}
                                </div>
                            ))}
                            {isStreaming && streamingContent && (
                                <div className="msg ai">
                                    <div className="msg-bubble">
                                        <div className="md-content">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingContent}</ReactMarkdown>
                                        </div>
                                    </div>
                                </div>
                            )}
                            {isStreaming && !streamingContent && (
                                <div className="msg ai">
                                    <div className="msg-bubble">
                                        <div className="typing-indicator"><span /><span /><span /></div>
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </>
                    ) : (
                        <div className="welcome-box">
                            <h2>你好！有什么可以帮你的？</h2>
                            <p>我是AI知识助手，可以回答你关于业务流程、产品知识等问题</p>
                            <div className="suggest-list">
                                {SUGGESTIONS.map(s => (
                                    <div
                                        key={s.text}
                                        className="suggest-item"
                                        onClick={() => sendMessage(s.text)}
                                    >
                                        {s.icon} {s.text}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* ===== Input Area ===== */}
                <div className="chat-input-area">
                    <div className="chat-input-wrap">
                        <textarea
                            placeholder="输入你的问题..."
                            value={inputText}
                            onChange={e => setInputText(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                        />
                        <button className="send-btn" onClick={() => sendMessage()} title="发送" disabled={isStreaming}>▶</button>
                    </div>
                </div>
            </div>

            {/* ===== Feedback Modal ===== */}
            <div className={`modal-overlay ${showFeedbackModal ? 'show' : ''}`} onClick={e => { if (e.target === e.currentTarget) setShowFeedbackModal(false); }}>
                <div className="modal">
                    <h3>👎 反馈原因</h3>
                    <div className="form-group">
                        <label>请选择原因</label>
                        <div className="feedback-reason-grid">
                            {FEEDBACK_REASONS.map(r => (
                                <button
                                    key={r}
                                    className={`feedback-reason-btn ${feedbackReason === r ? 'active' : ''}`}
                                    onClick={() => setFeedbackReason(r)}
                                >{r}</button>
                            ))}
                        </div>
                    </div>
                    <div className="form-group">
                        <label>补充说明（可选）</label>
                        <textarea rows={3} placeholder="请描述具体问题..." style={{
                            width: '100%', padding: '10px 14px', background: 'var(--card2)',
                            border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)',
                            fontSize: 14, fontFamily: 'inherit', outline: 'none', resize: 'vertical',
                        }} />
                    </div>
                    <div className="modal-actions">
                        <button className="btn btn-outline" onClick={() => setShowFeedbackModal(false)}>取消</button>
                        <button className="btn btn-primary" onClick={submitFeedback}>提交反馈</button>
                    </div>
                </div>
            </div>

            {/* ===== Favorites Modal ===== */}
            <div className={`modal-overlay ${showFavoritesModal ? 'show' : ''}`} onClick={e => { if (e.target === e.currentTarget) setShowFavoritesModal(false); }}>
                <div className="modal" style={{ maxWidth: 600 }}>
                    <h3>⭐ 我的收藏</h3>
                    {favorites.length === 0 ? (
                        <p style={{ color: 'var(--text3)', textAlign: 'center', padding: '30px 0' }}>暂无收藏内容，可在对话中点击 ⭐ 收藏有用的回答</p>
                    ) : (
                        <div style={{ maxHeight: 450, overflowY: 'auto' }}>
                            {favorites.map(f => (
                                <div key={f.id} style={{
                                    padding: '14px 16px', borderBottom: '1px solid var(--border)',
                                    cursor: 'pointer', borderRadius: 8, transition: 'background 0.15s',
                                }}
                                    onClick={() => { selectSession(f.session_id); setShowFavoritesModal(false); }}
                                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--card2)')}
                                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                                >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                            <span style={{
                                                fontSize: 11, padding: '2px 8px', borderRadius: 4, fontWeight: 600,
                                                background: f.role === 'user' ? 'rgba(99,102,241,0.15)' : 'rgba(16,185,129,0.15)',
                                                color: f.role === 'user' ? '#6366f1' : '#10b981',
                                            }}>
                                                {f.role === 'user' ? '👤 用户' : '🤖 AI'}
                                            </span>
                                            <span style={{ fontSize: 11, color: 'var(--text3)' }}>
                                                {formatTime(f.msg_created_at || f.created_at)}
                                            </span>
                                        </div>
                                        <button
                                            className="btn btn-outline"
                                            style={{ fontSize: 11, padding: '2px 10px', flexShrink: 0 }}
                                            onClick={e => { e.stopPropagation(); removeFavorite(f.id); }}
                                        >✕ 取消收藏</button>
                                    </div>
                                    <div style={{
                                        fontSize: 13, color: 'var(--text)', lineHeight: 1.6,
                                        overflow: 'hidden', display: '-webkit-box',
                                        WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' as any,
                                    }}>
                                        {f.content || '(消息内容已删除)'}
                                    </div>
                                    <div style={{ fontSize: 11, color: 'var(--primary)', marginTop: 6, opacity: 0.7 }}>
                                        点击查看原始对话 →
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                    <div className="modal-actions">
                        <button className="btn btn-outline" onClick={() => setShowFavoritesModal(false)}>关闭</button>
                    </div>
                </div>
            </div>



            {/* ===== Transfer Suggestion Modal (3 踩建议转人工) ===== */}
            <div className={`modal-overlay ${showTransferModal ? 'show' : ''}`} onClick={e => { if (e.target === e.currentTarget) setShowTransferModal(false); }}>
                <div className="modal" style={{ maxWidth: 400 }}>
                    <h3>🙋 建议转人工</h3>
                    <p style={{ color: 'var(--text2)', lineHeight: 1.6, margin: '12px 0' }}>
                        检测到多次负面反馈，建议将此问题转给人工客服处理，以获得更好的解答。
                    </p>
                    <div className="modal-actions">
                        <button className="btn btn-outline" onClick={() => setShowTransferModal(false)}>暂不需要</button>
                        <button className="btn btn-primary" onClick={() => handleTransfer(transferMsgId)}>
                            {transferLoading ? '⏳ 转接中...' : '确认转人工'}
                        </button>
                    </div>
                </div>
            </div>

            {/* ===== System Feedback Modal ===== */}
            <div className={`modal-overlay ${showSystemFeedbackModal ? 'show' : ''}`} onClick={e => { if (e.target === e.currentTarget) setShowSystemFeedbackModal(false); }}>
                <div className="modal" style={{ maxWidth: 480 }}>
                    <h3>💡 意见反馈</h3>
                    <div className="form-group">
                        <label>反馈类型</label>
                        <div style={{ display: 'flex', gap: 8 }}>
                            {['功能建议', 'Bug反馈', '体验评价'].map(c => (
                                <button
                                    key={c}
                                    className={`feedback-reason-btn ${sysFeedbackCategory === c ? 'active' : ''}`}
                                    onClick={() => setSysFeedbackCategory(c)}
                                >{c}</button>
                            ))}
                        </div>
                    </div>
                    <div className="form-group">
                        <label>评分</label>
                        <div style={{ display: 'flex', gap: 4, fontSize: 22 }}>
                            {[1, 2, 3, 4, 5].map(n => (
                                <span
                                    key={n}
                                    onClick={() => setSysFeedbackRating(n)}
                                    style={{ cursor: 'pointer', opacity: n <= sysFeedbackRating ? 1 : 0.3, transition: 'opacity 0.2s' }}
                                >{n <= sysFeedbackRating ? '⭐' : '☆'}</span>
                            ))}
                        </div>
                    </div>
                    <div className="form-group">
                        <label>反馈内容</label>
                        <textarea
                            rows={4}
                            placeholder="请详细描述您的建议或遇到的问题..."
                            value={sysFeedbackContent}
                            onChange={e => setSysFeedbackContent(e.target.value)}
                            style={{
                                width: '100%', padding: '10px 14px', background: 'var(--card2)',
                                border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)',
                                fontSize: 14, fontFamily: 'inherit', outline: 'none', resize: 'vertical',
                            }}
                        />
                    </div>
                    <div className="modal-actions">
                        <button className="btn btn-outline" onClick={() => setShowSystemFeedbackModal(false)}>取消</button>
                        <button className="btn btn-primary" onClick={submitSystemFeedback}>提交反馈</button>
                    </div>
                </div>
            </div>

            {/* ===== Search History Modal ===== */}
            <div className={`modal-overlay ${showSearchModal ? 'show' : ''}`} onClick={e => { if (e.target === e.currentTarget) setShowSearchModal(false); }}>
                <div className="modal" style={{ maxWidth: 600 }}>
                    <h3>🔍 搜索历史对话</h3>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
                        <input
                            type="text"
                            placeholder="输入关键词搜索所有对话记录..."
                            value={searchKeyword}
                            onChange={e => setSearchKeyword(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') searchHistory(); }}
                            style={{
                                flex: 1, padding: '10px 14px', background: 'var(--card2)',
                                border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)',
                                fontSize: 14, fontFamily: 'inherit', outline: 'none',
                            }}
                            autoFocus
                        />
                        <button className="btn btn-primary" onClick={searchHistory}
                            style={{ padding: '10px 20px', flexShrink: 0 }}>
                            {searchLoading ? '⏳' : '🔍'} 搜索
                        </button>
                    </div>
                    {searchResults.length > 0 ? (
                        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                            {searchResults.map((r: any) => (
                                <div key={r.id} style={{
                                    padding: '12px 14px', borderBottom: '1px solid var(--border)',
                                    cursor: 'pointer', borderRadius: 8,
                                    transition: 'background 0.15s',
                                }} onClick={async () => {
                                    setShowSearchModal(false);
                                    // 确保会话在侧边栏中可见
                                    const sessionExists = sessions.some((s: any) => s.id === r.session_id);
                                    if (!sessionExists) {
                                        // 刷新会话列表（搜索结果可能来自未加载的旧会话）
                                        try {
                                            const res = await chatService.listSessions();
                                            setSessions(res.data?.items || []);
                                        } catch { }
                                    }
                                    selectSession(r.session_id);
                                }}
                                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--card2)')}
                                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                                        <span style={{
                                            fontSize: 11, padding: '2px 8px', borderRadius: 4, fontWeight: 600,
                                            background: r.role === 'user' ? 'rgba(99,102,241,0.15)' : 'rgba(16,185,129,0.15)',
                                            color: r.role === 'user' ? '#6366f1' : '#10b981',
                                        }}>
                                            {r.role === 'user' ? '👤 用户' : '🤖 AI'}
                                        </span>
                                        <span style={{ fontSize: 11, color: 'var(--text3)' }}>
                                            {formatTime(r.created_at)}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.5 }}>
                                        {(() => {
                                            const text = r.content.length > 200 ? r.content.slice(0, 200) + '...' : r.content;
                                            const kw = searchKeyword.trim();
                                            if (!kw) return text;
                                            const parts = text.split(new RegExp(`(${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
                                            return parts.map((part: string, i: number) =>
                                                part.toLowerCase() === kw.toLowerCase()
                                                    ? <mark key={i} style={{ background: '#fbbf24', color: '#000', padding: '0 2px', borderRadius: 2 }}>{part}</mark>
                                                    : part
                                            );
                                        })()}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : searchKeyword && !searchLoading ? (
                        <p style={{ color: 'var(--text3)', textAlign: 'center', padding: '30px 0' }}>没有找到匹配的对话记录</p>
                    ) : !searchKeyword ? (
                        <p style={{ color: 'var(--text3)', textAlign: 'center', padding: '30px 0' }}>输入关键词后点击搜索</p>
                    ) : null}
                    <div className="modal-actions">
                        <button className="btn btn-outline" onClick={() => setShowSearchModal(false)}>关闭</button>
                    </div>
                </div>
            </div>
        </div>
    );
}

