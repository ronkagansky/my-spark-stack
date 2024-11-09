'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { PaperclipIcon, SendIcon } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';

export function Chat({ messages, onSendMessage, projectTitle, status }) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    onSendMessage(message);
    setMessage('');
  };

  return (
    <div className="flex-1 flex flex-col">
      <div className="fixed top-0 left-0 right-0 md:relative bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-10 border-b">
        <div className="px-4 py-2.5 flex items-center justify-between gap-4">
          <h1 className="text-base font-semibold truncate">{projectTitle}</h1>
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className={`w-2 h-2 rounded-full ${status.color}`} />
            <span className="text-sm text-muted-foreground capitalize">
              {status.status}
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
