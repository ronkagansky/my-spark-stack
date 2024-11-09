'use client';

import { useUser } from '@/context/user-context';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { MainLayout } from '@/components/layout/main-layout';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api';

export default function WorkspaceLayout({ children }) {
  const router = useRouter();
  const [projects, setProjects] = useState([]);
  const { toast } = useToast();
  const { user } = useUser();

  useEffect(() => {
    if (!user) return;
    api
      .getUserProjects(user.username)
      .then((data) => setProjects(data))
      .catch((err) => {
        console.error('Failed to fetch projects:', err);
        toast({
          title: 'Error',
          description: 'Failed to load projects',
          variant: 'destructive',
        });
      });
  }, [user, router, toast]);

  if (!user) return null;

  return (
    <MainLayout username={user.username} projects={projects}>
      {children}
    </MainLayout>
  );
}
