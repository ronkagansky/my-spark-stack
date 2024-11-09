'use client';

import { useUser } from '@/context/user-context';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { MainLayout } from '@/components/layout/main-layout';
import { useToast } from '@/hooks/use-toast';

export default function WorkspaceLayout({ children }) {
  const { user } = useUser();
  const router = useRouter();
  const [projects, setProjects] = useState([]);
  const { toast } = useToast();

  useEffect(() => {
    if (!user) {
      router.push('/auth');
      return;
    }

    // Fetch user's projects
    fetch(`http://localhost:8000/projects/${user.username}`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch projects');
        return res.json();
      })
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
