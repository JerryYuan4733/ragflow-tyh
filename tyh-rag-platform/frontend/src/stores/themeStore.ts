import { create } from 'zustand';

interface ThemeState {
    isDark: boolean;
    toggleTheme: () => void;
    setTheme: (isDark: boolean) => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
    isDark: localStorage.getItem('theme') === 'dark',
    toggleTheme: () =>
        set((state) => {
            const newIsDark = !state.isDark;
            localStorage.setItem('theme', newIsDark ? 'dark' : 'light');
            document.documentElement.setAttribute('data-theme', newIsDark ? 'dark' : 'light');
            return { isDark: newIsDark };
        }),
    setTheme: (isDark: boolean) => {
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        set({ isDark });
    },
}));
