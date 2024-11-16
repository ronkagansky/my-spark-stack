'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { FileText, GitBranch, Calendar, Pencil } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useUser } from '@/context/user-context';

export function ProjectTab({ project }) {
  const { team, refreshProjects } = useUser();
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(project?.name);
  const [editedDescription, setEditedDescription] = useState(
    project?.description
  );

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
      });
      setIsEditing(false);
      await refreshProjects();
    } catch (error) {
      console.error('Failed to update project:', error);
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
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => setIsEditing(true)}
              >
                <Pencil className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>

        <div className="grid gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4" />
              <h3 className="font-semibold">Files</h3>
            </div>
            <p className="text-muted-foreground">
              Total files: {project.fileCount}
            </p>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <GitBranch className="h-4 w-4" />
              <h3 className="font-semibold">Branches</h3>
            </div>
            <p className="text-muted-foreground">
              Total branches: {project.branchCount}
            </p>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Calendar className="h-4 w-4" />
              <h3 className="font-semibold">Last Updated</h3>
            </div>
            <p className="text-muted-foreground">
              Last updated: {project.lastUpdated}
            </p>
          </Card>
        </div>
      </div>
    </ScrollArea>
  );
}
