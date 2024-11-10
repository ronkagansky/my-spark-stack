'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  X as XIcon,
  ExternalLink as ExternalLinkIcon,
  RefreshCw as RefreshIcon,
  PanelRight as PanelRightIcon,
} from 'lucide-react';
import { PreviewTab } from './PreviewTab';
import { EditorTab } from './EditorTab';

export function Preview({
  isOpen,
  onClose,
  projectPreviewUrl,
  projectFileTree,
  projectId,
}) {
  const [selectedTab, setSelectedTab] = useState('preview');
  const [refreshCount, setRefreshCount] = useState(0);

  return (
    <>
      {isOpen && (
        <div className="md:hidden fixed top-4 right-4 z-40">
          <Button variant="outline" size="sm" onClick={() => onClose()}>
            <PanelRightIcon className="h-4 w-4" />
          </Button>
        </div>
      )}

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
              Files
            </Button>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              onClick={onClose}
            >
              <XIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="p-4">
          <div className="rounded-lg border bg-muted/40 h-[calc(100vh-8rem)]">
            {selectedTab === 'preview' ? (
              <PreviewTab
                projectPreviewUrl={projectPreviewUrl}
                key={refreshCount}
              />
            ) : (
              <EditorTab
                projectFileTree={projectFileTree}
                projectId={projectId}
              />
            )}
          </div>
        </div>
      </div>
    </>
  );
}
