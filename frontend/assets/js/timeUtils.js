/**
 * Time Utility Functions
 * Provides consistent time formatting across all pages
 * All times are displayed in user's local timezone
 * Date format: Jan 23, 2026 (US standard)
 * Time format: 02:30 PM (12-hour clock, US standard)
 */

const TimeUtils = {
    /**
     * Format date in standard US format: Jan 23, 2026
     * @param {string|Date} dateInput - Date string or Date object
     * @returns {string} Formatted date
     */
    formatDate(dateInput) {
        if (!dateInput) return '—';
        const date = new Date(dateInput);
        if (isNaN(date.getTime())) return '—';
        return date.toLocaleDateString({ month: 'short', day: 'numeric', year: 'numeric' });
    },

    /**
     * Format time in standard US format: 02:30 PM
     * @param {string|Date} dateInput - Date string or Date object
     * @returns {string} Formatted time
     */
    formatTime(dateInput) {
        if (!dateInput) return '—';
        const date = new Date(dateInput);
        if (isNaN(date.getTime())) return '—';
        return date.toLocaleTimeString({ hour: '2-digit', minute: '2-digit' });
    },

    /**
     * Format date and time combined: Jan 23, 2026 02:30 PM
     * @param {string|Date} dateInput - Date string or Date object
     * @returns {string} Formatted date and time
     */
    formatDateTime(dateInput) {
        if (!dateInput) return '—';
        const date = new Date(dateInput);
        if (isNaN(date.getTime())) return '—';
        const dateStr = date.toLocaleDateString({ month: 'short', day: 'numeric', year: 'numeric' });
        const timeStr = date.toLocaleTimeString({ hour: '2-digit', minute: '2-digit' });
        return `${dateStr} ${timeStr}`;
    },

    /**
     * Format relative time: Just now, 5 min ago, 2 hours ago, 3 days ago
     * @param {string|Date} dateInput - Date string or Date object
     * @returns {string} Relative time string
     */
    formatRelativeTime(dateInput) {
        if (!dateInput) return '—';
        const date = new Date(dateInput);
        if (isNaN(date.getTime())) return '—';
        
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        else if (diffMins < 60) return `${diffMins} min ago`;
        else if (diffHours < 24) return `${diffHours} hour ago`;
        else return `${diffDays} day ago`;
    },

    /**
     * Format date for greeting: Friday, January 23, 2026
     * @param {string|Date} dateInput - Date string or Date object
     * @returns {string} Formatted date with weekday
     */
    formatGreetingDate(dateInput) {
        if (!dateInput) return '—';
        const date = dateInput instanceof Date ? dateInput : new Date(dateInput);
        if (isNaN(date.getTime())) return '—';
        return date.toLocaleDateString({ weekday: 'long', month: 'long', day: 'numeric' });
    },

    /**
     * Format time in UTC format for admin views: 14:30:45 UTC
     * @param {string|Date} dateInput - Date string or Date object
     * @returns {string} Formatted UTC time
     */
    formatTimeUTC(dateInput) {
        if (!dateInput) return '—';
        const date = new Date(dateInput);
        if (isNaN(date.getTime())) return '—';
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) + ' UTC';
    },

    /**
     * Format date and time in UTC format for admin views
     * @param {string|Date} dateInput - Date string or Date object
     * @returns {string} Formatted UTC date and time
     */
    formatDateTimeUTC(dateInput) {
        if (!dateInput) return '—';
        const date = new Date(dateInput);
        if (isNaN(date.getTime())) return '—';
        const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
        return `${dateStr} ${timeStr} UTC`;
    }
};
