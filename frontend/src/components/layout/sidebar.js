'use client';

import React from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  PlusIcon,
  MenuIcon,
  XIcon,
  MoreVertical,
  Pencil,
  Trash2,
} from 'lucide-react';
import { useUser } from '@/context/user-context';
import { useRouter } from 'next/navigation';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { api } from '@/lib/api';

export const Sidebar = () => {
  const [isMobileOpen, setIsMobileOpen] = React.useState(false);
  const { user, projects, refreshProjects } = useUser();
  const router = useRouter();
  const [editingProjectId, setEditingProjectId] = React.useState(null);
  const [editingName, setEditingName] = React.useState('');

  const handleProjectClick = (projectId) => {
    router.push(`/workspace/${projectId}`);
    setIsMobileOpen(false);
  };

  const handleNewChat = () => {
    router.push('/workspace');
    setIsMobileOpen(false);
    window.location.href = '/workspace';
    window.location.reload();
  };

  const handleRename = (projectId, e) => {
    e.stopPropagation();
    const project = projects.find((p) => p.id === projectId);
    setEditingProjectId(projectId);
    setEditingName(project.name);
  };

  const handleRenameSubmit = async (projectId, e) => {
    e.preventDefault();
    e.stopPropagation();

    if (!editingName.trim()) return;

    try {
      await api.updateProject(projectId, { name: editingName.trim() });
      await refreshProjects();
      setEditingProjectId(null);
    } catch (error) {
      console.error('Failed to rename project:', error);
      // Add proper error handling here
    }
  };

  const handleDelete = async (projectId, e) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this project?')) {
      try {
        await api.deleteProject(projectId);
        // Refresh the projects list by calling the context update
        await refreshProjects();
        // If we're currently on the deleted project's page, redirect to home
        if (window.location.pathname.includes(`/workspace/${projectId}`)) {
          router.push('/workspace');
        }
      } catch (error) {
        console.error('Failed to delete project:', error);
        // You might want to add proper error handling/notification here
      }
    }
  };

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
        } md:translate-x-0 fixed md:static w-48 h-screen bg-background border-r transition-transform duration-200 ease-in-out z-40`}
      >
        <div className="flex flex-col h-full">
          <div className="p-3 border-b md:pl-3 pl-16">
            <Button
              variant="outline"
              className="w-full justify-start"
              size="sm"
              onClick={handleNewChat}
            >
              <PlusIcon className="mr-2 h-4 w-4" />
              New Chat
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground font-medium px-2">
                Recent Chats
              </div>
              {[...projects]
                .sort((a, b) => b.id - a.id)
                .map((project) => (
                  <div
                    key={project.id}
                    className="py-1 px-2 hover:bg-accent rounded-md cursor-pointer group relative"
                    onClick={() => handleProjectClick(project.id)}
                  >
                    <div className="flex justify-between items-center">
                      {editingProjectId === project.id ? (
                        <form
                          onSubmit={(e) => handleRenameSubmit(project.id, e)}
                          className="flex-1 mr-2"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="text"
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            className="w-full px-1 py-0.5 text-sm bg-background border rounded"
                            autoFocus
                            onBlur={(e) => handleRenameSubmit(project.id, e)}
                          />
                        </form>
                      ) : (
                        <span className="truncate pr-2 text-sm">
                          {project.name}
                        </span>
                      )}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="opacity-0 group-hover:opacity-100 h-6 w-6 p-0"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                          <DropdownMenuItem
                            onClick={(e) => handleRename(project.id, e)}
                          >
                            <Pencil className="mr-2 h-4 w-4" />
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e) => handleDelete(project.id, e)}
                            className="text-red-600 focus:text-red-600 focus:bg-red-100"
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
            </div>
          </div>
          <div className="p-4 border-t">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Avatar>
                  <AvatarImage src="" />
                  <AvatarFallback>{user.username[0]}</AvatarFallback>
                </Avatar>
                <span className="font-medium">{user.username}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-30 md:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}
    </>
  );
};
