export class ProjectWebSocketService {
  constructor(projectId) {
    this.ws = null;
    this.listeners = new Set();
    this.projectId = projectId;
  }

  connect() {
    const wsUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsProtocol = wsUrl.startsWith('https') ? 'wss://' : 'ws://';
    const baseUrl = wsUrl.replace(/^https?:\/\//, '');

    // Get token from localStorage
    const token = localStorage.getItem('token');
    if (!token) {
      console.error('No authentication token found');
      return;
    }

    this.ws = new WebSocket(
      `${wsProtocol}${baseUrl}/api/ws/project-chat/${this.projectId}`
    );

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.notifyListeners(data);
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket connection closed', event.code, event.reason);
      // Only attempt to reconnect if it wasn't closed due to auth errors
      if (![4001, 4003].includes(event.code)) {
        setTimeout(() => this.connect(), 5000);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  sendMessage(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  addListener(callback) {
    this.listeners.add(callback);
  }

  removeListener(callback) {
    this.listeners.delete(callback);
  }

  notifyListeners(data) {
    this.listeners.forEach((listener) => listener(data));
  }
}
