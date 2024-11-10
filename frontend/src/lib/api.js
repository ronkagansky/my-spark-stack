export const API_URL =
  window.location.hostname == 'localhost'
    ? 'http://localhost:8000'
    : window.location.origin;

class ApiClient {
  async _post(endpoint, data) {
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      throw new Error(`API error: ${res.statusText}`);
    }

    return res.json();
  }

  async _get(endpoint) {
    const res = await fetch(`${API_URL}${endpoint}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });

    if (!res.ok) {
      throw new Error(`API error: ${res.statusText}`);
    }

    return res.json();
  }

  async createAccount(username) {
    const data = await this._post('/api/auth/create', { username });
    localStorage.setItem('token', data.token);
    return data.user;
  }

  async getCurrentUser() {
    return this._get('/api/auth/me');
  }

  async getUserProjects() {
    return this._get('/api/projects');
  }

  async getProject(projectId) {
    return this._get(`/api/projects/${projectId}`);
  }

  async createProject(project) {
    return this._post('/api/projects', project);
  }

  async getProjectFile(projectId, filePath) {
    return this._get(`/api/projects/${projectId}/file/${filePath}`);
  }
}

// Export singleton instance
export const api = new ApiClient();
