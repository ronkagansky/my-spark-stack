'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { PaperclipIcon, SendIcon } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';

export function Chat({
  messages,
  onSendMessage,
  projectTitle,
  status = 'ready',
}) {
  const [message, setMessage] = useState('');

  const getStatusColor = (status) => {
    switch (status) {
      case 'ready':
        return 'bg-green-500';
      case 'booting':
        return 'bg-yellow-500';
      case 'offline':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    onSendMessage(message);
    setMessage('');
  };

  return (
    <div className="flex-1 flex flex-col">
      <div className="fixed top-0 left-0 right-0 md:relative bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-10 border-b">
        <div className="px-4 py-2.5 flex items-center justify-between">
          <h1 className="text-lg font-semibold">{projectTitle}</h1>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${getStatusColor(status)}`} />
            <span className="text-sm text-muted-foreground capitalize">
              {status}
            </span>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4 pt-16 md:pt-4">
        <div className="space-y-4">
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
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
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
  );
}
