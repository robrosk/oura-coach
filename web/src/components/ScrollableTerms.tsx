import { useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';

interface ScrollableTermsProps {
  content: string;
  onScrolledToBottom: (scrolled: boolean) => void;
}

export function ScrollableTerms({ content, onScrolledToBottom }: ScrollableTermsProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const checkScroll = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    // Consider "at bottom" when within 20px of the end
    const isAtBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight < 20;

    onScrolledToBottom(isAtBottom);
  }, [onScrolledToBottom]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Check initial state
    checkScroll();

    container.addEventListener('scroll', checkScroll);
    return () => container.removeEventListener('scroll', checkScroll);
  }, [checkScroll]);

  // Re-check when content loads (images, etc.)
  useEffect(() => {
    checkScroll();
  }, [content, checkScroll]);

  return (
    <div
      ref={containerRef}
      className="h-64 md:h-80 overflow-y-auto bg-surface-elevated border border-border rounded-lg p-4 markdown-content"
    >
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
