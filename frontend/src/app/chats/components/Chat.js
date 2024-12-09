'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import {
  SendIcon,
  Loader2,
  ImageIcon,
  X,
  Scan,
  RefreshCw,
  Pencil,
  Mic,
  MicOff,
} from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
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
import { SketchDialog } from './SketchDialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

const STARTER_PROMPTS = [
  'Build a 90s themed cat facts app with catfact.ninja API',
  'Build a modern control panel for a spaceship',
];

const EmptyState = ({
  selectedStack,
  stacks,
  onStackSelect,
  selectedProject,
  projects,
  onProjectSelect,
}) => (
  <div className="flex flex-col items-center justify-center h-full">
    <div className="max-w-md w-full space-y-4">
      <Select
        value={selectedProject}
        onValueChange={(value) => {
          onProjectSelect(value);
        }}
      >
        <SelectTrigger className="w-full py-10">
          <SelectValue placeholder="Select a Project" />
        </SelectTrigger>
        <SelectContent className="max-h-[500px] w-full">
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
          <SelectTrigger className="w-full py-10">
            <SelectValue placeholder="Select a Stack" />
          </SelectTrigger>
          <SelectContent className="max-h-[500px] w-full">
            {[
              {
                id: null,
                title: 'Auto Stack',
                description:
                  'Let AI choose the best stack based on your first prompt in the current chat.',
              },
            ]
              .concat(stacks ?? [])
              .map((pack) => (
                <SelectItem key={pack.id} value={pack.id} className="py-2">
                  <div className="flex flex-col gap-1 max-w-[calc(100vw-4rem)]">
                    <span className="font-medium truncate">{pack.title}</span>
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
            msg.role === 'user' ? 'bg-blue-500/10' : 'bg-primary/10'
          } flex-shrink-0 flex items-center justify-center text-sm font-medium ${
            msg.role === 'user' ? 'text-blue-500' : 'text-primary'
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

const ImageAttachments = ({ attachments, onRemove }) => (
  <div className="flex flex-wrap gap-2">
    {attachments.map((img, index) => (
      <div key={index} className="relative inline-block">
        <img
          src={img}
          alt={`attachment ${index + 1}`}
          className="max-h-32 max-w-[200px] object-contain rounded-lg"
        />
        <Button
          type="button"
          size="icon"
          variant="secondary"
          className="absolute top-1 right-1 h-6 w-6"
          onClick={() => onRemove(index)}
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    ))}
  </div>
);

const ChatInput = ({
  disabled,
  message,
  setMessage,
  handleSubmit,
  handleKeyDown,
  handleChipClick,
  suggestedFollowUps,
  chatPlaceholder,
  onImageAttach,
  imageAttachments,
  onRemoveImage,
  onScreenshot,
  uploadingImages,
  status,
  onReconnect,
  onSketchSubmit,
  messages,
}) => {
  const [sketchOpen, setSketchOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const recognition = useRef(null);

  useEffect(() => {
    if (window.webkitSpeechRecognition) {
      recognition.current = new window.webkitSpeechRecognition();
      recognition.current.continuous = true;
      recognition.current.interimResults = true;

      recognition.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0].transcript)
          .join('');
        setMessage(transcript);
      };

      recognition.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognition.current.onend = () => {
        setIsListening(false);
      };
    }

    return () => {
      if (recognition.current) {
        recognition.current.stop();
      }
    };
  }, []);

  const toggleListening = () => {
    if (!recognition.current) {
      alert('Speech recognition is not supported in your browser');
      return;
    }

    if (isListening) {
      recognition.current.stop();
      setIsListening(false);
    } else {
      recognition.current.start();
      setIsListening(true);
    }
  };

  const getDisabledReason = () => {
    if (uploadingImages) {
      return 'Uploading images...';
    } else if (status === 'WORKING') {
      return 'Please wait for the AI to finish...';
    } else if (status === 'WORKING_APPLYING') {
      return 'Please wait for the changes to be applied...';
    } else if (disabled) {
      if (status === 'BUILDING' || status === 'BUILDING_WAITING') {
        return 'Please wait while the development environment is being set up...';
      }
      return 'Chat is temporarily unavailable';
    }
    return null;
  };

  const isLongConversation = messages.length > 40;

  return (
    <>
      <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
        {disabled ||
        uploadingImages ||
        ['WORKING', 'WORKING_APPLYING'].includes(status) ? (
          <p className="text-sm text-muted-foreground">{getDisabledReason()}</p>
        ) : (
          <div className="flex flex-col md:flex-row flex-wrap gap-2">
            {suggestedFollowUps.map((prompt) => (
              <button
                key={prompt}
                type="button"
                disabled={disabled}
                onClick={() => handleChipClick(prompt)}
                className="w-10/12 md:w-auto px-3 py-1.5 text-sm rounded-full bg-secondary hover:bg-secondary/80 transition-colors text-left"
              >
                <span className="block truncate md:truncate-none">
                  {prompt}
                </span>
              </button>
            ))}
          </div>
        )}
        <div className="flex flex-col gap-4">
          {imageAttachments.length > 0 && (
            <ImageAttachments
              attachments={imageAttachments}
              onRemove={onRemoveImage}
            />
          )}
          <div className="flex gap-4">
            <Textarea
              placeholder={chatPlaceholder}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 min-h-[40px] max-h-[200px] resize-none"
              rows={Math.min(message.split('\n').length, 5)}
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
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  disabled={disabled}
                  onClick={onScreenshot}
                >
                  <Scan className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Take screenshot</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  disabled={disabled}
                  onClick={() => document.getElementById('imageInput').click()}
                >
                  <ImageIcon className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Upload image</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  disabled={disabled}
                  onClick={() => setSketchOpen(true)}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Draw sketch</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  size="icon"
                  variant={isListening ? 'destructive' : 'outline'}
                  disabled={disabled}
                  onClick={toggleListening}
                >
                  {isListening ? (
                    <MicOff className="h-4 w-4" />
                  ) : (
                    <Mic className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {isListening ? 'Stop recording' : 'Start recording'}
              </TooltipContent>
            </Tooltip>

            {status === 'DISCONNECTED' ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    onClick={onReconnect}
                    variant="destructive"
                    className="flex items-center gap-2"
                  >
                    <span>Reconnect</span>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Reconnect to server</TooltipContent>
              </Tooltip>
            ) : (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="submit"
                    size="icon"
                    disabled={disabled || uploadingImages}
                    variant={isLongConversation ? 'destructive' : 'default'}
                  >
                    {uploadingImages ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <SendIcon className="h-4 w-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {isLongConversation
                    ? 'Warning: Long conversations may be less effective. Consider starting a new chat in the same project.'
                    : 'Send message'}
                </TooltipContent>
              </Tooltip>
            )}
          </TooltipProvider>
        </div>
      </form>

      <SketchDialog
        open={sketchOpen}
        onOpenChange={setSketchOpen}
        onSave={onSketchSubmit}
      />
    </>
  );
};

const fixCodeBlocks = (content, partial) => {
  const replaceB64 = (_, filename, content) => {
    const b64 = Buffer.from(JSON.stringify({ filename, content })).toString(
      'base64'
    );
    return `<file-update>${b64}</file-update>`;
  };

  content = content.replace(
    /```[\w.]+\n[#/]+ (\S+)\n([\s\S]+?)```/g,
    replaceB64
  );
  content = content.replace(
    /```[\w.]+\n[/*]+ (\S+) \*\/\n([\s\S]+?)```/g,
    replaceB64
  );
  content = content.replace(
    /```[\w.]+\n<!-- (\S+) -->\n([\s\S]+?)```/g,
    replaceB64
  );
  if (partial) {
    content = content.replace(
      /```[\s\S]+$/,
      '<file-loading>...</file-loading>'
    );
  }
  return content;
};

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

  return (
    <div className="flex-1 flex flex-col md:max-w-[80%] md:mx-auto w-full h-[100dvh]">
      <div className="sticky top-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-10 border-b">
        <div className="px-4 py-2.5 pt-16 md:pt-2.5 flex items-center justify-between gap-4">
          <h1 className="text-base font-semibold truncate">{projectTitle}</h1>
          <div className="flex items-center gap-2 flex-shrink-0">
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
      <div
        className="flex-1 overflow-y-auto p-4 relative"
        onScroll={handleScroll}
      >
        {!showStackPacks &&
          messages.length <= 1 &&
          ['BUILDING', 'OFFLINE', 'BUILDING_WAITING'].includes(status) && (
            <>
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">
                  Booting up your development environment...
                </p>
              </div>
            </>
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
          disabled={!['NEW_CHAT', 'READY'].includes(status)}
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
        />
      </div>
    </div>
  );
}
