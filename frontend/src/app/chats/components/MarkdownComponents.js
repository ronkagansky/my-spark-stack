'use client';

import { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { getLanguageFromFilename } from '@/lib/utils';

export function FileUpdate({ children }) {
  const [isOpen, setIsOpen] = useState(false);

  const data = JSON.parse(atob(children));

  const handleClick = async () => {
    setIsOpen(true);
  };

  return (
    <>
      <span
        onClick={handleClick}
        className="inline-block max-w-[75vw] truncate px-2 py-1 mt-2 mb-2 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-md cursor-pointer transition-all duration-300 hover:bg-gradient-to-r hover:from-blue-500 hover:to-purple-500"
      >
        {data.filename}
      </span>

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

function FileLoading() {
  return (
    <span className="inline-block px-2 py-1 mt-2 mb-2 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-md animate-gradient bg-[length:200%_200%]">
      ...
    </span>
  );
}

function ShellCommand({ children }) {
  const [isOpen, setIsOpen] = useState(false);
  const data = JSON.parse(atob(children));
  const command = JSON.parse(data.content).command;

  let shownCommand = command;
  if (command.startsWith('cat ')) {
    shownCommand = `Reading ${command.slice(4)}...`;
  }

  const handleClick = () => {
    setIsOpen(true);
  };

  return (
    <>
      <span
        onClick={handleClick}
        className="inline-block max-w-[75vw] truncate px-2 py-1 mt-2 mb-2 bg-gradient-to-r from-emerald-400 to-teal-400 text-white rounded-md cursor-pointer transition-all duration-300 hover:bg-gradient-to-r hover:from-teal-500 hover:to-emerald-500"
      >
        {shownCommand.length > 30
          ? `${shownCommand.slice(0, 30)}...`
          : shownCommand}
      </span>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-[90vw] h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Shell Command</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-hidden">
            <Editor
              height="100%"
              defaultLanguage="shell"
              value={command}
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
function ApplyChanges({ children }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const startTime = Date.now();
    const duration = 30000; // 30 seconds

    const intervalId = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const newProgress = Math.min((elapsed / duration) * 100, 100);

      setProgress(newProgress);

      if (newProgress >= 100) {
        clearInterval(intervalId);
      }
    }, 250); // Update every 0.25 seconds

    return () => clearInterval(intervalId);
  }, []);
  return (
    <div className="w-full mt-2 mb-2">
      <div className="relative">
        <span className="inline-block px-2 py-1 bg-blue-500 text-white rounded-t-md">
          Applying...
        </span>
        <div className="h-2 bg-gray-200 rounded-b-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-100 ease-linear"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}

export const components = {
  'file-update': FileUpdate,
  'file-loading': FileLoading,
  'tool-run-shell-cmd': ShellCommand,
  'tool-apply-changes': ApplyChanges,
};
