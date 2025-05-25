// API Service
class AuthService {
  constructor() {
    this.baseUrl = '/api/auth';
    this.tokenKey = 'auth_token';
    this.refreshKey = 'refresh_token';
  }

  // Сохранение токенов
  setTokens({ access, refresh }) {
    localStorage.setItem(this.tokenKey, access);
    if (refresh) {
      localStorage.setItem(this.refreshKey, refresh);
    }
  }

  // Удаление токенов
  clearTokens() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshKey);
  }

  // Проверка авторизации
  isAuthenticated() {
    return !!localStorage.getItem(this.tokenKey);
  }

  // Авторизация
  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
      throw new Error('Ошибка авторизации');
    }

    const tokens = await response.json();
    this.setTokens({
      access: tokens.access,
      refresh: tokens.refresh
    });
    return tokens;
  }

  // Выход
  logout() {
    this.clearTokens();
    window.location.href = '/login';
  }

  // Обновление токена
  async refreshToken() {
    const refresh = localStorage.getItem(this.refreshKey);
    if (!refresh) throw new Error('No refresh token');

    const response = await fetch(`${this.baseUrl}/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh })
    });

    if (!response.ok) {
      this.clearTokens();
      throw new Error('Ошибка обновления токена');
    }

    const { access } = await response.json();
    localStorage.setItem(this.tokenKey, access);
    return access;
  }

  // Запрос с авторизацией
  async authFetch(url, options = {}) {
    let token = localStorage.getItem(this.tokenKey);
    if (!token) throw new Error('Not authenticated');

    // Добавляем токен в заголовки
    options.headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    };

    let response = await fetch(url, options);

    // Если токен истек, пробуем обновить
    if (response.status === 401) {
      try {
        token = await this.refreshToken();
        options.headers.Authorization = `Bearer ${token}`;
        response = await fetch(url, options);
      } catch (e) {
        this.logout();
        throw e;
      }
    }

    return response;
  }
}

// Инициализация сервиса
const authService = new AuthService();