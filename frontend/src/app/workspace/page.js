'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@/context/user-context';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ProjectWebSocketService } from '@/lib/project-websocket';
import { api } from '@/lib/api';
import { Chat } from './components/Chat';
import { Preview } from './components/Preview';

export default function WorkspacePage() {
  const { addProject } = useUser();
  const router = useRouter();
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [respStreaming, setRespStreaming] = useState(false);
  const [projectId, setProjectId] = useState(null);
  const [webSocketService, setWebSocketService] = useState(null);
  const [projectTitle, setProjectTitle] = useState('New Chat');
  const [projectPreviewUrl, setProjectPreviewUrl] = useState(null);
  const [projectFileTree, setProjectFileTree] = useState([]);
  const [projectStackPackId, setProjectStackPackId] = useState(null);
  const [suggestedFollowUps, setSuggestedFollowUps] = useState([]);
  const [previewHash, setPreviewHash] = useState(1);
  const [status, setStatus] = useState({
    status: 'Disconnected',
    color: 'bg-gray-500',
  });

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      router.push('/');
    }
  }, []);

  const initializeWebSocket = async (wsProjectId) => {
    const ws = new ProjectWebSocketService(wsProjectId);

    const connectWS = async () => {
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

        setStatus({ status: 'Setting up (~3m)', color: 'bg-yellow-500' });

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
          if (data.complete) {
            setRespStreaming(false);
            setPreviewHash((prev) => prev + 1);
          }
          if (data.suggested_follow_ups) {
            setSuggestedFollowUps(data.suggested_follow_ups);
          }
        };

        ws.addListener(handleSocketMessage);
        setWebSocketService(ws);

        return ws;
      } catch (error) {
        console.error('WebSocket connection failed:', error);
        setStatus({ status: 'Disconnected', color: 'bg-gray-500' });
      }
    };

    await connectWS();
    return { ws };
  };

  useEffect(() => {
    if (projectId) {
      initializeWebSocket(projectId)
        .then(({ ws }) => {
          setWebSocketService(ws);
        })
        .catch((error) => {
          console.error('Failed to initialize WebSocket:', error);
        });
    }
  }, [projectId]);

  const handleStackPackSelect = async (stackPackId) => {
    setProjectStackPackId(stackPackId);
  };

  const handleSendMessage = async (message) => {
    if (!message.content.trim()) return;

    const userMessage = {
      role: 'user',
      content: message.content,
    };

    try {
      setRespStreaming(true);
      if (!projectId) {
        setMessages((prev) => [...prev, userMessage]);

        const project = await api.createProject({
          name: 'Project',
          description: `Chat session started on ${new Date().toLocaleDateString()}`,
          stack_pack_id: projectStackPackId,
        });

        setProjectId(project.id);
        setProjectTitle(project.name);
        addProject(project);
        window.history.pushState({}, '', `/workspace/${project.id}`);

        const { ws } = await initializeWebSocket(project.id);
        setWebSocketService(ws);

        ws.sendMessage({ chat: [...messages, userMessage] });
        return;
      }

      setMessages((prev) => [...prev, userMessage]);
      webSocketService.sendMessage({ chat: [...messages, userMessage] });
    } catch (error) {
      console.error('Failed to send message:', error);
      setRespStreaming(false);
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
          const existingMessages =
            project?.chat_messages.map((m) => ({
              role: m.role,
              content: m.content,
            })) || [];
          setMessages(existingMessages);
          setProjectStackPackId(project.stack_pack_id);
        } catch (error) {
          console.error('Failed to load project details:', error);
        }
      } else {
        setProjectId(null);
        setProjectTitle('New Chat');
        setMessages([]);
        setProjectPreviewUrl(null);
        setProjectFileTree([]);
        setStatus({ status: 'Disconnected', color: 'bg-gray-500' });
      }
    };

    loadProjectDetails();
  }, []);

  return (
    <div className="flex h-screen bg-background">
      <div className="flex-1 flex flex-col md:flex-row">
        {!isPreviewOpen && (
          <div className="md:hidden fixed top-4 right-4 z-40">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsPreviewOpen(!isPreviewOpen)}
            >
              View
            </Button>
          </div>
        )}
        <Chat
          respStreaming={respStreaming}
          connected={!!webSocketService}
          messages={messages}
          onSendMessage={handleSendMessage}
          projectTitle={projectTitle}
          status={status}
          onStackPackSelect={handleStackPackSelect}
          showStackPacks={!projectId}
          suggestedFollowUps={suggestedFollowUps}
        />
        <Preview
          isOpen={isPreviewOpen}
          onClose={() => setIsPreviewOpen(false)}
          projectPreviewUrl={
            projectPreviewUrl
              ? `${projectPreviewUrl}?hash=${previewHash}`
              : null
          }
          projectFileTree={projectFileTree}
          projectId={projectId}
        />
      </div>
    </div>
  );
}
