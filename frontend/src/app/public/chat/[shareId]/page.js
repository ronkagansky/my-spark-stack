'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { components } from '@/app/chats/components/MarkdownComponents';
import { fixCodeBlocks } from '@/lib/code';

export default function PublicChatPage() {
  const { shareId } = useParams();
  const [chat, setChat] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchChat = async () => {
      try {
        const response = await api.getPublicChat(shareId);
        if (!response || !response.id) {
          throw new Error('Invalid chat data received');
        }
        setChat(response);
      } catch (err) {
        console.error('Error fetching chat:', err);
        setError('This chat is not available or has been removed');
      }
    };
    fetchChat();
  }, [shareId]);

  if (error) {
    return (
      <div className="container mx-auto p-4">
        <Card className="p-6">
          <h1 className="text-2xl font-bold text-red-500 mb-2">Error</h1>
          <p>{error}</p>
        </Card>
      </div>
    );
  }

  if (!chat) {
    return (
      <div className="container mx-auto p-4">
        <Card className="p-6">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <Card className="p-6">
        <h1 className="text-2xl font-bold mb-4">{chat.name}</h1>
        <div className="text-sm text-muted-foreground mb-4">
          Project: {chat.project?.name}
        </div>
        <ScrollArea className="h-[600px] pr-4">
          <div className="space-y-4">
            {chat.messages?.map((message, index) => (
              <div key={index} className="flex items-start gap-4">
                <div
                  className={`w-8 h-8 rounded ${
                    message.role === 'user' ? 'bg-blue-500/10' : 'bg-primary/10'
                  } flex-shrink-0 flex items-center justify-center text-sm font-medium ${
                    message.role === 'user' ? 'text-blue-500' : 'text-primary'
                  }`}
                >
                  {message.role === 'user' ? 'H' : 'AI'}
                </div>
                <div className="flex-1">
                  <div className="mt-1 prose prose-sm max-w-[80%]">
                    {message.images && message.images.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-4">
                        {message.images.map((img, imgIndex) => (
                          <img
                            key={imgIndex}
                            src={img}
                            alt={`Message attachment ${imgIndex + 1}`}
                            className="max-h-48 max-w-[300px] object-contain rounded-lg"
                          />
                        ))}
                      </div>
                    )}
                    {!message.content && message.thinking_content && (
                      <div className="prose prose-sm max-w-none">
                        <div className="inline-block px-2 py-1 mb-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-md animate-pulse">
                          {[
                            ...message.thinking_content.matchAll(
                              /### ([\s\S]+?)\n/g
                            ),
                          ].at(-1)?.[1] || 'Thinking...'}
                        </div>
                      </div>
                    )}
                    <ReactMarkdown
                      components={components}
                      rehypePlugins={[rehypeRaw]}
                      remarkPlugins={[remarkGfm]}
                      className="max-w-[80%]"
                    >
                      {fixCodeBlocks(message.content, false)}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </Card>
    </div>
  );
}
