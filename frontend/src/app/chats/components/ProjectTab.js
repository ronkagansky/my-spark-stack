'use client';

import { useState, useEffect } from 'react';
import { getProject } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { FileText, GitBranch, Calendar } from 'lucide-react';

export function ProjectTab({ projectId }) {
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchProject() {
      try {
        const data = await getProject(projectId);
        setProject(data);
      } catch (error) {
        console.error('Failed to fetch project:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchProject();
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Loading project information...
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        No project information available
      </div>
    );
  }

  return (
    <ScrollArea className="h-full p-6">
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold mb-2">{project.name}</h2>
          <p className="text-muted-foreground">{project.description}</p>
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
