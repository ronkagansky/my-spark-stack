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

const indeterminateAnimation = `
@keyframes indeterminate {
  0% {
    transform: translateX(-200%);
  }
  50% {
    transform: translateX(0%);
  }
  100% {
    transform: translateX(200%);
  }
}
`;

// Add the styles to the document
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = indeterminateAnimation;
  document.head.appendChild(style);
}

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
  } else if (command.startsWith('ls ')) {
    shownCommand = `Listing ${command.slice(3)}...`;
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
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
    }, 60000); // 1 minute in milliseconds

    return () => clearTimeout(timer);
  }, []);

  if (!visible) return null;

  return (
    <div className="w-full mt-2 mb-2">
      <div className="relative">
        <span className="inline-block px-2 py-1 bg-blue-500 text-white rounded-t-md">
          Applying...
        </span>
        <div className="h-2 bg-gray-200 rounded-b-full overflow-hidden">
          <div
            className="h-full bg-blue-500 animate-[indeterminate_3s_ease-in-out_infinite]"
            style={{
              width: '50%',
              backgroundImage:
                'linear-gradient(to right, transparent 0%, #3B82F6 50%, transparent 100%)',
            }}
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
