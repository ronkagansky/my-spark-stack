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
  const [projectPreviewUrl, setProjectPreviewUrl] = useState(null);
  const [projectFileTree, setProjectFileTree] = useState([]);
  const [status, setStatus] = useState({
    status: 'Disconnected',
    color: 'bg-gray-500',
  });

  const initializeWebSocket = async (wsProjectId) => {
    const ws = new ProjectWebSocketService(wsProjectId);

    try {
      await new Promise((resolve, reject) => {
        ws.connect();
        ws.ws.onopen = () => resolve();
        ws.ws.onerror = (error) => reject(error);
        ws.ws.onclose = () => {
          setStatus({ status: 'Disconnected', color: 'bg-gray-500' });
          setProjectPreviewUrl(null);
        };
        setTimeout(
          () => reject(new Error('WebSocket connection timeout')),
          5000
        );
      });

      setStatus({ status: 'Setting up', color: 'bg-yellow-500' });

      const handleSocketMessage = (data) => {
        console.log('handleMessage', data);
        if (data.for_type === 'sandbox_status') {
          handleSandboxStatus(data);
        } else if (data.for_type === 'chat_chunk') {
          handleChatChunk(data);
        } else if (data.for_type === 'sandbox_file_tree') {
          handleSandboxFileTree(data);
        }
      };

      const handleSandboxStatus = (data) => {
        if (data.status === 'READY') {
          setStatus({ status: 'Ready', color: 'bg-green-500' });
          setProjectPreviewUrl(data.tunnels[3000]);
        } else if (data.status === 'BUILDING') {
          setStatus({ status: 'Setting up (~3m)', color: 'bg-yellow-500' });
        }
      };

      const handleSandboxFileTree = (data) => {
        setProjectFileTree(data.paths);
      };

      const handleChatChunk = (data) => {
        setMessages((prev) => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage?.role === 'assistant') {
            return [
              ...prev.slice(0, -1),
              { ...lastMessage, content: lastMessage.content + data.content },
            ];
          }
          return [...prev, { role: 'assistant', content: data.content }];
        });
      };

      ws.addListener(handleSocketMessage);
      setWebSocketService(ws);

      return ws;
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      throw error;
    }
  };

  useEffect(() => {
    if (projectId) {
      let ws;
      initializeWebSocket(projectId)
        .then((websocket) => {
          ws = websocket;
        })
        .catch((error) => {
          console.error('Failed to initialize WebSocket:', error);
        });
      return () => {
        if (ws) {
          ws.disconnect();
        }
      };
    }
  }, [projectId]);

  const handleSendMessage = async (message) => {
    if (!message.content.trim()) return;

    const userMessage = {
      role: 'user',
      content: message.content,
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
        ws.sendMessage({ chat: [...messages, userMessage] });
      } else {
        setMessages((prev) => [...prev, userMessage]);
        webSocketService.sendMessage({ chat: [...messages, userMessage] });
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  useEffect(() => {
    const loadProjectDetails = async () => {
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
  }, []);

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
          connected={!!webSocketService}
          messages={messages}
          onSendMessage={handleSendMessage}
          projectTitle={projectTitle}
          status={status}
        />
        <Preview
          isOpen={isPreviewOpen}
          onClose={() => setIsPreviewOpen(false)}
          projectPreviewUrl={projectPreviewUrl}
          projectFileTree={projectFileTree}
        />
      </div>
    </div>
  );
}
