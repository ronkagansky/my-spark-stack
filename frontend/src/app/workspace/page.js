'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@/context/user-context';
import { Button } from '@/components/ui/button';
import { PaperclipIcon, SendIcon, XIcon, ChevronDownIcon } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ProjectWebSocketService } from '@/lib/project-websocket';
import { api } from '@/lib/api';
import { Textarea } from '@/components/ui/textarea';

export default function WorkspacePage() {
  const { addProject } = useUser();
  const [message, setMessage] = useState('');
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState('confirmation.tsx');
  const [messages, setMessages] = useState([]);
  const [projectId, setProjectId] = useState(null);
  const [webSocketService, setWebSocketService] = useState(null);

  const exampleFiles = [
    'confirmation.tsx',
    'calendar.tsx',
    'booking.tsx',
    'settings.tsx',
    'layout.tsx',
  ];

  useEffect(() => {
    if (projectId) {
      const ws = new ProjectWebSocketService(projectId);
      ws.connect();

      const handleMessage = (data) => {
        setMessages((prev) => [
          ...prev,
          {
            type: data.type,
            content: data.content,
            timestamp: data.timestamp,
          },
        ]);
      };

      ws.addListener(handleMessage);
      setWebSocketService(ws);

      return () => {
        ws.removeListener(handleMessage);
        ws.disconnect();
      };
    }
  }, [projectId]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    const userMessage = {
      type: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    if (!projectId) {
      try {
        const project = await api.createProject({
          name: new Date().toLocaleDateString(),
          description: `Chat session started on ${new Date().toLocaleDateString()}`,
        });
        setProjectId(project.id);
        addProject(project);

        const ws = new ProjectWebSocketService(project.id);

        // Wait for WebSocket connection to be established
        await new Promise((resolve, reject) => {
          ws.connect();
          ws.ws.onopen = () => resolve();
          ws.ws.onerror = () =>
            reject(new Error('WebSocket connection failed'));
        });

        const handleMessage = (data) => {
          setMessages((prev) => [
            ...prev,
            {
              type: data.type,
              content: data.content,
              timestamp: data.timestamp,
            },
          ]);
        };

        ws.addListener(handleMessage);
        setWebSocketService(ws);

        setMessages((prev) => [...prev, userMessage]);
        ws.sendMessage({
          type: 'message',
          content: message,
        });
      } catch (error) {
        console.error('Failed to create project:', error);
        return;
      }
    } else {
      setMessages((prev) => [...prev, userMessage]);
      webSocketService.sendMessage({
        type: 'message',
        content: message,
      });
    }

    setMessage('');
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Main content */}
      <div className="flex-1 flex flex-col md:flex-row">
        {/* Preview toggle for mobile - moved to top right */}
        <div className="md:hidden fixed top-4 right-4 z-40">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsPreviewOpen(!isPreviewOpen)}
          >
            {isPreviewOpen ? 'Hide Preview' : 'Show Preview'}
          </Button>
        </div>

        {/* Chat section - adjusted padding for mobile */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 overflow-auto p-4 pt-16 md:pt-4">
            {/* Messages will go here */}
            <div className="space-y-4">
              {/* Chat messages */}
              {messages.map((msg, index) => (
                <div key={index} className="flex items-start gap-4">
                  <div
                    className={`w-8 h-8 rounded ${
                      msg.type === 'user' ? 'bg-blue-500/10' : 'bg-primary/10'
                    } flex-shrink-0`}
                  />
                  <div className="flex-1">
                    <div className="mt-1 prose prose-sm max-w-none">
                      {msg.content}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="border-t p-4">
            <form className="flex flex-col gap-4" onSubmit={handleSendMessage}>
              <div className="flex gap-4">
                <Textarea
                  placeholder="Ask a follow up..."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="flex-1 min-h-[80px]"
                  rows={3}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" size="icon" variant="ghost">
                  <PaperclipIcon className="h-4 w-4" />
                </Button>
                <Button type="submit" size="icon">
                  <SendIcon className="h-4 w-4" />
                </Button>
              </div>
            </form>
          </div>
        </div>

        {/* Preview section */}
        <div
          className={`${
            isPreviewOpen ? 'translate-x-0' : 'translate-x-full'
          } md:translate-x-0 fixed md:static right-0 top-0 h-screen w-full md:w-[600px] border-l bg-background transition-transform duration-200 ease-in-out z-30`}
        >
          <div className="p-4 pl-16 md:pl-4 border-b flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button variant="ghost" size="sm">
                Preview
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="flex items-center gap-2"
                  >
                    {selectedFile}
                    <ChevronDownIcon className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  {exampleFiles.map((file) => (
                    <DropdownMenuItem
                      key={file}
                      onClick={() => setSelectedFile(file)}
                    >
                      {file}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            {/* Add close button for mobile */}
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              onClick={() => setIsPreviewOpen(false)}
            >
              <XIcon className="h-4 w-4" />
            </Button>
          </div>
          <div className="p-4">
            <div className="rounded-lg border bg-muted/40 h-[calc(100vh-8rem)]">
              {/* Preview content will go here */}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
