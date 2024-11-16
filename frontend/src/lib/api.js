export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

  async _delete(endpoint) {
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });

    if (!res.ok) {
      throw new Error(`API error: ${res.statusText}`);
    }

    return res.json();
  }

  async _patch(endpoint, data) {
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'PATCH',
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

  async createAccount(username) {
    const data = await this._post('/api/auth/create', { username });
    localStorage.setItem('token', data.token);
    return data.user;
  }

  async getCurrentUser() {
    try {
      return await this._get('/api/auth/me');
    } catch (error) {
      if (
        error.message.includes('401') ||
        error.message.includes('Unauthorized')
      ) {
        localStorage.removeItem('token');
        window.location.reload();
      }
      throw error;
    }
  }

  async getUserTeams() {
    return this._get('/api/teams');
  }

  async getUserProjects() {
    return this._get('/api/projects');
  }

  async getProject(projectId) {
    return this._get(`/api/projects/${projectId}`);
  }

  async createChat(chat) {
    return this._post('/api/chats', chat);
  }

  async getProjectFile(projectId, filePath) {
    return this._get(`/api/projects/${projectId}/file/${filePath}`);
  }

  async deleteProject(projectId) {
    return this._delete(`/api/projects/${projectId}`);
  }

  async updateProject(projectId, updates) {
    return this._patch(`/api/projects/${projectId}`, updates);
  }

  async getStackPacks() {
    return this._get('/api/stacks');
  }
}

// Export singleton instance
export const api = new ApiClient();
