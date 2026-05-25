const Auth = {
  PIN_SESSION_KEY: 'arcteronPinVerified',

  isLoggedIn() {
    return !!Api.getToken();
  },

  isPinSessionVerified() {
    return sessionStorage.getItem(this.PIN_SESSION_KEY) === '1';
  },

  markPinSessionVerified() {
    sessionStorage.setItem(this.PIN_SESSION_KEY, '1');
  },

  clearPinSession() {
    sessionStorage.removeItem(this.PIN_SESSION_KEY);
  },

  /**
   * Full gate: token, optional /me refresh for has_pin, set-pin vs enter-pin vs proceed.
   * Returns true only when the user may stay on the current protected page (e.g. dashboard).
   */
  async requireAuthAsync() {
    if (!this.isLoggedIn()) {
      Utils.navigateTo('/frontend/pages/login.html');
      return false;
    }

    let user = Api.getUser();
    if (!user) {
      Api.removeToken();
      Utils.navigateTo('/frontend/pages/login.html');
      return false;
    }

    // Validate token is still valid by hitting /api/auth/me
    // If token expired, clear and redirect to login instead of PIN
    if (typeof user.has_pin !== 'boolean') {
      const res = await Api.get('/api/auth/me', true);
      if (!res || !res.ok) {
        // Token invalid/expired - clear everything and go to login
        this.logout();
        return false;
      }
      Api.setUser(res.data);
      user = res.data;
    } else {
      // Even if has_pin is cached, verify token validity periodically
      const res = await Api.get('/api/auth/me', true);
      if (!res || !res.ok) {
        this.logout();
        return false;
      }
      // Update user cache with fresh data
      Api.setUser(res.data);
      user = res.data;
    }

    const path = window.location.pathname || '';
    const onSetPin = path.includes('set-pin.html');
    const onEnterPin = path.includes('enter-pin.html');

    if (user.has_pin === false) {
      if (!onSetPin) {
        window.location.href = '/frontend/pages/set-pin.html';
        return false;
      }
      return true;
    }

    if (!this.isPinSessionVerified()) {
      if (!onEnterPin) {
        window.location.href = '/frontend/pages/enter-pin.html';
        return false;
      }
      return true;
    }

    return true;
  },

  requireGuest() {
    if (!this.isLoggedIn()) return;
    const user = Api.getUser();
    if (!user) {
      Api.removeToken();
      return;
    }
    if (typeof user.has_pin !== 'boolean' || user.has_pin === false) {
      Utils.navigateTo('/frontend/pages/set-pin.html');
      return;
    }
    if (!this.isPinSessionVerified()) {
      Utils.navigateTo('/frontend/pages/enter-pin.html');
      return;
    }
    this.redirectByRole(user);
  },

  redirectByRole(user) {
    if (user.role === 'superadmin') {
      Utils.navigateTo('/frontend/pages/superadmin/dashboard.html');
    } else if (user.role === 'admin') {
      Utils.navigateTo('/frontend/pages/admin/dashboard.html');
    } else {
      Utils.navigateTo('/frontend/pages/user/dashboard.html');
    }
  },

  logout() {
    this.clearPinSession();
    Api.removeToken();
    Utils.navigateTo('/frontend/pages/login.html');
  },

  getInitials(firstName, lastName) {
    return `${firstName?.[0] || ''}${lastName?.[0] || ''}`.toUpperCase();
  }
};
