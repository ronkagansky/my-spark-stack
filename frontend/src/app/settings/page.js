'use client';

import { useState, Suspense } from 'react';
import { Button } from '@/components/ui/button';
import { HomeIcon, XIcon, MenuIcon, PlusCircleIcon } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { useUser } from '@/context/user-context';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

// Create a client component that uses useSearchParams
function SettingsContent() {
  const { user, team, teams } = useUser();
  const [inviteLink, setInviteLink] = useState('');
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const { toast } = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();
  const shouldHighlightBuy = searchParams.get('buy') === 'true';

  const handleTeamChange = async (teamId) => {
    localStorage.setItem('team', teamId);
    window.location.reload();
  };

  const handleGenerateInvite = async () => {
    try {
      const { invite_link } = await api.generateTeamInvite(team.id);
      setInviteLink(invite_link);
      toast({
        title: 'Invite Link Generated',
        description:
          'The invite link has been generated and copied to your clipboard.',
      });
      navigator.clipboard.writeText(invite_link);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to generate invite link',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="flex h-screen">
      {/* Toggle Button */}
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

      {/* Minimal Sidebar */}
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
              onClick={() => router.push('/chats/new')}
            >
              <HomeIcon className="mr-2 h-4 w-4" />
              Workspace
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-30 md:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="container max-w-2xl mx-auto px-4 py-8 md:py-12">
          <div className="space-y-8 md:max-w-2xl md:mx-auto mt-12 md:mt-0">
            <Card className="shadow-sm">
              <CardHeader className="space-y-2">
                <CardTitle>User Settings</CardTitle>
                <CardDescription>
                  Manage your user account settings
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                      Username
                    </label>
                    <div className="text-base">{user?.username}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-sm">
              <CardHeader className="space-y-2">
                <CardTitle>Team Settings</CardTitle>
                <CardDescription>
                  Teams share projects and credits.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                      Current Team
                    </label>
                    <Select
                      value={team?.id.toString()}
                      onValueChange={handleTeamChange}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select team" />
                      </SelectTrigger>
                      <SelectContent>
                        {teams.map((t) => (
                          <SelectItem key={t.id} value={t.id.toString()}>
                            {t.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none">
                      Credits Remaining
                    </label>
                    <div className="flex items-center gap-4">
                      <div className="text-2xl font-bold">
                        {team?.credits || 0}
                      </div>
                      <TooltipProvider>
                        <Tooltip open={shouldHighlightBuy}>
                          <TooltipTrigger asChild>
                            <Button
                              variant="secondary"
                              size="default"
                              onClick={() =>
                                (window.location.href = `https://buy.stripe.com/28odUpcNb0Xm4ww8wz?client_reference_id=promptstack___team_${team.id}`)
                              }
                            >
                              <PlusCircleIcon className="h-4 w-4 mr-2" />
                              Buy More Credits
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Click here to purchase more credits!</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <Button onClick={handleGenerateInvite}>
                      Generate Invite Link
                    </Button>
                    {inviteLink && (
                      <div className="space-y-2">
                        <Input value={inviteLink} readOnly />
                        <p className="text-sm text-muted-foreground">
                          Link copied to clipboard
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main page component
export default function SettingsPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SettingsContent />
    </Suspense>
  );
}
