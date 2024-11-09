'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@/context/user-context';
import { Button } from '@/components/ui/button';
import { ProjectWebSocketService } from '@/lib/project-websocket';
import { api } from '@/lib/api';
import { Chat } from './components/Chat';
import { Preview } from './components/Preview';

export default function WorkspacePage() {
  const { addProject } = useUser();
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [projectId, setProjectId] = useState(null);
  const [webSocketService, setWebSocketService] = useState(null);
  const [projectTitle, setProjectTitle] = useState('New Chat');

  // Consolidated WebSocket initialization
  const initializeWebSocket = async (wsProjectId) => {
    const ws = new ProjectWebSocketService(wsProjectId);

    try {
      await new Promise((resolve, reject) => {
        ws.connect();
        ws.ws.onopen = () => resolve();
        ws.ws.onerror = (error) => reject(error);

        // Add timeout for connection
        setTimeout(
          () => reject(new Error('WebSocket connection timeout')),
          5000
        );
      });

      const handleMessage = (data) => {
        setMessages((prev) => {
          if (data.is_chunk && prev.length > 0) {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage.type === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...lastMessage, content: lastMessage.content + data.content },
              ];
            }
          }
          return [
            ...prev,
            {
              type: data.type,
              content: data.content,
              timestamp: data.timestamp,
            },
          ];
        });
      };

      ws.addListener(handleMessage);
      setWebSocketService(ws);

      return ws;
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      throw error;
    }
  };

  // Updated project ID effect
  useEffect(() => {
    if (projectId) {
      let ws;
      initializeWebSocket(projectId)
        .then((websocket) => {
          ws = websocket;
        })
        .catch((error) => {
          console.error('Failed to initialize WebSocket:', error);
          // Handle connection error (e.g., show user notification)
        });

      return () => {
        if (ws) {
          ws.disconnect();
        }
      };
    }
  }, [projectId]);

  // Updated handleSendMessage
  const handleSendMessage = async (message) => {
    if (!message.trim()) return;

    const userMessage = {
      type: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    try {
      if (!projectId) {
        const projectName = new Date().toLocaleDateString();
        const project = await api.createProject({
          name: projectName,
          description: `Chat session started on ${new Date().toLocaleDateString()}`,
        });

        setProjectId(project.id);
        setProjectTitle(project.name);
        addProject(project);
        window.history.pushState({}, '', `/workspace/${project.id}`);

        const ws = await initializeWebSocket(project.id);
        setMessages((prev) => [...prev, userMessage]);
        ws.sendMessage({ type: 'message', content: message });
      } else {
        setMessages((prev) => [...prev, userMessage]);
        webSocketService.sendMessage({ type: 'message', content: message });
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      // Handle error (e.g., show user notification)
    }
  };

  // Add this new effect to load project details
  useEffect(() => {
    const loadProjectDetails = async () => {
      // Extract project ID from URL
      const pathParts = window.location.pathname.split('/');
      const urlProjectId = pathParts[pathParts.length - 1];

      if (urlProjectId && urlProjectId !== 'workspace') {
        try {
          const project = await api.getProject(urlProjectId);
          setProjectId(urlProjectId);
          setProjectTitle(project.name);
        } catch (error) {
          console.error('Failed to load project details:', error);
        }
      }
    };

    loadProjectDetails();
  }, []); // Run once on component mount

  return (
    <div className="flex h-screen bg-background">
      <div className="flex-1 flex flex-col md:flex-row">
        <div className="md:hidden fixed top-4 right-4 z-40">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsPreviewOpen(!isPreviewOpen)}
          >
            {isPreviewOpen ? 'Hide Preview' : 'Show Preview'}
          </Button>
        </div>

        <Chat
          messages={messages}
          onSendMessage={handleSendMessage}
          projectTitle={projectTitle}
        />
        <Preview
          isOpen={isPreviewOpen}
          onClose={() => setIsPreviewOpen(false)}
        />
      </div>
    </div>
  );
}
