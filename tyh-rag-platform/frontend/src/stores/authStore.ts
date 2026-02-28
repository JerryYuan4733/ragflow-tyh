/**
 * 认证状态管理 - Zustand Store
 * 同时持久化 token 和 user 到 localStorage
 */

import { create } from 'zustand';
import api from '../services/api';

interface User {
    id: string;
    username: string;
    displayName: string;
    role: 'user' | 'kb_admin' | 'it_admin';
    activeTeamId: string | null;
    activeTeamName: string | null;
}

interface AuthState {
    token: string | null;
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    setAuth: (token: string, user: User) => void;
    clearAuth: () => void;
    logout: () => void;
    restoreUser: () => Promise<void>;
}

/** 从 localStorage 读取持久化的 user */
function loadUser(): User | null {
    try {
        const raw = localStorage.getItem('user');
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

const clearFn = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    return { token: null, user: null, isAuthenticated: false, isLoading: false } as Partial<AuthState>;
};

export const useAuthStore = create<AuthState>((set, get) => ({
    token: localStorage.getItem('token'),
    user: loadUser(),
    isAuthenticated: !!localStorage.getItem('token'),
    isLoading: false,

    setAuth: (token: string, user: User) => {
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
        set({ token, user, isAuthenticated: true });
    },

    clearAuth: () => set(clearFn),
    logout: () => set(clearFn),

    /** 启动时从 /auth/me 恢复用户信息（用于 localStorage 丢失但 token 还在的场景） */
    restoreUser: async () => {
        const { token, user } = get();
        if (!token) return;
        if (user) return; // 已有用户数据，无需恢复

        set({ isLoading: true });
        try {
            const res = await api.get('/auth/me');
            const data = res.data;
            const restored: User = {
                id: data.id,
                username: data.username,
                displayName: data.display_name,
                role: data.role,
                activeTeamId: data.active_team_id,
                activeTeamName: data.active_team_name,
            };
            localStorage.setItem('user', JSON.stringify(restored));
            set({ user: restored, isLoading: false });
        } catch {
            // token 无效，清除认证
            set(clearFn);
        }
    },
}));
