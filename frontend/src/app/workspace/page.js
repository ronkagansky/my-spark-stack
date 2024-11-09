'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/context/user-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { SendIcon, XIcon, ChevronDownIcon } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { webSocketService } from '@/lib/websocket';

export default function WorkspacePage() {
  const router = useRouter();
  const { user } = useUser();
  const [message, setMessage] = useState('');
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState('confirmation.tsx');
  const [messages, setMessages] = useState([]);

  const exampleFiles = [
    'confirmation.tsx',
    'calendar.tsx',
    'booking.tsx',
    'settings.tsx',
    'layout.tsx',
  ];

  useEffect(() => {
    // Connect WebSocket when component mounts
    webSocketService.connect();

    // Add message listener
    const handleMessage = (data) => {
      setMessages((prev) => [...prev, data]);
    };

    webSocketService.addListener(handleMessage);

    // Cleanup
    return () => {
      webSocketService.removeListener(handleMessage);
    };
  }, []);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    // Add user message to chat
    const userMessage = {
      type: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Send message through WebSocket
    webSocketService.sendMessage({
      type: 'message',
      content: message,
    });

    // Clear input
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
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded bg-primary/10 flex-shrink-0" />
                <div className="flex-1">
                  <div className="mt-1 prose prose-sm max-w-none">
                    Fork of AI Calendly Clone was forked. Continue chatting to
                    ask questions about or make changes to it.
                  </div>
                </div>
              </div>

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
            <form className="flex gap-4" onSubmit={handleSendMessage}>
              <Input
                placeholder="Ask a follow up..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="flex-1"
              />
              <Button type="submit" size="icon">
                <SendIcon className="h-4 w-4" />
              </Button>
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
