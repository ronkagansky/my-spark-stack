import { Inter } from 'next/font/google';
import './globals.css';
import { UserProvider } from '@/context/user-context';
import { Toaster } from '@/components/ui/toaster';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'Prompt-Stack',
  description: 'Build full stack apps in your browser',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <UserProvider>
          {children}
          <Toaster />
        </UserProvider>
      </body>
    </html>
  );
}
