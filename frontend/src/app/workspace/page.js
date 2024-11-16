'use client';

import { useEffect, useState, useRef } from 'react';
import { useUser } from '@/context/user-context';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ProjectWebSocketService } from '@/lib/project-websocket';
import { api } from '@/lib/api';
import { Chat } from './components/Chat';
import { Preview } from './components/Preview';

export default function WorkspacePage({ chatId }) {
  const { addChat, team } = useUser();
  const router = useRouter();
  const [projectId, setProjectId] = useState(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [chatTitle, setChatTitle] = useState('New Chat');
  const [projectPreviewUrl, setProjectPreviewUrl] = useState(null);
  const [projectFileTree, setProjectFileTree] = useState([]);
  const [projectStackPackId, setProjectStackPackId] = useState(null);
  const [suggestedFollowUps, setSuggestedFollowUps] = useState([]);
  const [previewHash, setPreviewHash] = useState(1);
  const [status, setStatus] = useState('NEW_CHAT');
  const webSocketRef = useRef(null);

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      router.push('/');
    }
    if (!chatId) {
      router.push('/workspace/new');
    }
  }, [chatId]);

  const initializeWebSocket = async (wsProjectId) => {
    if (webSocketRef.current) {
      webSocketRef.current.disconnect();
    }
    const ws = new ProjectWebSocketService(wsProjectId);
    webSocketRef.current = ws;

    const connectWS = async () => {
      try {
        const date = +new Date();
        await new Promise((resolve, reject) => {
          ws.connect();
          ws.ws.onopen = () => resolve();
          ws.ws.onerror = (error) => reject(error);
          ws.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleSocketMessage(data);
          };
          ws.ws.onclose = (e) => {
            setStatus('DISCONNECTED');
            console.log('WebSocket connection closed', e.code, e.reason);
            if ([1002, 1003].includes(e.code)) {
              initializeWebSocket(chatId);
            }
          };
          setTimeout(
            () => reject(new Error('WebSocket connection timeout')),
            5000
          );
        });

        const handleSocketMessage = (data) => {
          console.log('handleMessage', data, date);
          if (data.for_type === 'status') {
            handleStatus(data);
          } else if (data.for_type === 'chat_update') {
            handleChatUpdate(data);
          } else if (data.for_type === 'chat_chunk') {
            handleChatChunk(data);
          }
        };

        const handleStatus = (data) => {
          setStatus(data.sandbox_status);
        };

        const handleChatUpdate = (data) => {
          setMessages((prev) => {
            const existingMessageIndex = prev.findIndex(
              (m) => m.id === data.message.id
            );
            if (existingMessageIndex >= 0) {
              return [
                ...prev.slice(0, existingMessageIndex),
                data.message,
                ...prev.slice(existingMessageIndex + 1),
              ];
            }
            return [...prev, data.message];
          });
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

        // const handleSandboxStatus = (data) => {
        //   if (data.status === 'READY') {
        //     setStatus({ status: 'Ready', color: 'bg-green-500' });
        //     setProjectPreviewUrl(data.tunnels[3000]);
        //   } else if (data.status === 'BUILDING') {
        //     setStatus({ status: 'Setting up (~3m)', color: 'bg-yellow-500' });
        //   }
        // };

        // const handleSandboxFileTree = (data) => {
        //   setProjectFileTree(data.paths);
        // };

        // const handleChatChunk = (data) => {
        //   setMessages((prev) => {
        //     const lastMessage = prev[prev.length - 1];
        //     if (lastMessage?.role === 'assistant') {
        //       return [
        //         ...prev.slice(0, -1),
        //         { ...lastMessage, content: lastMessage.content + data.content },
        //       ];
        //     }
        //     return [...prev, { role: 'assistant', content: data.content }];
        //   });
        //   if (data.complete) {
        //     setRespStreaming(false);
        //     setPreviewHash((prev) => prev + 1);
        //   }
        //   if (data.suggested_follow_ups) {
        //     setSuggestedFollowUps(data.suggested_follow_ups);
        //   }
        // };
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
    if (chatId !== 'new') {
      initializeWebSocket(chatId).catch((error) => {
        console.error('Failed to initialize WebSocket:', error);
      });
    }
    return () => {
      if (webSocketRef.current) {
        webSocketRef.current.disconnect();
      }
    };
  }, [chatId]);

  const handleStackPackSelect = (stackPackId) => {
    setProjectStackPackId(stackPackId);
  };

  const handleProjectSelect = (projectId) => {
    setProjectId(projectId);
  };

  const handleSendMessage = async (message) => {
    if (!message.content.trim() && message.images.length === 0) return;

    const userMessage = {
      role: 'user',
      content: message.content,
      images: message.images || [],
    };
    if (chatId === 'new') {
      const chat = await api.createChat({
        name: message.content,
        description: `Project started on ${new Date().toLocaleDateString()}`,
        stack_id: projectStackPackId,
        project_id: projectId,
        team_id: team.id,
      });
      addChat(chat);
      setTimeout(() => router.push(`/workspace/${chat.id}`), 100);
    } else {
      webSocketRef.current.sendMessage(userMessage);
    }
  };

  useEffect(() => {
    (async () => {
      if (chatId !== 'new') {
        setStatus('DISCONNECTED');
        const chat = await api.getChat(chatId);
        setChatTitle(chat.name);
        const existingMessages =
          chat?.messages.map((m) => ({
            role: m.role,
            content: m.content,
          })) || [];
        setMessages(existingMessages);
      } else {
        setChatTitle('New Chat');
        setMessages([]);
        setProjectPreviewUrl(null);
        setProjectFileTree([]);
        setStatus('NEW_CHAT');
      }
    })();
  }, [chatId]);

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
          connected={!!webSocketRef.current}
          messages={messages}
          onSendMessage={handleSendMessage}
          projectTitle={chatTitle}
          status={status}
          onProjectSelect={handleProjectSelect}
          onStackSelect={handleStackPackSelect}
          showStackPacks={chatId === 'new'}
          suggestedFollowUps={suggestedFollowUps}
        />
        <Preview
          isOpen={isPreviewOpen}
          onClose={() => setIsPreviewOpen(false)}
          projectPreviewUrl={
            projectPreviewUrl ? `${projectPreviewUrl}?v=${previewHash}` : null
          }
          projectFileTree={projectFileTree}
          projectId={projectId}
          chatId={chatId}
        />
      </div>
    </div>
  );
}
