'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { SendIcon, Loader2, ImageIcon, X, Scan } from 'lucide-react';
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
        <SelectTrigger className="w-full py-10">
          <SelectValue placeholder="Select a Stack" />
        </SelectTrigger>
        <SelectContent className="max-h-[500px] w-full">
          <SelectItem value={null} className="py-2 w-full">
            <div className="flex flex-col gap-1 w-full">
              <span className="font-medium">Pick stack for me</span>
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
              className="w-full"
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
  chatPlaceholder,
  isSettingUp,
  onImageAttach,
  imageAttachments,
  onRemoveImage,
  onScreenshot,
}) => (
  <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
    <div className="flex flex-wrap gap-2">
      {suggestedFollowUps.map((prompt) => (
        <button
          key={prompt}
          type="button"
          disabled={respStreaming || isSettingUp}
          onClick={() => handleChipClick(prompt)}
          className="px-3 py-1 text-sm rounded-full bg-secondary hover:bg-secondary/80 transition-colors"
        >
          {prompt}
        </button>
      ))}
    </div>
    <div className="flex flex-col gap-4">
      {imageAttachments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {imageAttachments.map((img, index) => (
            <div key={index} className="relative inline-block">
              <img
                src={img.data}
                alt={`attachment ${index + 1}`}
                className="max-h-32 max-w-[200px] object-contain rounded-lg"
              />
              <Button
                type="button"
                size="icon"
                variant="secondary"
                className="absolute top-1 right-1 h-6 w-6"
                onClick={() => onRemoveImage(index)}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}
      <div className="flex gap-4">
        <Input
          placeholder={chatPlaceholder}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1"
        />
      </div>
    </div>
    <div className="flex justify-end gap-2">
      <input
        type="file"
        id="imageInput"
        accept="image/*"
        multiple
        className="hidden"
        onChange={onImageAttach}
      />
      <Button
        type="button"
        size="icon"
        variant="outline"
        disabled={respStreaming || isSettingUp}
        onClick={onScreenshot}
      >
        <Scan className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        size="icon"
        variant="outline"
        disabled={respStreaming || isSettingUp}
        onClick={() => document.getElementById('imageInput').click()}
      >
        <ImageIcon className="h-4 w-4" />
      </Button>
      <Button type="submit" size="icon" disabled={respStreaming || isSettingUp}>
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
  const [imageAttachments, setImageAttachments] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const messagesEndRef = useRef(null);
  const [selectedEnvironment, setSelectedEnvironment] = useState(null);
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
    if (!message.trim() && imageAttachments.length === 0) return;

    onSendMessage({
      content: message,
      images: imageAttachments,
    });
    setMessage('');
    setImageAttachments([]);
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
  }, [messages]);

  const handleScroll = (e) => {
    const element = e.target;
    const isScrolledNearBottom =
      element.scrollHeight - element.scrollTop - element.clientHeight < 100;

    setAutoScroll(isScrolledNearBottom);
  };

  const handleChipClick = (prompt) => {
    onSendMessage({ content: prompt, images: imageAttachments });
  };

  const handleImageAttach = async (e) => {
    const files = Array.from(e.target.files);

    for (const file of files) {
      const img = new Image();
      const reader = new FileReader();

      await new Promise((resolve) => {
        reader.onload = (e) => {
          img.src = e.target.result;
          img.onload = () => {
            const canvas = document.createElement('canvas');
            const MAX_WIDTH = 1000;
            const MAX_HEIGHT = 1000;
            let width = img.width;
            let height = img.height;

            if (width > height) {
              if (width > MAX_WIDTH) {
                height *= MAX_WIDTH / width;
                width = MAX_WIDTH;
              }
            } else {
              if (height > MAX_HEIGHT) {
                width *= MAX_HEIGHT / height;
                height = MAX_HEIGHT;
              }
            }

            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);

            const resizedDataUrl = canvas.toDataURL(file.type, 0.7);

            setImageAttachments((prev) => [
              ...prev,
              {
                data: resizedDataUrl,
                name: file.name,
                type: file.type,
              },
            ]);
            resolve();
          };
        };
        reader.readAsDataURL(file);
      });
    }
  };

  useEffect(() => {
    if (status?.status.includes('Disconnected') && messages.length > 0) {
      const timer = setTimeout(() => {
        window.location.reload();
      }, 10000);

      return () => clearTimeout(timer);
    }
  }, [status?.status, messages.length]);

  const isSettingUp = status?.status.includes('Setting up');

  const handleRemoveImage = (index) => {
    setImageAttachments((prev) => prev.filter((_, i) => i !== index));
    // Clear the file input if all images are removed
    if (imageAttachments.length === 1) {
      const fileInput = document.getElementById('imageInput');
      if (fileInput) fileInput.value = '';
    }
  };

  const handleScreenshot = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        preferCurrentTab: true,
        video: {
          displaySurface: 'browser',
        },
      });

      // Create video element to capture the stream
      const video = document.createElement('video');
      video.srcObject = stream;

      // Wait for the video to load metadata
      await new Promise((resolve) => {
        video.onloadedmetadata = resolve;
      });
      video.play();

      // Create canvas and draw the video frame
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);

      // Stop all tracks
      stream.getTracks().forEach((track) => track.stop());

      // Resize the screenshot if needed
      const MAX_WIDTH = 1000;
      const MAX_HEIGHT = 1000;
      let width = canvas.width;
      let height = canvas.height;

      if (width > height) {
        if (width > MAX_WIDTH) {
          height *= MAX_WIDTH / width;
          width = MAX_WIDTH;
        }
      } else {
        if (height > MAX_HEIGHT) {
          width *= MAX_HEIGHT / height;
          height = MAX_HEIGHT;
        }
      }

      // Create resized canvas
      const resizedCanvas = document.createElement('canvas');
      resizedCanvas.width = width;
      resizedCanvas.height = height;
      const resizedCtx = resizedCanvas.getContext('2d');
      resizedCtx.drawImage(canvas, 0, 0, width, height);

      // Convert to data URL
      const dataUrl = resizedCanvas.toDataURL('image/jpeg', 0.7);

      setImageAttachments((prev) => [
        ...prev,
        {
          data: dataUrl,
          name: 'screenshot.jpg',
          type: 'image/jpeg',
        },
      ]);
    } catch (err) {
      console.error('Error taking screenshot:', err);
    }
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
        className="flex-1 overflow-auto p-4 pt-28 md:pt-4 relative"
        onScroll={handleScroll}
      >
        {!showStackPacks && messages.length <= 1 && isSettingUp && (
          <>
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">
                Booting up your development environment... ~3 minutes
              </p>
            </div>
          </>
        )}
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
          isSettingUp={isSettingUp}
          suggestedFollowUps={
            suggestedFollowUps &&
            suggestedFollowUps.length > 0 &&
            messages.length > 0
              ? suggestedFollowUps
              : STARTER_PROMPTS
          }
          chatPlaceholder={
            suggestedFollowUps &&
            suggestedFollowUps.length > 0 &&
            messages.length > 0
              ? suggestedFollowUps[0]
              : 'What would you like to build?'
          }
          onImageAttach={handleImageAttach}
          imageAttachments={imageAttachments}
          onRemoveImage={handleRemoveImage}
          onScreenshot={handleScreenshot}
        />
      </div>
    </div>
  );
}
