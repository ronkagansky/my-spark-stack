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

    this.ws = new WebSocket(
      `${wsProtocol}${baseUrl}/api/ws/chat/${this.projectId}`
    );

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.notifyListeners(data);
    };

    this.ws.onclose = () => {
      console.log('WebSocket connection closed');
      // Attempt to reconnect after 5 seconds
      setTimeout(() => this.connect(), 5000);
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
