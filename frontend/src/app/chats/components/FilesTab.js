'use client';

import Editor from '@monaco-editor/react';
import { useState, useEffect, useMemo } from 'react';
import { api } from '@/lib/api';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import {
  ChevronRight,
  ChevronDown,
  File,
  PanelLeftClose,
  PanelLeft,
  Download,
} from 'lucide-react';
import { useUser } from '@/context/user-context';
import { getLanguageFromFilename } from '@/lib/utils';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useToast } from '@/hooks/use-toast';

const FileTreeNode = ({ name, children, level = 0, onSelect, isSelected }) => {
  const [isOpen, setIsOpen] = useState(false);
  const hasChildren = children && Object.keys(children).length > 0;

  const handleClick = () => {
    if (hasChildren) {
      setIsOpen(!isOpen);
    } else {
      onSelect(name);
    }
  };

  return (
    <div>
      <div
        className={cn(
          'flex items-center py-1 px-2 hover:bg-accent rounded-md cursor-pointer text-sm',
          isSelected && !hasChildren && 'bg-accent'
        )}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={handleClick}
      >
        {hasChildren ? (
          isOpen ? (
            <ChevronDown className="h-4 w-4 shrink-0 mr-1" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 mr-1" />
          )
        ) : (
          <File className="h-4 w-4 shrink-0 mr-1" />
        )}
        <span className="truncate">
          {name.startsWith('/app/')
            ? name.split('/app/')[1]
            : name.split('/').pop()}
        </span>
      </div>
      {hasChildren && isOpen && (
        <div>
          {Object.entries(children).map(([childName, childValue]) => (
            <FileTreeNode
              key={childName}
              name={`${name}/${childName}`}
              children={childValue}
              level={level + 1}
              onSelect={onSelect}
              isSelected={isSelected}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export function FilesTab({ projectFileTree, project }) {
  const { team } = useUser();
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTreeCollapsed, setIsTreeCollapsed] = useState(false);
  const [treeWidth, setTreeWidth] = useState(400);
  const [isResizing, setIsResizing] = useState(false);
  const { toast } = useToast();

  const fileTree = useMemo(() => {
    const tree = {};
    projectFileTree.forEach((path) => {
      if (!path.startsWith('/app/')) return;

      const relativePath = path.substring(5);
      const parts = relativePath.split('/');

      let current = tree;
      parts.forEach((part, i) => {
        if (i === parts.length - 1) {
          current[part] = null;
        } else {
          current[part] = current[part] || {};
          current = current[part];
        }
      });
    });
    return tree;
  }, [projectFileTree]);

  const handleFileSelect = async (filename) => {
    if (!filename || !team || !project) return;
    setSelectedFile(filename);
    setIsLoading(true);
    setTreeWidth(200);
    try {
      const response = await api.getProjectFile(team.id, project.id, filename);
      setFileContent(response.content);
    } catch (error) {
      console.error('Error loading file:', error);
      setFileContent('Error loading file content');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleTree = () => {
    if (isTreeCollapsed && selectedFile) {
      handleFileSelect(selectedFile);
    }
    setIsTreeCollapsed(!isTreeCollapsed);
  };

  const handleMouseDown = (e) => {
    e.preventDefault();
    setIsResizing(true);
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      const newWidth = Math.max(160, Math.min(400, e.clientX));
      setTreeWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const handleDownload = async () => {
    if (!team || !project) return;
    try {
      const { url } = await api.zipProject(team.id, project.id);
      window.open(url, '_blank');
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Download failed',
        description:
          'Failed to download project files. Please try again later.',
      });
      console.error('Error downloading project:', error);
    }
  };

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <div className="flex-1 flex rounded-lg border bg-background shadow-sm min-h-0">
        <div
          className={cn(
            'border-r flex-shrink-0 transition-all duration-300 ease-in-out min-h-0',
            isTreeCollapsed ? 'w-0 overflow-hidden' : ''
          )}
          style={{ width: isTreeCollapsed ? 0 : treeWidth }}
        >
          <div className="h-full flex flex-col min-h-0">
            <div className="p-3 border-b flex items-center justify-between bg-muted/40 flex-shrink-0">
              <span className="text-sm font-medium">Files</span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={handleDownload}
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      disabled={!project}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>
                      {project ? 'Download Project' : 'No project selected'}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <ScrollArea className="flex-1 min-h-0">
              <div className="p-3">
                {Object.entries(fileTree).map(([name, children]) => (
                  <FileTreeNode
                    key={name}
                    name={name}
                    children={children}
                    onSelect={handleFileSelect}
                    isSelected={selectedFile === name}
                  />
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>
        <div
          className={cn(
            'flex items-center justify-center transition-all duration-300 ease-in-out',
            isTreeCollapsed
              ? 'w-12 border-r hover:bg-accent/10'
              : 'w-4 hover:bg-accent cursor-col-resize border-x'
          )}
          onMouseDown={!isTreeCollapsed ? handleMouseDown : undefined}
        >
          <div
            className={cn(
              'flex items-center justify-center',
              isTreeCollapsed ? 'w-full h-full p-2' : 'w-full h-8'
            )}
          >
            <Button
              variant="ghost"
              size="icon"
              className={cn('h-8 w-8', isTreeCollapsed && 'hover:bg-accent/20')}
              onClick={toggleTree}
            >
              {isTreeCollapsed ? (
                <PanelLeft className="h-4 w-4" />
              ) : (
                <PanelLeftClose className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
        <div className="flex-1 min-w-0">
          {selectedFile ? (
            <div className="h-full p-3">
              <Editor
                height="100%"
                defaultLanguage={getLanguageFromFilename(selectedFile)}
                value={isLoading ? 'Loading...' : fileContent}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  lineNumbersMinChars: 3,
                  lineDecorationsWidth: 0,
                }}
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Select file
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
