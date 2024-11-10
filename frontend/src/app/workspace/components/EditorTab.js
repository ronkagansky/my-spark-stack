'use client';

import Editor from '@monaco-editor/react';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export function EditorTab({ projectFileTree, projectId }) {
  const defaultFile = '/app/my-app/src/App.js';
  const [selectedFile, setSelectedFile] = useState(() =>
    projectFileTree.includes(defaultFile) ? defaultFile : null
  );
  const [fileContent, setFileContent] = useState('');

  // Load default file content on mount if it exists
  useEffect(() => {
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  }, []);

  const handleFileSelect = async (filename) => {
    if (!filename) return;
    setSelectedFile(filename);
    try {
      const response = await api.getProjectFile(projectId, filename);
      setFileContent(response.content);
    } catch (error) {
      console.error('Error loading file:', error);
      setFileContent('Error loading file content');
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-2">
        <select
          className="w-full h-10 px-3 py-2 text-sm rounded-md border border-input bg-background ring-offset-background 
            focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2
            disabled:cursor-not-allowed disabled:opacity-50"
          value={selectedFile || ''}
          onChange={(e) => handleFileSelect(e.target.value)}
        >
          <option value="" className="text-muted-foreground">
            Select a file...
          </option>
          {projectFileTree.map((path) => (
            <option key={path} value={path} className="text-foreground">
              {path}
            </option>
          ))}
        </select>
      </div>
      <div className="flex-1">
        {selectedFile ? (
          <Editor
            height="100%"
            defaultLanguage="typescript"
            value={fileContent}
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
