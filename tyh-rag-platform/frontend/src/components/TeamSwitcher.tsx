/**
 * 团队切换器组件 - 顶部导航栏内嵌
 * 显示当前活跃团队，点击展开下拉菜单切换团队
 */

import { useEffect } from 'react';
import { Dropdown, message } from 'antd';
import type { MenuProps } from 'antd';
import { useTeamStore } from '../stores/teamStore';
import { useAuthStore } from '../stores/authStore';

export default function TeamSwitcher() {
    const { user } = useAuthStore();
    const { myTeams, loading, switching, fetchMyTeams, switchActiveTeam } = useTeamStore();

    useEffect(() => {
        fetchMyTeams();
    }, [fetchMyTeams]);

    const handleSwitch = async (teamId: string) => {
        if (teamId === user?.activeTeamId) return;
        const ok = await switchActiveTeam(teamId);
        if (ok) {
            message.success('团队切换成功，页面数据已刷新');
            // 刷新页面数据（简单方案：重新加载当前页面）
            window.location.reload();
        } else {
            message.error('团队切换失败');
        }
    };

    const menuItems: MenuProps['items'] = myTeams.map((t) => ({
        key: t.team_id,
        label: (
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {t.is_active && <span style={{ color: '#1890ff' }}>✓</span>}
                <span>{t.team_name}</span>
                {t.is_default && (
                    <span style={{ fontSize: 11, color: '#999', marginLeft: 4 }}>默认</span>
                )}
            </span>
        ),
        disabled: switching,
        onClick: () => handleSwitch(t.team_id),
    }));

    // 只有一个团队时不显示切换器
    if (myTeams.length <= 1 && !loading) {
        return (
            <span
                className="team-switcher"
                style={{ fontSize: 13, color: 'var(--text2)', cursor: 'default' }}
                title="当前团队"
            >
                🏢 {user?.activeTeamName || '未分配团队'}
            </span>
        );
    }

    return (
        <Dropdown
            menu={{ items: menuItems }}
            trigger={['click']}
            placement="bottomRight"
        >
            <span
                className="team-switcher"
                style={{
                    fontSize: 13,
                    color: 'var(--primary)',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                }}
                title="点击切换团队"
            >
                🏢 {user?.activeTeamName || '未分配团队'} ▾
            </span>
        </Dropdown>
    );
}
