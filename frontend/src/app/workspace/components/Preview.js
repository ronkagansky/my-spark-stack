'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { XIcon } from 'lucide-react';
import { PreviewTab } from './PreviewTab';
import { EditorTab } from './EditorTab';

export function Preview({
  isOpen,
  onClose,
  projectPreviewUrl,
  projectFileTree,
}) {
  const [selectedTab, setSelectedTab] = useState('preview');

  return (
    <div
      className={`${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      } md:translate-x-0 fixed md:static right-0 top-0 h-screen w-full md:w-[600px] border-l bg-background transition-transform duration-200 ease-in-out z-30`}
    >
      <div className="p-4 pl-16 md:pl-4 border-b flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant={selectedTab === 'preview' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setSelectedTab('preview')}
          >
            Preview
          </Button>
          <Button
            variant={selectedTab === 'editor' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setSelectedTab('editor')}
          >
            Editor
          </Button>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="md:hidden"
          onClick={onClose}
        >
          <XIcon className="h-4 w-4" />
        </Button>
      </div>
      <div className="p-4">
        <div className="rounded-lg border bg-muted/40 h-[calc(100vh-8rem)]">
          {selectedTab === 'preview' ? (
            <PreviewTab projectPreviewUrl={projectPreviewUrl} />
          ) : (
            <EditorTab projectFileTree={projectFileTree} />
          )}
        </div>
      </div>
    </div>
  );
}
