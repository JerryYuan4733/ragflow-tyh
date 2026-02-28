/**
 * Chat Store - Zustand (T-040)
 */
import { create } from 'zustand';

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: any;
    created_at?: string;
    feedbackType?: 'like' | 'dislike' | null;
    isFavorited?: boolean;
    isTransferred?: boolean;
    _isStreaming?: boolean;
}

interface ChatSession {
    id: string;
    title: string;
    created_at: string;
}

interface ChatState {
    sessions: ChatSession[];
    currentSessionId: string | null;
    messages: Message[];
    isStreaming: boolean;
    streamingContent: string;
    setSessions: (sessions: ChatSession[]) => void;
    setCurrentSession: (id: string | null) => void;
    setMessages: (messages: Message[]) => void;
    addMessage: (message: Message) => void;
    setIsStreaming: (v: boolean) => void;
    setStreamingContent: (content: string) => void;
    appendStreamingContent: (chunk: string) => void;
    reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
    sessions: [],
    currentSessionId: null,
    messages: [],
    isStreaming: false,
    streamingContent: '',
    setSessions: (sessions) => set({ sessions }),
    setCurrentSession: (id) => set({ currentSessionId: id, messages: [], streamingContent: '' }),
    setMessages: (messages) => set({ messages }),
    addMessage: (message) => set((s) => ({ messages: [...s.messages, message] })),
    setIsStreaming: (v) => set({ isStreaming: v }),
    setStreamingContent: (content) => set({ streamingContent: content }),
    appendStreamingContent: (chunk) => set((s) => ({ streamingContent: s.streamingContent + chunk })),
    reset: () => set({ sessions: [], currentSessionId: null, messages: [], streamingContent: '' }),
}));
