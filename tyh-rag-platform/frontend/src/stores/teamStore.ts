/**
 * 团队状态管理 - Zustand Store
 * 管理当前用户的团队列表、活跃团队切换
 */

import { create } from 'zustand';
import { getMyTeams, switchTeam } from '../services/teamService';
import type { MyTeamItem } from '../types/team';
import { useAuthStore } from './authStore';

interface TeamState {
    /** 用户所属团队列表 */
    myTeams: MyTeamItem[];
    /** 是否正在加载 */
    loading: boolean;
    /** 是否正在切换团队 */
    switching: boolean;
    /** 加载用户所属团队列表 */
    fetchMyTeams: () => Promise<void>;
    /** 切换活跃团队 */
    switchActiveTeam: (teamId: string) => Promise<boolean>;
}

export const useTeamStore = create<TeamState>((set, get) => ({
    myTeams: [],
    loading: false,
    switching: false,

    fetchMyTeams: async () => {
        set({ loading: true });
        try {
            const data = await getMyTeams();
            set({ myTeams: data.items, loading: false });
        } catch {
            set({ loading: false });
        }
    },

    switchActiveTeam: async (teamId: string) => {
        set({ switching: true });
        try {
            const result = await switchTeam(teamId);

            // 更新本地团队列表的 is_active 状态
            const updated = get().myTeams.map((t) => ({
                ...t,
                is_active: t.team_id === teamId,
            }));
            set({ myTeams: updated, switching: false });

            // 同步更新 authStore 中的用户信息
            const authStore = useAuthStore.getState();
            if (authStore.user) {
                const updatedUser = {
                    ...authStore.user,
                    activeTeamId: result.active_team_id,
                    activeTeamName: result.active_team_name,
                };
                authStore.setAuth(authStore.token!, updatedUser);
            }

            return true;
        } catch {
            set({ switching: false });
            return false;
        }
    },
}));
