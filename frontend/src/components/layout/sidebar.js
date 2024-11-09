'use client';

import React from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { PlusIcon, MenuIcon, XIcon } from 'lucide-react';

export const Sidebar = ({ username, projects }) => {
  const [isMobileOpen, setIsMobileOpen] = React.useState(false);

  // Add mobile toggle button that's only visible on small screens
  const toggleButton = (
    <Button
      variant="ghost"
      size="sm"
      className="fixed top-4 left-4 z-50 md:hidden"
      onClick={() => setIsMobileOpen(!isMobileOpen)}
    >
      {isMobileOpen ? (
        <XIcon className="h-4 w-4" />
      ) : (
        <MenuIcon className="h-4 w-4" />
      )}
    </Button>
  );

  return (
    <>
      {toggleButton}
      <div
        className={`${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0 fixed md:static w-64 h-screen bg-background border-r transition-transform duration-200 ease-in-out z-40`}
      >
        <div className="flex flex-col h-full">
          {/* New Chat Button - Added padding-left on mobile */}
          <div className="p-4 border-b md:pl-4 pl-16">
            <Button
              variant="outline"
              className="w-full justify-start"
              size="sm"
            >
              <PlusIcon className="mr-2 h-4 w-4" />
              New Chat
            </Button>
          </div>

          {/* Projects List */}
          <div className="flex-1 overflow-y-auto p-4">
            <h2 className="text-lg font-semibold mb-4">Recent Projects</h2>
            <div className="space-y-2">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className="p-2 hover:bg-accent rounded-md cursor-pointer"
                >
                  {project.name}
                </div>
              ))}
            </div>
          </div>

          {/* User Profile */}
          <div className="p-4 border-t">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Avatar>
                  <AvatarImage src="" />
                  <AvatarFallback>{username[0]}</AvatarFallback>
                </Avatar>
                <span className="font-medium">{username}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      {/* Add overlay for mobile */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-30 md:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}
    </>
  );
};
