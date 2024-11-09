'use client';

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import WorkspacePage from '../page';

export default function ProjectWorkspace() {
  const params = useParams();

  return <WorkspacePage projectId={params.projectId} />;
}
