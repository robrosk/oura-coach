import ReactMarkdown from 'react-markdown';
import { CURRENT_TERMS_VERSION } from '../lib/terms';

interface MarkdownPageProps {
  content: string;
}

export function MarkdownPage({ content }: MarkdownPageProps) {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="text-sm text-text-muted mb-6">
        Version: {CURRENT_TERMS_VERSION}
      </div>
      <article className="markdown-content">
        <ReactMarkdown>{content}</ReactMarkdown>
      </article>
      <div className="mt-8 pt-4 border-t border-border">
        <p className="text-sm text-text-muted">
          Last updated: {CURRENT_TERMS_VERSION}
        </p>
      </div>
    </div>
  );
}
