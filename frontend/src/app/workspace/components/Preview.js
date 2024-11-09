'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { XIcon, ChevronDownIcon } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const exampleFiles = [
  'confirmation.tsx',
  'calendar.tsx',
  'booking.tsx',
  'settings.tsx',
  'layout.tsx',
];

export function Preview({ isOpen, onClose }) {
  const [selectedFile, setSelectedFile] = useState('confirmation.tsx');

  return (
    <div
      className={`${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      } md:translate-x-0 fixed md:static right-0 top-0 h-screen w-full md:w-[600px] border-l bg-background transition-transform duration-200 ease-in-out z-30`}
    >
      <div className="p-4 pl-16 md:pl-4 border-b flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="sm">
            Preview
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="flex items-center gap-2"
              >
                {selectedFile}
                <ChevronDownIcon className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              {exampleFiles.map((file) => (
                <DropdownMenuItem
                  key={file}
                  onClick={() => setSelectedFile(file)}
                >
                  {file}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
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
          {/* Preview content will go here */}
        </div>
      </div>
    </div>
  );
}
