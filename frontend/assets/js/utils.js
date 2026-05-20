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
  }
};

document.addEventListener('DOMContentLoaded', () => Utils.hideLoader());
window.addEventListener('beforeunload', () => Utils.showLoader());