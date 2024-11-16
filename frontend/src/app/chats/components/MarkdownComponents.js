'use client';

import { useState } from 'react';
import Editor from '@monaco-editor/react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

function getLanguageFromFilename(filename) {
  const extension = filename.split('.').pop().toLowerCase();
  const languageMap = {
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    py: 'python',
    json: 'json',
    md: 'markdown',
    css: 'css',
    html: 'html',
    yml: 'yaml',
    yaml: 'yaml',
    xml: 'xml',
    sql: 'sql',
    sh: 'shell',
    bash: 'shell',
    txt: 'plaintext',
  };
  return languageMap[extension] || 'plaintext';
}

export function FileUpdate({ children }) {
  const [isOpen, setIsOpen] = useState(false);

  const data = JSON.parse(atob(children));

  const handleClick = async () => {
    setIsOpen(true);
  };

  return (
    <>
      <div
        onClick={handleClick}
        className="inline-block px-2 py-1 mt-2 mb-2 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-md cursor-pointer transition-all duration-300 hover:bg-gradient-to-r hover:from-blue-500 hover:to-purple-500"
      >
        {data.filename}
      </div>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-[90vw] h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{data.filename}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-hidden">
            <Editor
              height="100%"
              defaultLanguage={getLanguageFromFilename(data.filename)}
              value={data.content}
              theme="vs-dark"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                lineNumbersMinChars: 3,
                lineDecorationsWidth: 0,
                scrollBeyondLastLine: false,
              }}
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export const components = {
  'file-update': FileUpdate,
};
