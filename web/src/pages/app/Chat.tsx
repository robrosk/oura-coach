import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { sendChatMessage } from '../../lib/api';
import type { ChatMessage, ToolCall } from '../../types';

const STARTER_MESSAGE: ChatMessage = {
  role: 'assistant',
  content:
    "Hi, I'm Oura Coach. Ask me about your sleep, readiness, or activity habits. I can suggest non-medical experiments you can try.",
};

const TOOL_LABELS: Record<string, string> = {
  get_readiness_data: 'Readiness data',
  get_sleep_data: 'Sleep data',
  get_activity_data: 'Activity data',
  web_search: 'Web search',
  web_fetch: 'Web fetch',
};

type ChatItem =
  | {
      id: string;
      type: 'message';
      role: 'user' | 'assistant';
      content: string;
    }
  | {
      id: string;
      type: 'tool';
      status: 'pending' | 'done';
      toolCalls: ToolCall[];
    };

function createId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function formatToolLabel(name: string): string {
  return TOOL_LABELS[name] || name.replace(/_/g, ' ');
}

function formatRangeLabel(tool: ToolCall): string | null {
  const range = tool.resolved_range;
  if (!range) return null;
  if (typeof range.days === 'number') {
    return `Last ${range.days} days`;
  }
  if (range.start_date && range.end_date) {
    return `${range.start_date} to ${range.end_date}`;
  }
  return null;
}

function formatArgs(tool: ToolCall): string {
  const args = tool.args || {};
  const keys = Object.keys(args);
  if (keys.length === 0) {
    return 'Using defaults';
  }
  return JSON.stringify(args, null, 2);
}

export function Chat() {
  const [history, setHistory] = useState<ChatMessage[]>([STARTER_MESSAGE]);
  const [items, setItems] = useState<ChatItem[]>([
    {
      id: createId(),
      type: 'message',
      role: 'assistant',
      content: STARTER_MESSAGE.content,
    },
  ]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [items, isSending]);

  const submitMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    const priorHistory = history;
    const userMessage: ChatMessage = { role: 'user', content: trimmed };
    const userItem: ChatItem = {
      id: createId(),
      type: 'message',
      role: 'user',
      content: trimmed,
    };
    const toolItemId = createId();
    const toolItem: ChatItem = {
      id: toolItemId,
      type: 'tool',
      status: 'pending',
      toolCalls: [],
    };

    setItems((prev) => [...prev, userItem, toolItem]);
    setHistory((prev) => [...prev, userMessage]);
    setInput('');
    setIsSending(true);
    setError(null);

    try {
      const response = await sendChatMessage(trimmed, priorHistory);
      const reply = response.reply || 'Sorry, I did not get a response. Please try again.';
      const assistantMessage: ChatMessage = { role: 'assistant', content: reply };
      const assistantItem: ChatItem = {
        id: createId(),
        type: 'message',
        role: 'assistant',
        content: reply,
      };
      const toolCalls = response.tool_calls ?? [];

      setHistory((prev) => [...prev, assistantMessage]);
      setItems((prev) => {
        const updated = prev
          .map((item) => {
            if (item.id !== toolItemId) return item;
            if (toolCalls.length === 0) return null;
            return { ...item, status: 'done', toolCalls };
          })
          .filter(Boolean) as ChatItem[];

        return [...updated, assistantItem];
      });
    } catch (err) {
      console.error('Chat request failed:', err);
      setError('Failed to reach Oura Coach. Please try again.');
      setItems((prev) => prev.filter((item) => item.id !== toolItemId));
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void submitMessage();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void submitMessage();
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link
        to="/app"
        className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to Home
      </Link>

      <h1 className="text-2xl md:text-3xl font-bold mb-2 text-text-primary">
        Chat with Oura Coach
      </h1>
      <p className="text-text-secondary mb-6">
        Ask questions, explore patterns, or get non-medical experiment ideas.
      </p>

      <div className="bg-surface border border-border rounded-lg p-4">
        <div className="max-h-[60vh] min-h-[260px] overflow-y-auto space-y-4 pr-1">
          {items.map((item) => {
            if (item.type === 'tool') {
              return (
                <div key={item.id} className="flex justify-start">
                  <div className="max-w-[85%] w-full rounded-2xl border border-border bg-surface-elevated px-4 py-3 text-sm text-text-secondary">
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-text-muted">
                      {item.status === 'pending' ? (
                        <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                      <span>Tool activity</span>
                    </div>

                    {item.status === 'pending' ? (
                      <p className="mt-2 text-xs text-text-muted">Checking tools and data ranges...</p>
                    ) : (
                      <div className="mt-3 space-y-3">
                        {item.toolCalls.map((tool, index) => {
                          const rangeLabel = formatRangeLabel(tool);
                          const argsText = formatArgs(tool);
                          return (
                            <div
                              key={`${tool.name}-${index}`}
                              className="rounded-lg border border-border bg-surface px-3 py-2"
                            >
                              <div className="flex items-center justify-between gap-3">
                                <span className="text-xs font-semibold text-text-primary">
                                  {formatToolLabel(tool.name)}
                                </span>
                                {rangeLabel && (
                                  <span className="text-[11px] text-text-muted">{rangeLabel}</span>
                                )}
                              </div>
                              <pre className="mt-2 text-[11px] whitespace-pre-wrap text-text-muted">{argsText}</pre>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              );
            }

            return (
              <div
                key={item.id}
                className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    item.role === 'user'
                      ? 'bg-accent text-background'
                      : 'bg-surface-elevated text-text-primary'
                  }`}
                >
                  {item.role === 'assistant' ? (
                    <div className="chat-markdown">
                      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                        {item.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    item.content
                  )}
                </div>
              </div>
            );
          })}
          <div ref={endRef} />
        </div>
      </div>

      {error && (
        <div className="mt-4 bg-error/10 border border-error/30 rounded-lg p-3">
          <p className="text-sm text-error">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about sleep, readiness, activity, or habits..."
          rows={2}
          className="w-full rounded-lg border border-border bg-surface-elevated px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:border-accent"
        />
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-text-muted">
            Oura Coach provides non-medical wellness guidance only.
          </p>
          <button
            type="submit"
            disabled={isSending || !input.trim()}
            className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
              isSending || !input.trim()
                ? 'bg-surface-elevated text-text-muted cursor-not-allowed'
                : 'bg-accent hover:bg-accent-hover text-background'
            }`}
          >
            {isSending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
}
