'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useUser } from '@/context/user-context';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api';

export default function AuthPage() {
  const [username, setUsername] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { createAccount } = useUser();
  const { toast } = useToast();

  // Redirect if already logged in
  useEffect(() => {
    const username = localStorage.getItem('username');
    if (username) {
      router.push('/workspace');
    }
  }, [router]);

  const handleCreateAccount = async () => {
    if (!username.trim()) return;

    try {
      setIsLoading(true);
      const user = await api.createAccount(username);
      localStorage.setItem('username', username);
      toast({
        title: 'Success!',
        description: 'Account created successfully',
      });
      router.push('/workspace');
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
          <h1 className="text-3xl font-bold">Create Your Account</h1>
          <p className="text-muted-foreground">
            Choose a username to get started
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
