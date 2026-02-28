/**
 * 时间格式化工具 — 统一将 UTC 时间转换为北京时间显示
 *
 * 格式: YYYY-MM-DD HH:mm:ss (UTC+8)
 */

const BEIJING_OFFSET_MS = 8 * 60 * 60 * 1000;

/**
 * 将 ISO/UTC 时间字符串格式化为北京时间
 * @param value ISO 时间字符串，例如 "2026-02-26T02:25:26"
 * @param fallback 无效值时的默认显示
 * @returns "2026-02-26 10:25:26"
 */
export function formatTime(value: string | null | undefined, fallback = '-'): string {
    if (!value) return fallback;
    try {
        const date = new Date(value);
        if (isNaN(date.getTime())) return fallback;

        // 转为北京时间：UTC 毫秒 + 8 小时偏移
        const beijing = new Date(date.getTime() + BEIJING_OFFSET_MS);

        const y = beijing.getUTCFullYear();
        const m = String(beijing.getUTCMonth() + 1).padStart(2, '0');
        const d = String(beijing.getUTCDate()).padStart(2, '0');
        const hh = String(beijing.getUTCHours()).padStart(2, '0');
        const mm = String(beijing.getUTCMinutes()).padStart(2, '0');
        const ss = String(beijing.getUTCSeconds()).padStart(2, '0');

        return `${y}-${m}-${d} ${hh}:${mm}:${ss}`;
    } catch {
        return fallback;
    }
}
