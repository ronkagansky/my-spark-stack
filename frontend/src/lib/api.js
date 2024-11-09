const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  async createAccount(username) {
    const res = await fetch(`${API_URL}/api/auth/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username }),
    });

    if (!res.ok) {
      throw new Error(`Failed to create account: ${res.statusText}`);
    }

    const data = await res.json();
    return data;
  }

  async getCurrentUser(username) {
    const res = await fetch(`${API_URL}/api/auth/me?username=${username}`);

    if (!res.ok) {
      throw new Error(`Failed to get user: ${res.statusText}`);
    }

    const data = await res.json();
    return data;
  }

  async getUserProjects(username) {
    const res = await fetch(`${API_URL}/projects/${username}`);

    if (!res.ok) {
      throw new Error(`Failed to get projects: ${res.statusText}`);
    }

    const data = await res.json();
    return data;
  }

  async createProject(username, project) {
    const res = await fetch(`${API_URL}/projects/create?username=${username}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(project),
    });

    if (!res.ok) {
      throw new Error(`Failed to create project: ${res.statusText}`);
    }

    const data = await res.json();
    return data;
  }
}

// Export singleton instance
export const api = new ApiClient();
