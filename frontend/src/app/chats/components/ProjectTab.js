'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  FileText,
  GitBranch,
  Pencil,
  Loader2,
  RotateCcw,
  Trash2,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useUser } from '@/context/user-context';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useRouter } from 'next/navigation';

export function ProjectTab({ project, onSendMessage }) {
  const { team, refreshProjects } = useUser();
  const router = useRouter();
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(project?.name);
  const [editedDescription, setEditedDescription] = useState(
    project?.description
  );
  const [editedInstructions, setEditedInstructions] = useState(
    project?.custom_instructions
  );
  const [gitLog, setGitLog] = useState([]);
  const [isLoadingGitLog, setIsLoadingGitLog] = useState(true);
  const [chats, setChats] = useState([]);
  const [isLoadingChats, setIsLoadingChats] = useState(true);

  useEffect(() => {
    const fetchGitLog = async () => {
      try {
        const logData = await api.getProjectGitLog(team.id, project.id);
        setGitLog(logData);
      } catch (error) {
      } finally {
        setIsLoadingGitLog(false);
      }
    };

    const fetchChats = async () => {
      try {
        const chatData = await api.getProjectChats(team.id, project.id);
        setChats(chatData);
      } catch (error) {
        console.error('Failed to fetch chats:', error);
      } finally {
        setIsLoadingChats(false);
      }
    };

    if (project && team?.id) {
      fetchGitLog();
      fetchChats();
    }
  }, [project, team?.id]);

  if (!project) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        No project information available
      </div>
    );
  }

  const handleSave = async () => {
    try {
      await api.updateProject(team.id, project.id, {
        name: editedName,
        description: editedDescription,
        custom_instructions: editedInstructions,
      });
      setIsEditing(false);
      await refreshProjects();
    } catch (error) {
      console.error('Failed to update project:', error);
    }
  };

  const handleRestore = async (hash) => {
    await onSendMessage({
      content: `Revert changes using \`git revert ${hash}..HEAD\``,
      images: [],
    });
  };

  const handleDeleteProject = async () => {
    if (
      confirm(
        'Are you sure you want to delete this project? This action cannot be undone.'
      )
    ) {
      try {
        await api.deleteProject(team.id, project.id);
        await refreshProjects();
        await refreshChats();
        router.push('/chats/new');
        router.refresh();
      } catch (error) {
        console.error('Failed to delete project:', error);
      }
    }
  };

  return (
    <ScrollArea className="h-full p-6">
      <div className="space-y-6">
        <div className="group relative">
          {isEditing ? (
            <div className="space-y-4">
              <Input
                value={editedName}
                onChange={(e) => setEditedName(e.target.value)}
                className="text-2xl font-bold"
              />
              <Textarea
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                className="text-muted-foreground"
              />
              <Card className="p-4">
                <h3 className="font-semibold mb-2">Custom Instructions</h3>
                <Textarea
                  value={editedInstructions}
                  onChange={(e) => setEditedInstructions(e.target.value)}
                  className="text-muted-foreground"
                  placeholder="Add custom instructions for this project..."
                  rows={4}
                />
              </Card>
              <div className="space-x-2">
                <Button onClick={handleSave}>Save</Button>
                <Button variant="outline" onClick={() => setIsEditing(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <>
              <h2 className="text-2xl font-bold mb-2">{project.name}</h2>
              <p className="text-muted-foreground">{project.description}</p>
              <Card className="p-4 mt-4">
                <h3 className="font-semibold mb-2">Custom Instructions</h3>
                <p className="text-muted-foreground">
                  {project.custom_instructions ||
                    'No custom instructions set for this project.'}
                </p>
              </Card>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => setIsEditing(true)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Edit</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </>
          )}
        </div>

        <div className="grid gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4" />
              <h3 className="font-semibold">Chats</h3>
            </div>
            {isLoadingChats ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            ) : chats?.length === 0 ? (
              <div className="text-sm text-muted-foreground">
                No chats in this project yet.
              </div>
            ) : (
              <ScrollArea className="h-[250px]">
                <div className="space-y-2">
                  {chats?.map((chat) => (
                    <div
                      key={chat.id}
                      className="flex items-start gap-3 text-sm p-2 hover:bg-muted rounded-md cursor-pointer"
                      onClick={() => router.push(`/chats/${chat.id}`)}
                    >
                      <div className="flex-1">
                        <div className="font-medium">
                          {chat.name || 'Untitled Chat'}
                        </div>
                        <div className="text-muted-foreground text-xs">
                          {new Date(chat.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <GitBranch className="h-4 w-4" />
              <h3 className="font-semibold">History</h3>
            </div>
            {isLoadingGitLog ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            ) : (
              <ScrollArea className="h-[250px]">
                <div className="space-y-2">
                  {gitLog?.lines?.map((entry) => (
                    <div
                      key={entry.hash}
                      className="flex items-start gap-3 text-sm"
                    >
                      <div className="text-muted-foreground font-mono">
                        {entry.hash.substring(0, 7)}
                      </div>
                      <div className="flex-1">
                        <div className="font-medium">{entry.message}</div>
                        <div className="text-muted-foreground text-xs">
                          {new Date(entry.date).toLocaleDateString()}
                        </div>
                      </div>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleRestore(entry.hash)}
                              className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                            >
                              <RotateCcw className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Restore Version</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </Card>
        </div>

        <div className="pt-6 border-t">
          <Button
            variant="destructive"
            className="w-full"
            onClick={handleDeleteProject}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete Project
          </Button>
        </div>
      </div>
    </ScrollArea>
  );
}
