'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { useUser } from '@/context/user-context';

export default function AuthPage() {
  const [username, setUsername] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { toast } = useToast();
  const { createAccount } = useUser();

  const handleCreateAccount = async () => {
    if (!username.trim()) return;

    try {
      setIsLoading(true);
      await createAccount(username);
      localStorage.setItem('username', username);
      toast({
        title: 'Success!',
        description: 'Account created successfully',
      });
      router.push('/workspace/new');
    } catch (error) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to create account',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && username.trim()) {
      handleCreateAccount();
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="w-full max-w-md space-y-6 p-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold">Prompt Stack</h1>
          <p className="text-muted-foreground">
            Choose a username to start building. This tool is experimental and
            projects may be deleted without notice.
          </p>
        </div>

        <div className="space-y-4">
          <Input
            placeholder="Enter username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
            autoFocus
          />
          <Button
            className="w-full"
            onClick={handleCreateAccount}
            disabled={!username.trim() || isLoading}
          >
            {isLoading ? 'Creating Account...' : 'Create Account'}
          </Button>
        </div>
      </div>
    </div>
  );
}
