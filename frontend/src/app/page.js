'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const username = localStorage.getItem('username');
    if (username) {
      router.push('/workspace');
    } else {
      router.push('/auth');
    }
  }, [router]);

  return null; // Or a loading spinner if you prefer
}
