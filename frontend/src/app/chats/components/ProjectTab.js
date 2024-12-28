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
  Rocket,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';

function ChatsTab({ chats, isLoadingChats, router }) {
  return (
    <Card className="p-4">
      {isLoadingChats ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      ) : chats?.length === 0 ? (
        <div className="text-sm text-muted-foreground">
          No chats in this project yet.
        </div>
      ) : (
        <ScrollArea className="h-[400px]">
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
  );
}

function HistoryTab({ gitLog, isLoadingGitLog, handleRestore }) {
  return (
    <Card className="p-4">
      {isLoadingGitLog ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      ) : (
        <ScrollArea className="h-[400px]">
          <div className="space-y-2">
            {gitLog?.lines?.map((entry) => (
              <div key={entry.hash} className="flex items-start gap-3 text-sm">
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
  );
}

function DeployTab({ project, team }) {
  const [status, setStatus] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isPushing, setIsPushing] = useState(false);
  const [message, setMessage] = useState(null);
  const [githubToken, setGithubToken] = useState('');
  const { toast } = useToast();

  useEffect(() => {
    const fetchGithubDeployStatus = async () => {
      const status = await api.deployStatusGithub(team.id, project.id);
      setStatus(status);
    };
    fetchGithubDeployStatus();
  }, [project, team]);

  const handleGithubCreateDeploy = async () => {
    if (!githubToken) {
      toast({
        title: 'GitHub Token Required',
        description: 'Please enter your GitHub token to continue.',
        variant: 'destructive',
      });
      return;
    }
    setIsCreating(true);
    setMessage('Deploying...');
    try {
      await api.deployCreateGithub(
        team.id,
        project.id,
        {
          githubToken,
        },
        (message) => {
          try {
            const data = JSON.parse(message);
            if (data.message) {
              setMessage(data.message);
            }
            if (data.done) {
              toast({
                title: 'Integration Complete',
                description: 'Your project has been integrated with GitHub.',
              });
              setIsCreating(false);
            }
          } catch (e) {
            console.error('Failed to parse deploy status:', e);
          }
        }
      );
    } catch (error) {
      console.error('Failed to deploy:', error);
      toast({
        title: 'Integration Failed',
        description: 'There was an error integrating with GitHub.',
        variant: 'destructive',
      });
    } finally {
      setIsCreating(false);
    }
  };

  const handleGithubPushDeploy = async () => {
    setIsPushing(true);
    setMessage('Pushing...');
    try {
      await api.deployPushGithub(team.id, project.id);
      toast({
        title: 'Push Complete',
        description: 'Your project has been pushed to GitHub.',
      });
    } catch (error) {
      console.error('Failed to push:', error);
      toast({
        title: 'Push Failed',
        description: 'There was an error pushing to GitHub.',
        variant: 'destructive',
      });
    } finally {
      setIsPushing(false);
    }
  };

  if (status?.created) {
    return (
      <Card className="p-4">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">GitHub</h3>
              <a
                href={`https://github.com/${status.repo_name}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline"
              >
                {status.repo_name}
              </a>
            </div>
            <Button onClick={handleGithubPushDeploy} disabled={isPushing}>
              {isPushing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {message}
                </>
              ) : (
                <>
                  <GitBranch className="mr-2 h-4 w-4" />
                  Push Changes
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>
    );
  } else if (status && !status.created) {
    return (
      <Card className="p-4">
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground">
            <p>
              For long-term hosting and CI/CD deployments, we support syncing
              with GitHub.
            </p>
            <ul className="list-disc list-inside mt-2">
              <li>24/7 uptime</li>
              <li>Custom domains</li>
              <li>Free hosting with tools like Netlify, Vercel, and more</li>
            </ul>
          </div>

          <div className="space-y-4">
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Step 1: GitHub Token</h3>
              <p className="text-sm text-muted-foreground">
                Create a GitHub token with <b>repo</b> access at{' '}
                <a
                  href="https://github.com/settings/tokens/new"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  github.com/settings/tokens/new
                </a>
              </p>
              <Input
                type="password"
                placeholder="Enter your GitHub token"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <h3 className="text-sm font-medium">Step 2: Create Repository</h3>
              <p className="text-sm text-muted-foreground">
                Create a new GitHub repository to host your project.
              </p>
              <Button
                onClick={handleGithubCreateDeploy}
                // disabled={!githubToken || isDeploying}
                className="w-full"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {message}
                  </>
                ) : (
                  <>
                    <GitBranch className="mr-2 h-4 w-4" />
                    Create Repository
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </Card>
    );
  } else {
    return (
      <Card className="flex items-center justify-center p-4">
        <Loader2 className="h-4 w-4 animate-spin" />
      </Card>
    );
  }
}

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
  const { toast } = useToast();

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
      content: `Please revert recent changes with $ git revert ${hash}..HEAD`,
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

  const handleRestartProject = async () => {
    try {
      await api.restartProject(team.id, project.id);
      await refreshProjects();
      router.refresh();
      toast({
        title: 'Project Restarted',
        description:
          'The project has been successfully restarted. Reconnect to continue.',
      });
    } catch (error) {
      console.error('Failed to restart project:', error);
      toast({
        title: 'Error',
        description: 'Failed to restart the project. Please try again.',
        variant: 'destructive',
      });
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

        <Tabs defaultValue="chats" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="chats" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Chats
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center gap-2">
              <GitBranch className="h-4 w-4" />
              History
            </TabsTrigger>
            <TabsTrigger value="deploy" className="flex items-center gap-2">
              <Rocket className="h-4 w-4" />
              Deploy
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chats" className="mt-4">
            <ChatsTab
              chats={chats}
              isLoadingChats={isLoadingChats}
              router={router}
            />
          </TabsContent>

          <TabsContent value="history" className="mt-4">
            <HistoryTab
              gitLog={gitLog}
              isLoadingGitLog={isLoadingGitLog}
              handleRestore={handleRestore}
            />
          </TabsContent>

          <TabsContent value="deploy" className="mt-4">
            <DeployTab project={project} team={team} />
          </TabsContent>
        </Tabs>

        <div className="pt-6 border-t space-y-2">
          <Button
            variant="outline"
            className="w-full"
            onClick={handleRestartProject}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Restart Project
          </Button>
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
