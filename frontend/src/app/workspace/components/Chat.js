'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { SendIcon } from 'lucide-react';
import { Input } from '@/components/ui/input';
import rehypeRaw from 'rehype-raw';

const FileUpdate = (props) => {
  return (
    <div className="inline-block px-2 py-1 mt-2 mb-2 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-md">
      {props.children}
    </div>
  );
};
const components = {
  'file-update': FileUpdate,
};

export function Chat({
  respStreaming,
  connected,
  messages,
  onSendMessage,
  projectTitle,
  status,
}) {
  const [message, setMessage] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const messagesEndRef = useRef(null);

  const fixCodeBlocks = (content) => {
    content = content.replace(
      /```[\w.]+\n[#/]+ (\S+)\n[\s\S]+?```/g,
      '<file-update>$1</file-update>'
    );
    content = content.replace(
      /```[\w.]+\n[/*]+ (\S+) \*\/\n[\s\S]+?```/g,
      '<file-update>$1</file-update>'
    );
    content = content.replace(/```[^`]+$/, '...');
    return content;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    onSendMessage({ content: message });
    setMessage('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.ctrlKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  console.log(messages);

  const scrollToBottom = () => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]); // Scroll when messages update

  const handleScroll = (e) => {
    const element = e.target;
    const isScrolledNearBottom =
      element.scrollHeight - element.scrollTop - element.clientHeight < 100;

    setAutoScroll(isScrolledNearBottom);
  };

  return (
    <div className="flex-1 flex flex-col md:max-w-[80%] md:mx-auto w-full">
      <div className="fixed top-0 left-0 right-0 md:relative bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-10 border-b">
        <div className="px-4 py-2.5 pt-16 md:pt-2.5 flex items-center justify-between gap-4">
          <h1 className="text-base font-semibold truncate">{projectTitle}</h1>
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className={`w-2 h-2 rounded-full ${status.color}`} />
            <span className="text-sm text-muted-foreground capitalize">
              {status.status}
            </span>
          </div>
        </div>
      </div>
      <div
        className="flex-1 overflow-auto p-4 pt-28 md:pt-4"
        onScroll={handleScroll}
      >
        <div className="space-y-4">
          {messages.map((msg, index) => (
            <div key={index} className="flex items-start gap-4">
              <div
                className={`w-8 h-8 rounded ${
                  msg.role === 'user' ? 'bg-blue-500/10' : 'bg-primary/10'
                } flex-shrink-0 flex items-center justify-center text-sm font-medium ${
                  msg.role === 'user' ? 'text-blue-500' : 'text-primary'
                }`}
              >
                {msg.role === 'user' ? 'H' : 'AI'}
              </div>
              <div className="flex-1">
                <div className="mt-1 prose prose-sm max-w-none">
                  <ReactMarkdown
                    components={components}
                    rehypePlugins={[rehypeRaw]}
                    remarkPlugins={[remarkGfm]}
                  >
                    {fixCodeBlocks(msg.content)}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div ref={messagesEndRef} /> {/* Scroll anchor */}
      </div>
      <div className="border-t p-4">
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="flex gap-4">
            <Input
              placeholder="Ask a follow up..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1"
            />
          </div>
          <div className="flex justify-end gap-2">
            {/* <Button type="button" size="icon" variant="ghost">
              <PaperclipIcon className="h-4 w-4" />
            </Button> */}
            <Button type="submit" size="icon" disabled={respStreaming}>
              <SendIcon className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
