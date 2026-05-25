# 1. Complete File Tree of Frontend
```text
frontend/404.html
frontend/assets/css/public.css
frontend/assets/css/style.css
frontend/assets/css/theme.css
frontend/assets/images/logo.svg
frontend/assets/js/api.js
frontend/assets/js/auth.js
frontend/assets/js/main.js
frontend/assets/js/notifications-ui.js
frontend/assets/js/public.js
frontend/assets/js/receiptModal.js
frontend/assets/js/theme.js
frontend/assets/js/timeUtils.js
frontend/assets/js/utils.js
frontend/index.html
frontend/pages/about.html
frontend/pages/admin/admin-dashboard.html
frontend/pages/admin/codes.html
frontend/pages/admin/dashboard.html
frontend/pages/admin/js/codes.js
frontend/pages/admin/js/dashboard.js
frontend/pages/admin/js/transactions.js
frontend/pages/admin/js/users.js
frontend/pages/admin-login.html
frontend/pages/admin/settings.html
frontend/pages/admin/transactions.html
frontend/pages/admin/users.html
frontend/pages/business-banking.html
frontend/pages/contact.html
frontend/pages/enter-pin.html
frontend/pages/forgot-password.html
frontend/pages/forgot-pin.html
frontend/pages/loans.html
frontend/pages/login.html
frontend/pages/personal-banking.html
frontend/pages/privacy.html
frontend/pages/register.html
frontend/pages/resend-verification.html
frontend/pages/reset-password.html
frontend/pages/reset-pin.html
frontend/pages/set-pin.html
frontend/pages/super-admin/admins.html
frontend/pages/super-admin/dashboard.html
frontend/pages/super-admin/js/admins.js
frontend/pages/super-admin/js/dashboard.js
frontend/pages/terms.html
frontend/pages/user/cards.html
frontend/pages/user/dashboard.html
frontend/pages/user/js/dashboard.js
frontend/pages/user/js/notification.js
frontend/pages/user/js/profile.js
frontend/pages/user/js/transactions.js
frontend/pages/user/js/transfer.js
frontend/pages/user/loans.html
frontend/pages/user/notifications.html
frontend/pages/user/profile.html
frontend/pages/user/support.html
frontend/pages/user/transactions.html
frontend/pages/user/transfer.html
frontend/pages/verify-email.html
frontend/pages/wealth-management.html
frontend/vercel.json
```

# 2. Complete contents of /frontend/pages/admin/admin-dashboard.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard — Arcteron Trust Admin</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../../assets/css/theme.css">
    <link rel="stylesheet" href="../../assets/css/style.css">
    <script src="../../assets/js/theme.js"></script>
    <style>
        body {
            font-family: 'DM Sans', sans-serif;
            margin: 0;
        }

        .layout {
            display: flex;
            min-height: 100vh;
        }

        /* ── Sidebar ── */
        .sidebar {
            width: 260px;
            background: #171A20;
            border-right: none;
            display: flex;
            flex-direction: column;
            position: fixed;
            top: 0;
            left: 0;
            height: 100vh;
            z-index: 300;
            transition: transform 0.3s ease;
        }

        [data-theme="light"] .sidebar {
            background: #171A20;
            border-right: none;
        }

        .sidebar-logo {
            padding: 0 20px;
            height: 60px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
        }

        [data-theme="light"] .sidebar-logo {
            border-bottom-color: rgba(255, 255, 255, 0.08);
        }

        .sidebar-logo-icon {
            width: 28px;
            height: 28px;
            flex-shrink: 0;
            opacity: 0.8;
            color: currentColor;
        }

        [data-theme="light"] .sidebar-logo-icon {
            opacity: 1;
            color: #ffffff;
        }

        .sidebar-logo-text h1 {
            font-family: 'Cormorant Garamond', serif;
            font-size: 16px;
            font-weight: 600;
            color: #ffffff;
            line-height: 1.2;
            margin: 0;
        }

        .sidebar-logo-text p {
            font-size: 9px;
            color: rgba(255, 255, 255, 0.3);
            margin-top: 1px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        .sidebar-nav {
            padding: 10px 10px;
            flex: 1;
            overflow-y: auto;
        }

        .nav-section-label {
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.25);
            padding: 10px 10px 4px;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.5);
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 1px;
            text-decoration: none;
        }

        .nav-item:hover {
            background: rgba(255, 255, 255, 0.07);
            color: rgba(255, 255, 255, 0.85);
        }

        .nav-item.active {
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            font-weight: 600;
        }

        .nav-item svg {
            width: 16px;
            height: 16px;
            flex-shrink: 0;
        }

        .nav-item.danger {
            color: rgba(239, 68, 68, 0.7);
        }

        .nav-item.danger:hover {
            background: rgba(239, 68, 68, 0.1);
            color: #EF4444;
        }

        .sidebar-footer {
            padding: 12px 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        }

        .user-card {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
            margin-bottom: 4px;
        }

        .user-card:hover {
            background: rgba(255, 255, 255, 0.07);
        }

        .sidebar-avatar {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.12);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            flex-shrink: 0;
            font-family: 'Cormorant Garamond', serif;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }

        .user-name {
            font-size: 13px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.85);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .user-role {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.3);
        }

        /* ── Main ── */
        .main-content {
            margin-left: 260px;
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            background: var(--bg-primary);
        }

        /* ── Topbar ── */
        .topbar {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            padding: 0 28px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 200;
            flex-shrink: 0;
        }

        .topbar-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .menu-btn {
            display: none;
            width: 36px;
            height: 36px;
            border-radius: 8px;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            align-items: center;
            justify-content: center;
            cursor: pointer;
            color: var(--text-secondary);
            flex-shrink: 0;
        }

        .topbar-title {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .topbar-right {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .icon-btn {
            width: 36px;
            height: 36px;
            border-radius: 8px;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            color: var(--text-secondary);
            transition: all 0.2s;
            position: relative;
            text-decoration: none;
        }

        .icon-btn:hover {
            color: var(--text-primary);
        }

        /* ── Page content ── */
        .page-content {
            padding: 28px;
            flex: 1;
        }

        /* ── Stats ── */
        .stats-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
        }

        .stat-card-label {
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .stat-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .stat-card-value {
            font-family: 'Cormorant Garamond', serif;
            font-size: 22px;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1;
            margin-bottom: 3px;
        }

        .stat-card-sub {
            font-size: 11px;
            color: var(--text-muted);
        }

        /* ── Quick Actions ── */
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }

        .quick-action-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .quick-action-card:hover {
            border-color: var(--text-primary);
        }

        .quick-action-card h4 {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 4px;
            color: var(--text-primary);
        }

        .quick-action-card p {
            font-size: 13px;
            color: var(--text-secondary);
        }

        /* ── Recent Activity ── */
        .recent-activity {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
        }

        .recent-activity h2 {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text-primary);
        }

        .activity-item {
            display: flex;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid var(--border-color);
        }

        .activity-item:last-child {
            border-bottom: none;
        }

        .activity-icon {
            width: 40px;
            height: 40px;
            border-radius: 8px;
            background: rgba(15, 17, 21, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 16px;
            flex-shrink: 0;
        }

        .activity-icon svg {
            width: 20px;
            height: 20px;
        }

        .activity-details {
            flex: 1;
        }

        .activity-details h4 {
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 2px;
            color: var(--text-primary);
        }

        .activity-details p {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .activity-time {
            font-size: 12px;
            color: var(--text-muted);
        }

        .btn {
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            border: none;
            transition: opacity 0.2s;
        }

        .btn:hover {
            opacity: 0.85;
        }

        .btn-primary {
            background: #0F1115;
            color: #fff;
        }

        .btn-secondary {
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }

        /* Overlay */
        .sidebar-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.6);
            z-index: 299;
            backdrop-filter: blur(2px);
        }

        .sidebar-overlay.show {
            display: block;
        }

        /* ── Responsive ── */
        @media (max-width: 900px) {
            .sidebar {
                transform: translateX(-260px);
            }

            .sidebar.open {
                transform: translateX(0);
                box-shadow: 4px 0 24px rgba(0, 0, 0, 0.4);
            }

            .main-content {
                margin-left: 0;
            }

            .menu-btn {
                display: flex;
            }

            .page-content {
                padding: 16px;
            }

            .topbar {
                padding: 0 16px;
                height: 56px;
            }

            .topbar-right {
                gap: 6px;
            }

            .btn {
                padding: 8px 10px;
                font-size: 12px;
            }

            .btn-secondary {
                display: none;
            }

            .btn-primary span {
                display: none;
            }

            .icon-btn {
                width: 32px;
                height: 32px;
            }

            .stats-row {
                grid-template-columns: 1fr 1fr;
            }

            .quick-actions {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 480px) {
            .stats-row {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>

<body>
    <div class="layout">
        <aside class="sidebar">
            <div class="sidebar-logo">
                <svg class="sidebar-logo-icon" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="20" cy="20" r="18" stroke="currentColor" stroke-width="2" opacity="0.4" />
                    <path d="M20 8 L30 28 H24 L20 20 L16 28 H10 Z" fill="currentColor" opacity="0.9" />
                    <path d="M14 23 H26" stroke="currentColor" stroke-width="2" opacity="0.8" />
                    <circle cx="20" cy="6" r="2" fill="currentColor" opacity="0.6" />
                </svg>
                <div class="sidebar-logo-text">
                    <h1>Arcteron Trust</h1>
                    <p>Admin Portal</p>
                </div>
            </div>
            <nav class="sidebar-nav">
                <div class="nav-section-label">Main</div>
                <a class="nav-item active" href="admin-dashboard.html">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="7" height="7"></rect>
                        <rect x="14" y="3" width="7" height="7"></rect>
                        <rect x="14" y="14" width="7" height="7"></rect>
                        <rect x="3" y="14" width="7" height="7"></rect>
                    </svg>
                    Dashboard
                </a>
                <a class="nav-item" href="users.html">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                        <circle cx="9" cy="7" r="4"></circle>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                    </svg>
                    Users
                </a>
                <a class="nav-item" href="transactions.html">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="1" x2="12" y2="23"></line>
                        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                    </svg>
                    Transactions
                </a>
                <a class="nav-item" href="codes.html">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                    </svg>
                    COT/BOP Codes
                </a>
                <div class="nav-section-label">Account</div>
                <a class="nav-item danger" onclick="logout()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                        <polyline points="16 17 21 12 16 7"></polyline>
                        <line x1="21" y1="12" x2="9" y2="12"></line>
                    </svg>
                    Logout
                </a>
            </nav>
            <div class="sidebar-footer">
                <div class="user-card">
                    <div class="sidebar-avatar">A</div>
                    <div>
                        <div class="user-name">Admin</div>
                        <div class="user-role">Administrator</div>
                    </div>
                </div>
            </div>
        </aside>

        <div class="sidebar-overlay" onclick="toggleSidebar()"></div>

        <main class="main-content">
            <div class="topbar">
                <div class="topbar-left">
                    <button class="menu-btn" onclick="toggleSidebar()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="3" y1="12" x2="21" y2="12"></line>
                            <line x1="3" y1="6" x2="21" y2="6"></line>
                            <line x1="3" y1="18" x2="21" y2="18"></line>
                        </svg>
                    </button>
                    <div class="topbar-title">Dashboard</div>
                </div>
                <div class="topbar-right">
                    <a class="icon-btn" id="themeToggle" onclick="Theme.toggle()" title="Toggle Theme">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                        </svg>
                    </a>
                    <button class="btn btn-secondary" onclick="refreshData()">Refresh</button>
                    <button class="btn btn-primary" onclick="navigate('users')">Manage Users</button>
                </div>
            </div>

            <div class="page-content">
                <div class="stats-row">
                    <div class="stat-card">
                        <div class="stat-card-label">
                            <div class="stat-dot" style="background: #10B981;"></div>
                            Total Users
                        </div>
                        <div class="stat-card-value" id="totalUsers">-</div>
                        <div class="stat-card-sub">Active accounts</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">
                            <div class="stat-dot" style="background: #3B82F6;"></div>
                            Total Balance
                        </div>
                        <div class="stat-card-value" id="totalBalance">-</div>
                        <div class="stat-card-sub">Across all accounts</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">
                            <div class="stat-dot" style="background: #EF4444;"></div>
                            Blocked Users
                        </div>
                        <div class="stat-card-value" id="blockedUsers">-</div>
                        <div class="stat-card-sub">Require attention</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">
                            <div class="stat-dot" style="background: #10B981;"></div>
                            Active Users
                        </div>
                        <div class="stat-card-value" id="activeUsers">-</div>
                        <div class="stat-card-sub">Can transact</div>
                    </div>
                </div>

                <div class="quick-actions">
                    <div class="quick-action-card" onclick="navigate('users')">
                        <h4>Create User</h4>
                        <p>Add a new user to the system</p>
                    </div>
                    <div class="quick-action-card" onclick="navigate('users')">
                        <h4>Credit Account</h4>
                        <p>Manual credit to user account</p>
                    </div>
                    <div class="quick-action-card" onclick="navigate('users')">
                        <h4>Block User</h4>
                        <p>Restrict user account access</p>
                    </div>
                </div>

                <div class="recent-activity">
                    <h2>Recent Activity</h2>
                    <div id="activityList">
                        <div class="activity-item">
                            <div class="activity-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <polyline points="12 6 12 12 16 14"></polyline>
                                </svg>
                            </div>
                            <div class="activity-details">
                                <h4>System initialized</h4>
                                <p>Admin dashboard loaded</p>
                            </div>
                            <div class="activity-time" id="systemInitTime">Just now</div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        const API_BASE = 'https://arcteron-trust.onrender.com';

        // Check authentication
        function checkAuth() {
            const token = localStorage.getItem('admin_token');
            if (!token) {
                window.location.href = '../admin-login.html';
                return false;
            }

            // Set dynamic admin name
            const userJson = localStorage.getItem('admin_user');
            if (userJson) {
                try {
                    const user = JSON.parse(userJson);
                    const userCard = document.querySelector('.user-name');
                    if (userCard) {
                        userCard.textContent = `${user.first_name} ${user.last_name}`;
                    }
                } catch (e) { }
            }

            // Set system initialization time
            setSystemInitTime();

            return true;
        }

        // Set system initialization time
        function setSystemInitTime() {
            const now = new Date();
            const timeElement = document.getElementById('systemInitTime');
            if (timeElement) {
                timeElement.textContent = formatTimeAgo(now);
            }
        }

        // Format time as "X minutes ago" or "Just now"
        function formatTimeAgo(date) {
            const now = new Date();
            const diff = now - date;
            const minutes = Math.floor(diff / 60000);

            if (minutes < 1) {
                return 'Just now';
            } else if (minutes === 1) {
                return '1 minute ago';
            } else if (minutes < 60) {
                return `${minutes} minutes ago`;
            } else {
                const hours = Math.floor(minutes / 60);
                if (hours === 1) {
                    return '1 hour ago';
                } else {
                    return `${hours} hours ago`;
                }
            }
        }

        // Toggle sidebar
        function toggleSidebar() {
            const sidebar = document.querySelector('.sidebar');
            const overlay = document.querySelector('.sidebar-overlay');
            sidebar.classList.toggle('open');
            overlay.classList.toggle('show');
        }

        // Load dashboard stats
        async function loadStats() {
            try {
                const token = localStorage.getItem('admin_token');
                const response = await fetch(`${API_BASE}/api/admin/users?page=1&per_page=1000`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    const users = data.users;

                    // Calculate stats
                    const totalUsers = users.length;
                    const totalBalance = users.reduce((sum, user) => sum + user.balance, 0);
                    const blockedUsers = users.filter(u => u.status === 'blocked').length;
                    const activeUsers = users.filter(u => u.status === 'active').length;

                    document.getElementById('totalUsers').textContent = totalUsers;
                    document.getElementById('totalBalance').textContent = '$' + totalBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    document.getElementById('blockedUsers').textContent = blockedUsers;
                    document.getElementById('activeUsers').textContent = activeUsers;
                }
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        // Navigate to different pages
        function navigate(page) {
            switch (page) {
                case 'dashboard':
                    window.location.href = 'admin-dashboard.html';
                    break;
                case 'users':
                    window.location.href = 'users.html';
                    break;
                case 'transactions':
                    window.location.href = 'transactions.html';
                    break;
                case 'codes':
                    window.location.href = 'codes.html';
                    break;
                case 'settings':
                    window.location.href = 'settings.html';
                    break;
            }
        }

        // Logout
        function logout() {
            localStorage.removeItem('admin_token');
            localStorage.removeItem('admin_user');
            window.location.href = '../admin-login.html';
        }

        // Refresh data
        function refreshData() {
            loadStats();
        }

        // Initialize
        if (checkAuth()) {
            loadStats();
        }
    </script>
</body>

</html>
```

# 3. CSS files linked

### `assets/css/theme.css`
```css
:root {
  --bg-primary: #F5F7FA;
  --bg-secondary: #FFFFFF;
  --bg-card: #FFFFFF;
  --border-color: #E5E7EB;
  --text-primary: #111827;
  --text-secondary: #6B7280;
  --text-muted: #9CA3AF;
  --accent: #111827;
  --accent-hover: #374151;
  --success: #10B981;
  --danger: #EF4444;
  --warning: #F59E0B;
  --shadow: 0 1px 3px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.08);
  --shadow-lg: 0 8px 32px rgba(0,0,0,0.10);
  --radius: 12px;
  --radius-sm: 8px;
  --sidebar-width: 260px;
}

[data-theme="dark"] {
  --bg-primary: #0F1115;
  --bg-secondary: #171A20;
  --bg-card: #171A20;
  --border-color: #2B2F36;
  --text-primary: #E5E7EB;
  --text-secondary: #9CA3AF;
  --text-muted: #6B7280;
  --accent: #E5E7EB;
  --accent-hover: #F9FAFB;
  --shadow: 0 1px 3px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.3);
  --shadow-lg: 0 8px 32px rgba(0,0,0,0.4);
}

/* Page loader */
.page-loader {
  position: fixed;
  inset: 0;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  transition: opacity 0.4s ease;
}

.page-loader.fade-out {
  opacity: 0;
  pointer-events: none;
}

.loader-spiral {
  width: 56px;
  height: 56px;
  animation: spiralSpin 1s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  margin-bottom: 20px;
}

@keyframes spiralSpin {
  0% { transform: rotate(0deg) scale(1); }
  50% { transform: rotate(180deg) scale(1.08); }
  100% { transform: rotate(360deg) scale(1); }
}

.loader-name {
  font-family: 'Cormorant Garamond', serif;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  color: var(--text-primary);
  animation: loaderPulse 1.5s ease-in-out infinite;
}

.loader-sub {
  font-size: 10px;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-top: 4px;
  animation: loaderPulse 1.5s ease-in-out infinite;
  animation-delay: 0.2s;
}

@keyframes loaderPulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}
```

### `assets/css/style.css`
```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  transition: background-color 0.3s ease, color 0.3s ease;
  min-height: 100vh;
}

a {
  text-decoration: none;
  color: inherit;
}

input,
select,
textarea {
  font-family: inherit;
  font-size: 14px;
  outline: none;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  width: 100%;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

input:focus,
select:focus,
textarea:focus {
  border-color: var(--text-primary);
  box-shadow: 0 0 0 3px rgba(17, 24, 39, 0.08);
}

[data-theme="dark"] input:focus,
[data-theme="dark"] select:focus {
  box-shadow: 0 0 0 3px rgba(229, 231, 235, 0.08);
}

button {
  font-family: inherit;
  cursor: pointer;
  border: none;
  outline: none;
}

/* Primary Button */
.btn-primary {
  background: var(--text-primary);
  color: var(--bg-primary);
  padding: 13px 24px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.3px;
  width: 100%;
  transition: opacity 0.2s ease, transform 0.1s ease;
}

.btn-primary:hover {
  opacity: 0.85;
}

.btn-primary:active {
  transform: scale(0.99);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: var(--text-primary);
  padding: 12px 24px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  border: 1px solid var(--border-color);
  transition: background 0.2s ease;
}

.btn-secondary:hover {
  background: var(--bg-primary);
}

/* Card */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow);
}

/* Form Group */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 18px;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  letter-spacing: 0.2px;
}

/* Alert */
.alert {
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  margin-bottom: 16px;
  display: none;
}

.alert.show {
  display: block;
}

.alert-error {
  background: #FEF2F2;
  color: #DC2626;
  border: 1px solid #FECACA;
}

.alert-success {
  background: #F0FDF4;
  color: #16A34A;
  border: 1px solid #BBF7D0;
}

[data-theme="dark"] .alert-error {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.2);
  color: #FCA5A5;
}

[data-theme="dark"] .alert-success {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.2);
  color: #6EE7B7;
}

/* Spinner */
.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
  vertical-align: middle;
  margin-right: 8px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Sidebar Layout */
.layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  z-index: 100;
  transition: transform 0.3s ease;
}

/* Dashboard: fixed dark brand sidebar — not affected by theme toggle */
.layout--fixed-sidebar .sidebar {
  background: #171A20;
  border-right: none;
}

[data-theme="dark"] .layout--fixed-sidebar .sidebar {
  background: #171A20;
}

[data-theme="dark"] .layout--fixed-sidebar .balance-card {
  background: #171A20;
  color: inherit;
  border: none;
}

.main-content {
  margin-left: var(--sidebar-width);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: 0 32px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 99;
}

.page-content {
  padding: 32px;
  flex: 1;
}

/* Sidebar nav */
.sidebar-logo {
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--border-color);
}

.sidebar-logo h1 {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--text-primary);
}

.sidebar-logo p {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
  letter-spacing: 0.3px;
}

.sidebar-nav {
  padding: 16px 12px;
  flex: 1;
  overflow-y: auto;
}

.nav-section-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 8px 12px 4px;
  margin-top: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 2px;
}

.nav-item:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-weight: 600;
}

.nav-item svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 16px 12px;
  border-top: 1px solid var(--border-color);
}

/* Topbar */
.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.topbar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.icon-btn {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s ease;
  position: relative;
}

.icon-btn:hover {
  color: var(--text-primary);
  background: var(--border-color);
}

.notification-dot {
  width: 8px;
  height: 8px;
  background: var(--danger);
  border-radius: 50%;
  position: absolute;
  top: 6px;
  right: 6px;
  border: 2px solid var(--bg-secondary);
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--text-primary);
  color: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  flex-shrink: 0;
}

/* Balance Card */
.balance-card {
  background: var(--text-primary);
  color: var(--bg-primary);
  border-radius: var(--radius);
  padding: 28px 32px;
  position: relative;
  overflow: hidden;
}

[data-theme="dark"] .balance-card {
  background: #1E2128;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.balance-card::before {
  content: '';
  position: absolute;
  top: -40px;
  right: -40px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.04);
}

.balance-card::after {
  content: '';
  position: absolute;
  bottom: -60px;
  right: 60px;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.03);
}

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

/* Table */
.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.data-table td {
  padding: 14px 16px;
  font-size: 14px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
}

.data-table tr:last-child td {
  border-bottom: none;
}

.data-table tr:hover td {
  background: var(--bg-primary);
}

/* Badge */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.badge-success {
  background: rgba(16, 185, 129, 0.1);
  color: #10B981;
}

.badge-danger {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

.badge-warning {
  background: rgba(245, 158, 11, 0.1);
  color: #F59E0B;
}

.badge-neutral {
  background: var(--bg-primary);
  color: var(--text-secondary);
}

/* Amount colors */
.amount-credit {
  color: #10B981;
  font-weight: 600;
}

.amount-debit {
  color: #EF4444;
  font-weight: 600;
}

/* Mobile */
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .main-content {
    margin-left: 0;
  }

  .page-content {
    padding: 16px;
  }

  .topbar {
    padding: 0 16px;
  }
}

/* Overlay */
.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 99;
}

.sidebar-overlay.show {
  display: block;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-muted);
}

.empty-state svg {
  width: 48px;
  height: 48px;
  margin: 0 auto 16px;
  opacity: 0.4;
}

.empty-state p {
  font-size: 14px;
}

/* Loading skeleton */
.skeleton {
  background: linear-gradient(90deg, var(--border-color) 25%, var(--bg-primary) 50%, var(--border-color) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }

  100% {
    background-position: -200% 0;
  }
}

/* ── Input placeholder faint ── */
input::placeholder {
  color: #9CA3AF !important;
  opacity: 1;
}

[data-theme="dark"] input::placeholder {
  color: #4B5563 !important;
}

/* Light mode input background tint */
[data-theme="light"] input,
[data-theme="light"] select {
  background: #F9FAFB !important;
}
```

# 4. Javascript files specific to admin dashboard

### `assets/js/theme.js`
```javascript
const Theme = {
  init() {
    const saved = localStorage.getItem('arcteronTheme') || 'system';
    this.apply(saved);
  },

  apply(preference) {
    localStorage.setItem('arcteronTheme', preference);
    let theme;
    if (preference === 'system') {
      theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    } else {
      theme = preference;
    }
    document.documentElement.setAttribute('data-theme', theme);

    // Update toggle button if it exists
    const btn = document.getElementById('themeToggle');
    if (btn) {
      btn.innerHTML = theme === 'dark' ? getSunIcon() : getMoonIcon();
    }
  },

  toggle() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    this.apply(next);
  }
};

function getMoonIcon() {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
}

function getSunIcon() {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
}

// Watch system preference changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (localStorage.getItem('arcteronTheme') === 'system') {
    Theme.apply('system');
  }
});

Theme.init();
```

*Note: All page-specific logic for `admin-dashboard.html` is implemented natively via an inline `<script>` at the bottom of the HTML file (lines 696 to 831). There are no external JS files specifically linked for page logic.*
