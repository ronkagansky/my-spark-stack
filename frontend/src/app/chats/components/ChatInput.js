'use client';

import { useState, useRef, useEffect } from 'react';
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { SketchDialog } from './SketchDialog';

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

export function ChatInput({
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
  isSubmitting,
}) {
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
    } else if (isSubmitting) {
      return 'Creating your new chat...';
    } else if (status === 'WORKING') {
      return 'Please wait for the AI to finish...';
    } else if (status === 'WORKING_APPLYING') {
      return 'Please wait for the changes to be applied...';
    } else if (disabled) {
      if (status === 'BUILDING' || status === 'BUILDING_WAITING') {
        return 'Please wait while the project is being set up...';
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
        isSubmitting ||
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
                    disabled={disabled || uploadingImages || isSubmitting}
                    variant={isLongConversation ? 'destructive' : 'default'}
                  >
                    {uploadingImages || isSubmitting ? (
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
}
