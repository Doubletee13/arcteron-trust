/**
 * NotificationsUI - Shared component for the notification dropdown and receipt modal.
 */
const NotificationsUI = {
  btn: null,
  drop: null,
  dot: null,
  isOpen: false,

  init() {
    // Robust selector for the notification bell icon across all topbars
    this.btn = document.getElementById('notifBtn') || document.querySelector('.topbar-right .icon-btn');
    if (!this.btn) return;

    // Inject CSS
    if (!document.getElementById('notif-ui-styles')) {
      const style = document.createElement('style');
      style.id = 'notif-ui-styles';
      style.innerHTML = `
        .notif-drop {
          position: fixed;
          width: 340px;
          max-width: calc(100vw - 24px);
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: 14px;
          box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
          display: none;
          z-index: 1000;
          overflow: hidden;
          animation: dropIn 0.2s ease-out;
        }
        .notif-drop.show { display: block; }
        @keyframes dropIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        .notif-drop-header { padding: 16px 18px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
        .notif-drop-header h3 { font-size: 14px; font-weight: 600; margin: 0; color: var(--text-primary); }
        .notif-drop-header .text-btn { background: transparent; border: none; color: var(--text-muted); font-size: 11px; cursor: pointer; padding: 4px; }
        .notif-drop-header .text-btn:hover { color: var(--text-primary); }
        .notif-drop-list { max-height: 380px; overflow-y: auto; }
        .notif-drop-item { padding: 14px 18px; display: flex; gap: 14px; border-bottom: 1px solid var(--border-color); cursor: pointer; transition: background 0.2s; }
        .notif-drop-item:hover { background: var(--bg-primary); }
        .notif-drop-item.unread { background: rgba(59, 130, 246, 0.03); }
        .notif-drop-icon { width: 32px; height: 32px; border-radius: 8px; background: var(--bg-primary); display: flex; align-items: center; justify-content: center; color: var(--text-muted); flex-shrink: 0; }
        .notif-drop-item.unread .notif-drop-icon { color: var(--text-primary); background: rgba(59, 130, 246, 0.1); }
        .notif-drop-content { flex: 1; min-width: 0; }
        .notif-drop-title { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 2px; }
        .notif-drop-time { font-size: 11px; color: var(--text-muted); }
        .notif-drop-footer { padding: 12px; text-align: center; border-top: 1px solid var(--border-color); background: var(--bg-primary); }
        .notif-drop-footer a { font-size: 11px; font-weight: 600; color: var(--text-muted); text-decoration: none; }
        .notif-drop-footer a:hover { color: var(--text-primary); }
        .notif-dot { position: absolute; top: 0; right: 0; width: 8px; height: 8px; background: #EF4444; border: 2px solid var(--bg-secondary); border-radius: 50%; }
        .receipt-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px); display: none; align-items: center; justify-content: center; z-index: 2000; padding: 20px; }
        .receipt-modal-overlay.show { display: flex; }
      `;
      document.head.appendChild(style);
    }

    this.btn.id = 'notifBtn';
    this.btn.style.position = 'relative';

    // Create dropdown container
    this.drop = document.createElement('div');
    this.drop.className = 'notif-drop';
    this.drop.innerHTML = `
      <div class="notif-drop-header">
        <h3>Notifications</h3>
        <button class="text-btn" onclick="NotificationsUI.markAllRead()">Mark all as read</button>
      </div>
      <div class="notif-drop-list" id="notifDropList">
        <div class="notif-drop-loading">Loading...</div>
      </div>
      <div class="notif-drop-footer">
        <a href="/frontend/pages/user/notifications.html">View all notifications</a>
      </div>
    `;
    document.body.appendChild(this.drop);

    // Event listeners
    this.btn.onclick = (e) => {
      e.stopPropagation();
      this.toggle();
    };

    document.addEventListener('click', (e) => {
      if (this.isOpen && !this.drop.contains(e.target) && e.target !== this.btn) {
        this.close();
      }
    });

    // Initial count
    this.refreshCount();
    // Refresh every 30s
    setInterval(() => this.refreshCount(), 30000);
  },

  toggle() {
    this.isOpen ? this.close() : this.open();
  },

  open() {
    this.isOpen = true;
    this.drop.classList.add('show');
    this.loadList();

    // Position drop relative to btn
    const rect = this.btn.getBoundingClientRect();
    this.drop.style.top = (rect.bottom + 10) + 'px';
    const rightEdge = window.innerWidth - rect.right;
    // On very small screens prefer aligning to left edge of viewport with a small margin
    if (window.innerWidth <= 420) {
      this.drop.style.right = 'auto';
      this.drop.style.left = '12px';
    } else {
      this.drop.style.left = 'auto';
      this.drop.style.right = Math.max(rightEdge, 12) + 'px';
    }
  },

  close() {
    this.isOpen = false;
    this.drop.classList.remove('show');
  },

  async loadList() {
    const list = document.getElementById('notifDropList');
    try {
      const res = await Api.get('/api/notifications/?per_page=5', true);
      const notifs = res.data.notifications || [];

      if (notifs.length === 0) {
        list.innerHTML = `
          <div class="notif-drop-loading" style="padding: 32px 20px; color: var(--text-muted); font-size: 13px;">
            No notifications yet
          </div>`;
        return;
      }

      list.innerHTML = notifs.map(n => `
        <div class="notif-drop-item ${n.is_read ? '' : 'unread'}" onclick="NotificationsUI.handleClick('${n.id}', '${n.related_transaction_id}')">
          <div class="notif-drop-icon">${this.getIcon(n.notification_type)}</div>
          <div class="notif-drop-content">
            <div class="notif-drop-title">${this.escape(n.title)}</div>
            <div class="notif-drop-time">${this.timeAgo(new Date(n.created_at))}</div>
          </div>
        </div>
      `).join('');
    } catch (err) {
      list.innerHTML = '<div class="notif-drop-loading">Failed to load</div>';
    }
  },

  async refreshCount() {
    try {
      const res = await Api.get('/api/notifications/unread-count', true);
      const count = res.data?.count || 0;

      if (count > 0) {
        if (!this.dot) {
          this.dot = document.createElement('div');
          this.dot.className = 'notif-dot';
          this.btn.appendChild(this.dot);
        }
        this.dot.style.display = 'block';
      } else if (this.dot) {
        this.dot.style.display = 'none';
      }
    } catch (err) {
      // Fail silently
    }
  },

  async handleClick(id, txId) {
    // Mark as read
    await Api.put(`/api/notifications/${id}/read`, {}, true);
    this.close();
    this.refreshCount();

    if (txId && txId !== 'null' && txId !== 'undefined' && txId !== 'None') {
      TransactionDetails.show(txId);
    } else {
      window.location.href = '/frontend/pages/user/notifications.html';
    }
  },

  async markAllRead() {
    await Api.put('/api/notifications/mark-all-read', {}, true);
    this.loadList();
    this.refreshCount();
  },

  getIcon(type) {
    if (type === 'transaction') return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>';
    if (type === 'security') return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>';
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
  },

  timeAgo(date) {
    const now = new Date();
    const sec = Math.floor((now - date) / 1000);
    if (sec < 60) return 'Just now';
    if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
    return date.toLocaleDateString();
  },

  escape(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
};

/**
 * TransactionDetails - Contextual modal for viewing transaction receipts
 */
const TransactionDetails = {
  modal: null,

  async show(txId) {
    try {
      const res = await Api.get(`/api/transactions/${txId}`, true);
      if (!res || !res.ok) throw new Error('Failed to load transaction');
      this.renderReceipt(res.data);
    } catch (err) {
      console.error(err);
      Utils.showToast('Could not load transaction details.');
    }
  },

  renderReceipt(tx) {
    if (!this.modal) {
      this.modal = document.createElement('div');
      this.modal.className = 'receipt-modal-overlay';
      this.modal.onclick = (e) => {
        if (e.target === this.modal) this.hide();
      };
      document.body.appendChild(this.modal);
    }

    const is_credit = tx.is_credit;
    const date = new Date(tx.transaction_date || tx.created_at);
    const amount = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(tx.amount || 0);

    this.modal.innerHTML = `
      <div class="modal show" style="max-width: 440px;">
        <div class="receipt-modal-header" style="flex-direction: column; align-items: center; gap: 12px; padding: 32px 24px; background: #1F2937; position: relative; border-radius: 14px 14px 0 0;">
          <div style="display:flex; align-items:center; gap:10px;">
            <svg width="28" height="28" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="18" stroke="white" stroke-width="1.5" opacity="0.3" />
              <path d="M20 8 L30 28 H24 L20 20 L16 28 H10 Z" fill="white" opacity="0.9" />
              <path d="M14 23 H26" stroke="white" stroke-width="1.5" opacity="0.6" />
              <circle cx="20" cy="6" r="2" fill="white" opacity="0.5" />
            </svg>
            <span style="font-family: 'Cormorant Garamond', serif; font-size: 24px; font-weight: 600; color: #fff;">Arcteron Trust</span>
          </div>
          <h2 style="font-size: 14px; opacity: 0.7; font-weight: 500; letter-spacing: 1px; text-transform: uppercase; color: #fff; margin-top: 10px;">Transaction Receipt</h2>
          <button class="icon-btn" onclick="TransactionDetails.hide()" style="position: absolute; top: 16px; right: 16px; background:transparent; border:none; color:#fff; opacity: 0.5; cursor:pointer;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div class="receipt-modal-body" style="padding: 24px; background: var(--bg-secondary);">
          <div style="text-align: center; margin-bottom: 24px;">
            <label style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; display:block; margin-bottom: 8px;">Transaction Amount</label>
            <div style="font-size: 32px; font-weight: 700; color: var(--text-primary);">${amount}</div>
            <div style="display:inline-block; margin-top: 10px; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: capitalize; background: ${tx.status === 'completed' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)'}; color: ${tx.status === 'completed' ? '#10B981' : '#F59E0B'};">${tx.status}</div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; border-top: 1px solid var(--border-color); padding-top: 24px;">
            <div><label style="font-size:10px; color:var(--text-muted); text-transform:uppercase; display:block; margin-bottom:4px;">${is_credit ? 'Received From' : 'Transfer To'}</label><p style="font-size: 13px; font-weight: 600; margin:0;">${tx.recipient_name || 'System'}</p></div>
            <div><label style="font-size:10px; color:var(--text-muted); text-transform:uppercase; display:block; margin-bottom:4px;">Reference</label><p style="font-size: 13px; font-weight: 600; margin:0;">#${(tx.reference || '').slice(-8).toUpperCase()}</p></div>
            <div><label style="font-size:10px; color:var(--text-muted); text-transform:uppercase; display:block; margin-bottom:4px;">Bank</label><p style="font-size: 13px; font-weight: 600; margin:0;">${tx.recipient_bank || 'Arcteron Trust'}</p></div>
            <div><label style="font-size:10px; color:var(--text-muted); text-transform:uppercase; display:block; margin-bottom:4px;">Date</label><p style="font-size: 13px; font-weight: 600; margin:0;">${date.toLocaleDateString()}</p></div>
            <div style="grid-column: span 2;"><label style="font-size:10px; color:var(--text-muted); text-transform:uppercase; display:block; margin-bottom:4px;">Account Number</label><p style="font-size: 13px; font-weight: 600; margin:0;">${tx.recipient_account || '—'}</p></div>
          </div>
        </div>
        <div style="padding: 20px 24px 24px; background: var(--bg-secondary); border-radius: 0 0 14px 14px; display:flex; gap:10px;">
          <button onclick="TransactionDetails.download('${tx.id}')" style="flex:1; height:44px; background: #111827; color:#fff; border:none; border-radius:8px; font-weight:600; font-size:13px; cursor:pointer;">Download Receipt</button>
          <button onclick="TransactionDetails.hide()" style="padding:0 20px; height:44px; background:transparent; border:1px solid var(--border-color); border-radius:8px; font-weight:500; font-size:13px; color:var(--text-secondary); cursor:pointer;">Close</button>
        </div>
      </div>
    `;

    this.modal.style.display = 'flex';
    this.modal.classList.add('show');
  },

  hide() {
    if (this.modal) {
      this.modal.classList.remove('show');
      this.modal.style.display = 'none';
    }
  },

  async download(txId) {
    try {
      const theme = document.documentElement.getAttribute('data-theme') || 'light';
      const token = Api.getToken();
      const url = `${API_BASE}/api/transactions/${txId}/receipt?theme=${theme}`;
      const res = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
      if (!res.ok) { Utils.showToast('Could not download receipt.'); return; }
      const blob = await res.blob();
      const objUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objUrl;
      link.download = `receipt-${txId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(objUrl), 1000);
    } catch (e) {
      Utils.showToast('Download failed. Check your connection.');
    }
  }
};

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
  NotificationsUI.init();
});
