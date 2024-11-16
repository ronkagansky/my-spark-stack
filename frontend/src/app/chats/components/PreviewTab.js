import { useState, useEffect, useRef } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Smartphone,
  Monitor,
  Maximize2,
  RotateCw,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useDebounce } from '@/lib/hooks/useDebounce';

export function PreviewTab({
  projectPreviewUrl,
  projectPreviewHash,
  projectPreviewPath,
  setProjectPreviewPath,
}) {
  const [viewport, setViewport] = useState('full');
  const [scale, setScale] = useState(1);
  const debouncedPath = useDebounce(projectPreviewPath, 500);
  const containerRef = useRef(null);

  const viewportStyles = {
    mobile: { width: '375px', height: '667px' },
    desktop: { width: '1920px', height: '1080px' },
    full: { width: '100%', height: '100%' },
  };

  useEffect(() => {
    const calculateScale = () => {
      if (viewport === 'full' || !containerRef.current) return 1;

      const container = containerRef.current;
      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;
      const viewportWidth = parseInt(viewportStyles[viewport].width);
      const viewportHeight = parseInt(viewportStyles[viewport].height);

      const scaleX = (containerWidth - 40) / viewportWidth; // 40px padding
      const scaleY = (containerHeight - 40) / viewportHeight;

      return Math.min(1, scaleX, scaleY);
    };

    const handleResize = () => {
      setScale(calculateScale());
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [viewport]);

  const handleRefresh = () => {
    const iframe = document.querySelector('iframe');
    if (iframe) {
      iframe.src = iframe.src;
    }
  };

  useEffect(() => {
    handleRefresh();
  }, [projectPreviewHash, debouncedPath]);

  if (!projectPreviewUrl) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        No preview available
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-2 border-b flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={viewport}
            onValueChange={(value) => setViewport(value)}
          >
            <SelectTrigger className="w-[140px] sm:w-[180px]">
              <SelectValue placeholder="Select viewport" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="full">
                <div className="flex items-center gap-2">
                  <Maximize2 className="h-4 w-4" />
                  <span>Full Width</span>
                </div>
              </SelectItem>
              <SelectItem value="desktop">
                <div className="flex items-center gap-2">
                  <Monitor className="h-4 w-4" />
                  <span>Desktop</span>
                </div>
              </SelectItem>
              <SelectItem value="mobile">
                <div className="flex items-center gap-2">
                  <Smartphone className="h-4 w-4" />
                  <span>Mobile</span>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
          <Input
            value={projectPreviewPath}
            onChange={(e) => setProjectPreviewPath(e.target.value)}
            className="w-full sm:w-[120px]"
            placeholder="Path (e.g. /)"
          />
        </div>
        <div className="flex gap-2 self-end sm:self-auto">
          <Button variant="ghost" size="icon" onClick={handleRefresh}>
            <RotateCw className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => window.open(projectPreviewUrl, '_blank')}
          >
            <ExternalLink className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div
        className="flex-1 flex items-start justify-center p-4 bg-gray-50"
        ref={containerRef}
      >
        <div
          style={{
            width: viewport === 'full' ? '100%' : 'auto',
            height: viewport === 'full' ? '100%' : 'auto',
            transform: viewport !== 'full' ? `scale(${scale})` : 'none',
            transformOrigin: 'top center',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'center',
            marginTop: '20px',
          }}
        >
          <iframe
            src={`${projectPreviewUrl}${debouncedPath}`}
            style={viewportStyles[viewport]}
            className="border shadow-sm bg-white"
            title="Project Preview"
          />
        </div>
      </div>
    </div>
  );
}
