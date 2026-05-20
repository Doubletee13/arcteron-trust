const API_BASE = 'http://127.0.0.1:8000';

const Api = {
  getToken() {
    return localStorage.getItem('arcteronToken');
  },

  setToken(token) {
    localStorage.setItem('arcteronToken', token);
  },

  removeToken() {
    localStorage.removeItem('arcteronToken');
    localStorage.removeItem('arcteronUser');
    sessionStorage.removeItem('arcteronPinVerified');
  },

  getUser() {
    const u = localStorage.getItem('arcteronUser');
    return u ? JSON.parse(u) : null;
  },

  setUser(user) {
    localStorage.setItem('arcteronUser', JSON.stringify(user));
  },

  async request(method, endpoint, body = null, auth = false) {
    const headers = { 'Content-Type': 'application/json' };
    if (auth) {
      const token = this.getToken();
      if (!token) {
        window.location.href = '/frontend/pages/login.html';
        return;
      }
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config = { method, headers };
    if (body) config.body = JSON.stringify(body);

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, config);
      const data = await res.json();

      if (res.status === 401) {
        this.removeToken();
        window.location.href = '/frontend/pages/login.html';
        return;
      }

      return { ok: res.ok, status: res.status, data };
    } catch (err) {
      return { ok: false, status: 0, data: { detail: 'Network error. Please check your connection.' } };
    }
  },

  get(endpoint, auth = false) {
    return this.request('GET', endpoint, null, auth);
  },

  post(endpoint, body, auth = false) {
    return this.request('POST', endpoint, body, auth);
  },

  put(endpoint, body, auth = false) {
    return this.request('PUT', endpoint, body, auth);
  },

  delete(endpoint, auth = false) {
    return this.request('DELETE', endpoint, null, auth);
  }
};