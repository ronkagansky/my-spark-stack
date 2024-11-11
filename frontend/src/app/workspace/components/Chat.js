'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { SendIcon } from 'lucide-react';
import { Input } from '@/components/ui/input';
import rehypeRaw from 'rehype-raw';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { api } from '@/lib/api';

const STARTER_PROMPTS = [
  'Build a cat facts app with catfact.ninja API',
  'Build a maps app for coffee shops in SF',
];

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

const EmptyState = ({
  selectedEnvironment,
  setSelectedEnvironment,
  stackPacks,
  onStackPackSelect,
}) => (
  <div className="flex flex-col items-center justify-center h-full">
    <div className="max-w-md w-full">
      <Select
        value={selectedEnvironment}
        onValueChange={(value) => {
          setSelectedEnvironment(value);
          onStackPackSelect(value);
        }}
      >
        <SelectTrigger className="w-full py-6">
          <SelectValue placeholder="Select a Stack" />
        </SelectTrigger>
        <SelectContent className="max-h-[400px] w-full">
          <SelectItem value={null} className="py-2 w-full">
            <div className="flex flex-col gap-1 w-full">
              <span className="font-medium">Pick for me</span>
              <p className="text-sm text-muted-foreground break-words whitespace-normal w-full pr-4">
                Let AI choose the best stack for your project based on your
                first prompt.
              </p>
            </div>
          </SelectItem>
          {stackPacks?.map((pack) => (
            <SelectItem key={pack.id} value={pack.id} className="py-2 w-full">
              <div className="flex flex-col gap-1 w-full">
                <span className="font-medium">{pack.title}</span>
                <p className="text-sm text-muted-foreground break-words whitespace-normal w-full pr-4">
                  {pack.description}
                </p>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  </div>
);

const MessageList = ({ messages, fixCodeBlocks }) => (
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
);

const ChatInput = ({
  message,
  setMessage,
  handleSubmit,
  handleKeyDown,
  handleChipClick,
  respStreaming,
  suggestedFollowUps,
}) => (
  <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
    <div className="flex flex-wrap gap-2">
      {(suggestedFollowUps && suggestedFollowUps.length > 0
        ? suggestedFollowUps
        : STARTER_PROMPTS
      ).map((prompt) => (
        <button
          key={prompt}
          type="button"
          disabled={respStreaming}
          onClick={() => handleChipClick(prompt)}
          className="px-3 py-1 text-sm rounded-full bg-secondary hover:bg-secondary/80 transition-colors"
        >
          {prompt}
        </button>
      ))}
    </div>
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
      <Button type="submit" size="icon" disabled={respStreaming}>
        <SendIcon className="h-4 w-4" />
      </Button>
    </div>
  </form>
);

export function Chat({
  respStreaming,
  messages,
  onSendMessage,
  projectTitle,
  status,
  onStackPackSelect,
  showStackPacks = false,
  suggestedFollowUps = [],
}) {
  const [message, setMessage] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const messagesEndRef = useRef(null);
  const [selectedEnvironment, setSelectedEnvironment] = useState('');
  const [stackPacks, setStackPacks] = useState([]);

  useEffect(() => {
    const fetchStackPacks = async () => {
      try {
        const packs = await api.getStackPacks();
        setStackPacks(packs);
      } catch (error) {
        console.error('Failed to fetch stack packs:', error);
      }
    };
    fetchStackPacks();
  }, []);

  const fixCodeBlocks = (content) => {
    content = content.replace(
      /```[\w.]+\n[#/]+ (\S+)\n[\s\S]+?```/g,
      '<file-update>$1</file-update>'
    );
    content = content.replace(
      /```[\w.]+\n[/*]+ (\S+) \*\/\n[\s\S]+?```/g,
      '<file-update>$1</file-update>'
    );
    content = content.replace(
      /```[\w.]+\n<!-- (\S+) -->\n[\s\S]+?```/g,
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

  const handleChipClick = (prompt) => {
    onSendMessage({ content: prompt });
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
        {messages.length === 0 && showStackPacks ? (
          <EmptyState
            selectedEnvironment={selectedEnvironment}
            setSelectedEnvironment={setSelectedEnvironment}
            stackPacks={stackPacks}
            onStackPackSelect={onStackPackSelect}
          />
        ) : (
          <MessageList messages={messages} fixCodeBlocks={fixCodeBlocks} />
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="border-t p-4">
        <ChatInput
          message={message}
          setMessage={setMessage}
          handleSubmit={handleSubmit}
          handleKeyDown={handleKeyDown}
          handleChipClick={handleChipClick}
          respStreaming={respStreaming}
          suggestedFollowUps={suggestedFollowUps}
        />
      </div>
    </div>
  );
}
