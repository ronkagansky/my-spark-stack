'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Loader2, X, Share2, Link } from 'lucide-react';
import rehypeRaw from 'rehype-raw';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useUser } from '@/context/user-context';
import { api, uploadImage } from '@/lib/api';
import { resizeImage, captureScreenshot } from '@/lib/image';
import { components } from '@/app/chats/components/MarkdownComponents';
import { fixCodeBlocks } from '@/lib/code';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useShareChat } from '@/hooks/use-share-chat';
import { Progress } from '@/components/ui/progress';
import { ChatInput } from './ChatInput';

const STARTER_PROMPTS = [
  'Build a 90s themed cat facts app with catfact.ninja API',
  'Build a modern control panel for a spaceship',
  'Build a unique p5.js asteroid game',
];

const EmptyState = ({
  selectedStack,
  stacks,
  onStackSelect,
  selectedProject,
  projects,
  onProjectSelect,
}) => (
  <div className="flex flex-col items-center justify-center min-h-0 h-full overflow-hidden">
    <div className="max-w-md w-full space-y-4 px-4 sm:px-6">
      <Select
        value={selectedProject}
        onValueChange={(value) => {
          onProjectSelect(value);
        }}
      >
        <SelectTrigger className="w-full py-10 md:py-12">
          <SelectValue placeholder="Select a Project" />
        </SelectTrigger>
        <SelectContent className="max-h-[40vh] w-full overflow-y-auto">
          {[
            {
              id: null,
              name: 'New Project',
              description:
                'Start a new project from scratch. The project will be created after your first chat.',
            },
          ]
            .concat(projects ?? [])
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .map((project) => (
              <SelectItem key={project.id} value={project.id} className="py-2">
                <div className="flex flex-col gap-1 max-w-[calc(100vw-4rem)]">
                  <span className="font-medium truncate">{project.name}</span>
                  <p className="text-sm text-muted-foreground break-words whitespace-normal max-w-full">
                    {project.description}
                  </p>
                </div>
              </SelectItem>
            ))}
        </SelectContent>
      </Select>

      {selectedProject === null && (
        <Select
          value={selectedStack}
          onValueChange={(value) => {
            onStackSelect(value);
          }}
        >
          <SelectTrigger className="w-full py-10 md:py-12">
            <SelectValue placeholder="Select a Stack" />
          </SelectTrigger>
          <SelectContent className="max-h-[40vh] w-full overflow-y-auto">
            {[
              {
                id: null,
                title: 'Auto',
                description:
                  'Let AI choose the best set of tools based on your first prompt in the current chat.',
              },
            ]
              .concat(stacks ?? [])
              .map((pack) => (
                <SelectItem key={pack.id} value={pack.id} className="py-2">
                  <div className="flex flex-col gap-1 max-w-[calc(100vw-4rem)]">
                    <span className="font-medium truncate">
                      {pack.title}
                      {(pack.title === 'Next.js Shadcn' ||
                        pack.title === 'p5.js') &&
                        ' ⭐'}
                    </span>
                    <p className="text-sm text-muted-foreground break-words whitespace-normal max-w-full">
                      {pack.description}
                    </p>
                  </div>
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
      )}
    </div>
  </div>
);

const ThinkingContent = ({ thinkingContent }) => {
  let lastHeader = [...thinkingContent.matchAll(/### ([\s\S]+?)\n/g)].at(
    -1
  )?.[1];
  return (
    <div className="prose prose-sm max-w-none ">
      <div className="inline-block px-2 py-1 mb-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-md animate-pulse">
        {lastHeader || 'Thinking...'}
      </div>
    </div>
  );
};

const MessageList = ({ messages, status }) => (
  <div className="space-y-4">
    {messages.map((msg, index) => (
      <div key={index} className="flex items-start gap-4">
        <div
          className={`w-8 h-8 rounded ${
            msg.role === 'user' ? 'bg-orange-500/10' : 'bg-primary/10'
          } flex-shrink-0 flex items-center justify-center text-sm font-medium ${
            msg.role === 'user' ? 'text-orange-500' : 'text-primary'
          }`}
        >
          {msg.role === 'user' ? 'H' : 'AI'}
        </div>
        <div className="flex-1">
          <div className="mt-1 prose prose-sm max-w-[80%]">
            {msg.images && msg.images.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {msg.images.map((img, imgIndex) => (
                  <img
                    key={imgIndex}
                    src={img}
                    alt={`Message attachment ${imgIndex + 1}`}
                    className="max-h-48 max-w-[300px] object-contain rounded-lg"
                  />
                ))}
              </div>
            )}
            {!msg.content && msg.thinking_content && (
              <ThinkingContent thinkingContent={msg.thinking_content} />
            )}
            <ReactMarkdown
              components={components}
              rehypePlugins={[rehypeRaw]}
              remarkPlugins={[remarkGfm]}
              className="max-w-[80%]"
            >
              {fixCodeBlocks(msg.content, status === 'WORKING')}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    ))}
  </div>
);

const statusMap = {
  NEW_CHAT: { status: 'Ready', color: 'bg-gray-500', animate: false },
  DISCONNECTED: {
    status: 'Disconnected',
    color: 'bg-gray-500',
    animate: false,
  },
  OFFLINE: { status: 'Offline', color: 'bg-gray-500', animate: false },
  BUILDING: {
    status: 'Setting up (~1m)',
    color: 'bg-yellow-500',
    animate: true,
  },
  BUILDING_WAITING: {
    status: 'Setting up (~3m)',
    color: 'bg-yellow-500',
    animate: true,
  },
  READY: { status: 'Ready', color: 'bg-green-500', animate: false },
  WORKING: { status: 'Coding...', color: 'bg-green-500', animate: true },
  WORKING_APPLYING: {
    status: 'Applying...',
    color: 'bg-green-500',
    animate: true,
  },
  CONNECTING: {
    status: 'Connecting...',
    color: 'bg-yellow-500',
    animate: true,
  },
};

const LoadingState = () => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const duration = 60000; // 1 minutes in milliseconds
    const interval = 100; // Update every 100ms
    const increment = (interval / duration) * 100;

    const timer = setInterval(() => {
      setProgress((prev) => {
        const next = prev + increment;
        return next >= 100 ? 100 : next;
      });
    }, interval);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">Setting things up...</p>
      <div className="w-64">
        <Progress value={progress} className="h-2" />
      </div>
    </div>
  );
};

export function Chat({
  messages,
  onSendMessage,
  projectTitle,
  status,
  onStackSelect,
  onProjectSelect,
  showStackPacks = false,
  suggestedFollowUps = [],
  onReconnect,
  chat,
  isSubmitting,
}) {
  const { projects } = useUser();
  const [message, setMessage] = useState('');
  const [imageAttachments, setImageAttachments] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const messagesEndRef = useRef(null);
  const [selectedStack, setSelectedStack] = useState(null);
  const [stacks, setStackPacks] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [uploadingImages, setUploadingImages] = useState(false);
  const { sharingChatId, handleShare: shareChat } = useShareChat();

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
    // Check for Ctrl/Cmd + Enter for new line
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      return; // Allow default behavior (new line)
    }

    // Submit on plain Enter
    if (e.key === 'Enter' && !e.shiftKey) {
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
    setUploadingImages(true);
    try {
      const processedImages = await Promise.all(
        files.map(async (file) => {
          const resizedImage = await resizeImage(file);
          return uploadImage(resizedImage.data, resizedImage.type);
        })
      );
      setImageAttachments((prev) => [...prev, ...processedImages]);
    } catch (err) {
      console.error('Error processing image:', err);
    } finally {
      setUploadingImages(false);
    }
  };

  const handleRemoveImage = (index) => {
    setImageAttachments((prev) => prev.filter((_, i) => i !== index));
    // Clear the file input if all images are removed
    if (imageAttachments.length === 1) {
      const fileInput = document.getElementById('imageInput');
      if (fileInput) fileInput.value = '';
    }
  };

  const handleScreenshot = async () => {
    setUploadingImages(true);
    try {
      const screenshot = await captureScreenshot();
      const url = await uploadImage(screenshot.data, screenshot.type);
      setImageAttachments((prev) => [...prev, url]);
    } catch (err) {
      console.error('Error taking/uploading screenshot:', err);
    } finally {
      setUploadingImages(false);
    }
  };

  const handleStackSelect = (stack) => {
    setSelectedStack(stack);
    onStackSelect(stack);
  };

  const handleProjectSelect = (project) => {
    setSelectedProject(project);
    setSelectedStack(null);
    onProjectSelect(project);
  };

  const handleSketchSubmit = async (sketchDataUrl) => {
    setUploadingImages(true);
    try {
      const url = await uploadImage(sketchDataUrl, 'image/png');
      setImageAttachments((prev) => [...prev, url]);
    } catch (err) {
      console.error('Error uploading sketch:', err);
    } finally {
      setUploadingImages(false);
    }
  };

  const handleShare = () => {
    if (chat) {
      shareChat(chat);
    }
  };

  return (
    <div className="flex-1 flex flex-col md:max-w-[80%] md:mx-auto w-full h-[100dvh]">
      <div className="sticky top-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-10 border-b">
        <div className="px-8 py-2.5 pt-16 md:pt-2.5 flex items-center justify-between gap-4">
          <h1 className="text-base font-semibold truncate">{projectTitle}</h1>
          <div className="flex items-center gap-4 flex-shrink-0">
            {chat?.id && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={handleShare}
                      disabled={sharingChatId === chat.id}
                    >
                      {sharingChatId === chat.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : chat.is_public ? (
                        <Link className="h-4 w-4" />
                      ) : (
                        <Share2 className="h-4 w-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {chat.is_public ? 'Unshare chat' : 'Share chat'}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${statusMap[status].color} ${
                  statusMap[status].animate ? 'animate-pulse' : ''
                }`}
              />
              <span className="text-sm text-muted-foreground capitalize">
                {statusMap[status].status}
              </span>
            </div>
          </div>
        </div>
      </div>
      <div
        className="flex-1 overflow-y-auto p-4 relative"
        onScroll={handleScroll}
      >
        {!showStackPacks &&
          messages.length <= 1 &&
          ['BUILDING', 'OFFLINE', 'BUILDING_WAITING'].includes(status) && (
            <LoadingState />
          )}
        {messages.length === 0 && showStackPacks ? (
          <EmptyState
            selectedStack={selectedStack}
            stacks={stacks}
            onStackSelect={handleStackSelect}
            selectedProject={selectedProject}
            projects={projects}
            onProjectSelect={handleProjectSelect}
          />
        ) : (
          <MessageList messages={messages} status={status} />
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="border-t p-4">
        <ChatInput
          disabled={!['NEW_CHAT', 'READY'].includes(status) || isSubmitting}
          message={message}
          setMessage={setMessage}
          handleSubmit={handleSubmit}
          handleKeyDown={handleKeyDown}
          handleChipClick={handleChipClick}
          status={status}
          onReconnect={onReconnect}
          suggestedFollowUps={
            suggestedFollowUps && suggestedFollowUps.length > 0
              ? suggestedFollowUps
              : messages.length === 0
              ? STARTER_PROMPTS
              : []
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
          uploadingImages={uploadingImages}
          onSketchSubmit={handleSketchSubmit}
          messages={messages}
          isSubmitting={isSubmitting}
        />
      </div>
    </div>
  );
}
