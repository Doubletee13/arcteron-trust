const Utils = {
  formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2
    }).format(amount);
  },

  formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric'
    });
  },

  formatDateTime(dateStr) {
    return new Date(dateStr).toLocaleString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  },

  showAlert(id, message, type = 'error') {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = message;
    el.className = `alert alert-${type} show`;
    setTimeout(() => el.classList.remove('show'), 5000);
  },

  setLoading(btnId, loading, defaultText) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    btn.innerHTML = loading ? `<span class="spinner"></span> Please wait...` : defaultText;
  },

  maskAccountNumber(number) {
    if (!number) return '----';
    return `****${number.slice(-4)}`;
  },

  getStatusBadge(status) {
    const map = {
      completed: 'badge-success',
      pending: 'badge-warning',
      failed: 'badge-danger',
      reversed: 'badge-neutral'
    };
    return `<span class="badge ${map[status] || 'badge-neutral'}">${status}</span>`;
  },

  showLoader() {
    if (document.getElementById('pageLoader')) return;
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const loader = document.createElement('div');
    loader.id = 'pageLoader';
    loader.className = 'page-loader';
    loader.innerHTML = `
      <svg class="loader-spiral" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="28" cy="28" r="24" stroke="${isDark ? '#2B2F36' : '#E5E7EB'}" stroke-width="3"/>
        <path d="M28 4 A24 24 0 0 1 52 28" stroke="${isDark ? '#E5E7EB' : '#111827'}" stroke-width="3.5" stroke-linecap="round"/>
        <path d="M52 28 A24 24 0 0 1 28 52" stroke="#6B7280" stroke-width="3" stroke-linecap="round"/>
        <path d="M28 52 A24 24 0 0 1 4 28" stroke="${isDark ? '#374151' : '#D1D5DB'}" stroke-width="3" stroke-linecap="round"/>
        <circle cx="28" cy="4" r="3.5" fill="${isDark ? '#E5E7EB' : '#111827'}"/>
        <circle cx="52" cy="28" r="3" fill="#6B7280"/>
      </svg>
      <div class="loader-name">Arcteron Trust</div>
      <div class="loader-sub">Private Banking</div>
    `;
    document.body.appendChild(loader);
  },

  hideLoader() {
    const loader = document.getElementById('pageLoader');
    if (!loader) return;
    loader.classList.add('fade-out');
    setTimeout(() => loader.remove(), 400);
  },

  navigateTo(url, delay = 300) {
    this.showLoader();
    setTimeout(() => { window.location.href = url; }, delay);
  },

  setAvatar(elementId, user) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (user.profile_photo) {
      el.innerHTML = '<img src="' + user.profile_photo + '" alt="' + (user.first_name || '') + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">';
    } else {
      const initials = (user.first_name?.[0] || '') + (user.last_name?.[0] || '');
      el.textContent = initials.toUpperCase();
    }
  },

  showToast(message, type = 'error') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        gap: 8px;
        pointer-events: none;
      `;
      document.body.appendChild(container);

      // Add styles if not present
      if (!document.getElementById('toast-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
          .toast {
            padding: 12px 20px;
            background: #111827;
            color: #fff;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
            transform: translateY(20px);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: auto;
            display: flex;
            align-items: center;
            gap: 10px;
          }
          .toast.show { transform: translateY(0); opacity: 1; }
          .toast-error { border-left: 4px solid #EF4444; }
          .toast-success { border-left: 4px solid #10B981; }
          [data-theme="dark"] .toast { background: #1F2937; border: 1px solid #374151; }
        `;
        document.head.appendChild(style);
      }
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ?
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' :
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';

    toast.innerHTML = `${icon} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
};

document.addEventListener('DOMContentLoaded', () => Utils.hideLoader());
window.addEventListener('beforeunload', () => Utils.showLoader());