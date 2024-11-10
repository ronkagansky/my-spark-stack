'use client';

import Editor from '@monaco-editor/react';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export function EditorTab({ projectFileTree, projectId }) {
  const defaultFile = '/app/my-app/src/App.js';
  const [selectedFile, setSelectedFile] = useState(() =>
    projectFileTree.includes(defaultFile) ? defaultFile : null
  );
  const [fileContent, setFileContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Load default file content on mount if it exists
  useEffect(() => {
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  }, []);

  const handleFileSelect = async (filename) => {
    if (!filename) return;
    setSelectedFile(filename);
    setIsLoading(true);
    try {
      const response = await api.getProjectFile(projectId, filename);
      setFileContent(response.content);
    } catch (error) {
      console.error('Error loading file:', error);
      setFileContent('Error loading file content');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-2">
        <Select value={selectedFile || ''} onValueChange={handleFileSelect}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select a file..." />
          </SelectTrigger>
          <SelectContent>
            {projectFileTree.map((path) => (
              <SelectItem key={path} value={path}>
                {path}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex-1">
        {selectedFile ? (
          <Editor
            height="100%"
            defaultLanguage="typescript"
            value={isLoading ? 'Loading...' : fileContent}
            theme="vs-dark"
            options={{
              readOnly: true,
              minimap: { enabled: false },
              lineNumbersMinChars: 3,
              lineDecorationsWidth: 0,
            }}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            Select a file to view
          </div>
        )}
      </div>
    </div>
  );
}
