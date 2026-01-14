import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { getExperiment, streamExperimentChat } from '../../lib/api';
import type { ChatMessage, Experiment, ToolCall } from '../../types';

const STARTER_MESSAGE: ChatMessage = {
  role: 'assistant',
  content: "I'm here to coach you through this experiment. How has it been going so far?",
};

const TOOL_LABELS: Record<string, string> = {
  get_readiness_data: 'Readiness data',
  get_sleep_data: 'Sleep data',
  get_activity_data: 'Activity data',
  create_experiment: 'Create experiment',
  end_experiment: 'End experiment',
  experiment_success: 'Mark success',
  experiment_failure: 'Mark failure',
  web_search: 'Web search',
  pubmed_search: 'PubMed search',
  web_fetch: 'Web fetch',
};

const TOOL_STYLES: Record<
  string,
  {
    accent: string;
    border: string;
    bg: string;
    spinner: string;
    badge: string;
    borderStyle?: string;
  }
> = {
  get_readiness_data: {
    accent: 'text-success',
    border: 'border-success/30',
    bg: 'bg-success/10',
    spinner: 'border-success',
    badge: 'bg-success/20 text-success',
  },
  get_sleep_data: {
    accent: 'text-accent',
    border: 'border-accent/30',
    bg: 'bg-accent/10',
    spinner: 'border-accent',
    badge: 'bg-accent/20 text-accent',
  },
  get_activity_data: {
    accent: 'text-warning',
    border: 'border-warning/30',
    bg: 'bg-warning/10',
    spinner: 'border-warning',
    badge: 'bg-warning/20 text-warning',
  },
  create_experiment: {
    accent: 'text-accent',
    border: 'border-accent/30',
    bg: 'bg-accent/10',
    spinner: 'border-accent',
    badge: 'bg-accent/20 text-accent',
  },
  end_experiment: {
    accent: 'text-text-primary',
    border: 'border-border',
    bg: 'bg-surface-elevated',
    spinner: 'border-text-secondary',
    badge: 'bg-surface text-text-secondary',
  },
  experiment_success: {
    accent: 'text-success',
    border: 'border-success/30',
    bg: 'bg-success/10',
    spinner: 'border-success',
    badge: 'bg-success/20 text-success',
  },
  experiment_failure: {
    accent: 'text-error',
    border: 'border-error/30',
    bg: 'bg-error/10',
    spinner: 'border-error',
    badge: 'bg-error/20 text-error',
  },
  web_search: {
    accent: 'text-text-secondary',
    border: 'border-border',
    bg: 'bg-surface',
    spinner: 'border-text-secondary',
    badge: 'bg-surface-elevated text-text-secondary',
    borderStyle: 'border-dashed',
  },
  pubmed_search: {
    accent: 'text-text-primary',
    border: 'border-border',
    bg: 'bg-surface-elevated',
    spinner: 'border-text-muted',
    badge: 'bg-surface text-text-secondary',
    borderStyle: 'border-dotted',
  },
  web_fetch: {
    accent: 'text-error',
    border: 'border-error/30',
    bg: 'bg-error/10',
    spinner: 'border-error',
    badge: 'bg-error/20 text-error',
  },
};

const DEFAULT_TOOL_STYLE = {
  accent: 'text-text-secondary',
  border: 'border-border',
  bg: 'bg-surface',
  spinner: 'border-text-secondary',
  badge: 'bg-surface-elevated text-text-secondary',
  borderStyle: 'border-dashed',
};

type ChatItem =
  | {
      id: string;
      type: 'message';
      role: 'user' | 'assistant';
      content: string;
      status?: 'thinking' | 'streaming' | 'done';
    }
  | {
      id: string;
      type: 'tool';
      status: 'pending' | 'done';
      toolCall: ToolCall;
    };

function createId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function formatToolLabel(name: string): string {
  return TOOL_LABELS[name] || name.replace(/_/g, ' ');
}

function getToolStyle(name: string) {
  return TOOL_STYLES[name] || DEFAULT_TOOL_STYLE;
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

function renderExperimentMeta(experiment: Experiment) {
  return (
    <div className="bg-surface border border-border rounded-lg p-5 mb-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-text-primary">
            {experiment.title}
          </h1>
          <p className="text-text-secondary mt-1">{experiment.objective}</p>
          <p className="text-xs text-text-muted mt-2">
            {experiment.start_date} to {experiment.end_date} · {experiment.duration_days} days
          </p>
        </div>
        <span className="text-xs font-semibold px-3 py-1 rounded-full bg-surface-elevated text-text-secondary">
          {experiment.status}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-text-secondary">
        <div>
          <p className="text-xs uppercase tracking-wide text-text-muted mb-1">Hypothesis</p>
          <p>{experiment.hypothesis}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-text-muted mb-1">Success Criteria</p>
          <p>{experiment.success_criteria}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-text-muted mb-1">Protocol</p>
          <p>{experiment.protocol}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-text-muted mb-1">Metrics</p>
          <p>{experiment.metrics.length ? experiment.metrics.join(', ') : 'Not specified'}</p>
        </div>
      </div>
      {experiment.outcome && (
        <div className="mt-4 text-sm text-text-secondary">
          <p className="text-xs uppercase tracking-wide text-text-muted mb-1">Outcome</p>
          <p>{experiment.outcome}</p>
        </div>
      )}
    </div>
  );
}

export function ExperimentChat() {
  const { experimentId } = useParams();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
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
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!experimentId) return;
    getExperiment(experimentId)
      .then((response) => setExperiment(response))
      .catch((err) => {
        console.error('Failed to load experiment:', err);
        setLoadError('Unable to load experiment details.');
      })
      .finally(() => setLoading(false));
  }, [experimentId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [items, isSending]);

  const submitMessage = async () => {
    if (!experimentId) return;
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
    const assistantId = createId();
    const assistantItem: ChatItem = {
      id: assistantId,
      type: 'message',
      role: 'assistant',
      content: '',
      status: 'thinking',
    };

    setItems((prev) => [...prev, userItem, assistantItem]);
    setHistory((prev) => [...prev, userMessage]);
    setInput('');
    setIsSending(true);
    setChatError(null);

    let replyBuffer = '';
    let hasToken = false;
    let assistantPresent = true;
    let sawToolEvents = false;
    const toolCallToItemId = new Map<string, string>();

    const upsertAssistant = (content: string, status: 'thinking' | 'streaming' | 'done') => {
      setItems((prev) => {
        const exists = prev.some((item) => item.id === assistantId);
        const nextItem: ChatItem = {
          id: assistantId,
          type: 'message',
          role: 'assistant',
          content,
          status,
        };
        if (!exists) {
          return [...prev, nextItem];
        }
        return prev.map((item) => (item.id === assistantId ? nextItem : item));
      });
    };

    const removeAssistant = () => {
      setItems((prev) => prev.filter((item) => item.id !== assistantId));
    };

    try {
      for await (const event of streamExperimentChat(experimentId, trimmed, priorHistory)) {
        if (event.type === 'tool_start') {
          sawToolEvents = true;
          if (assistantPresent && !hasToken) {
            assistantPresent = false;
            removeAssistant();
          }
          const toolCall = {
            ...event.tool_call,
            args: event.tool_call.args || {},
          };
          const toolItemId = createId();
          const callId = toolCall.id || toolItemId;
          toolCallToItemId.set(callId, toolItemId);
          const toolItem: ChatItem = {
            id: toolItemId,
            type: 'tool',
            status: 'pending',
            toolCall,
          };
          setItems((prev) => [...prev, toolItem]);
          continue;
        }

        if (event.type === 'tool_end') {
          const toolItemId = toolCallToItemId.get(event.tool_call_id);
          if (!toolItemId) {
            continue;
          }
          setItems((prev) =>
            prev.map((item) => {
              if (item.id !== toolItemId || item.type !== 'tool') {
                return item;
              }
              const resolvedRange = event.resolved_range || item.toolCall.resolved_range;
              return {
                ...item,
                status: 'done',
                toolCall: resolvedRange
                  ? { ...item.toolCall, resolved_range: resolvedRange }
                  : item.toolCall,
              };
            })
          );
          continue;
        }

        if (event.type === 'token') {
          hasToken = true;
          replyBuffer += event.content;
          assistantPresent = true;
          upsertAssistant(replyBuffer, 'streaming');
          continue;
        }

        if (event.type === 'error') {
          throw new Error(event.message);
        }

        if (event.type !== 'done') {
          continue;
        }

        const reply =
          event.reply || replyBuffer || 'Sorry, I did not get a response. Please try again.';
        hasToken = true;
        replyBuffer = reply;
        assistantPresent = true;

        upsertAssistant(reply, 'done');
        setHistory((prev) => [...prev, { role: 'assistant', content: reply }]);

        if (!sawToolEvents && event.tool_calls && event.tool_calls.length > 0) {
          event.tool_calls.forEach((toolCall) => {
            const toolItemId = createId();
            const callId = toolCall.id || toolItemId;
            toolCallToItemId.set(callId, toolItemId);
            setItems((prev) => [
              ...prev,
              {
                id: toolItemId,
                type: 'tool',
                status: 'done',
                toolCall,
              },
            ]);
          });
        }
      }
    } catch (err) {
      console.error('Experiment chat failed:', err);
      setChatError('Failed to reach Oura Coach. Please try again.');
      setItems((prev) => {
        if (!hasToken) {
          const filtered = prev.filter((item) => item.id !== assistantId);
          return filtered;
        }
        return prev.map((item) =>
          item.id === assistantId ? { ...item, status: 'done' } : item
        );
      });
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

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-surface border border-border rounded-lg p-4 flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span className="text-text-secondary">Loading experiment...</span>
        </div>
      </div>
    );
  }

  if (loadError || !experiment) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <Link
          to="/app/experiments"
          className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors mb-6"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Experiments
        </Link>
        <div className="bg-error/10 border border-error/30 rounded-lg p-4 text-sm text-error">
          {loadError || 'Experiment not found.'}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link
        to="/app/experiments"
        className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Experiments
      </Link>

      {renderExperimentMeta(experiment)}

      <div className="bg-surface border border-border rounded-lg p-4">
        <div className="max-h-[60vh] min-h-[260px] overflow-y-auto space-y-4 pr-1">
          {items.map((item) => {
            if (item.type === 'tool') {
              const isPending = item.status === 'pending';
              const tool = item.toolCall;
              const rangeLabel = formatRangeLabel(tool);
              const argsText = formatArgs(tool);
              const style = getToolStyle(tool.name);
              return (
                <div key={item.id} className="flex justify-start">
                  <div className="max-w-[85%] w-full rounded-2xl border border-border bg-surface-elevated px-4 py-3 text-sm text-text-secondary">
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-text-muted">
                      {isPending ? (
                        <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                      <span>Tool activity</span>
                    </div>
                    <div className="mt-3">
                      <div
                        className={`rounded-lg border ${style.border} ${style.borderStyle || ''} ${style.bg} px-3 py-2`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            {isPending ? (
                              <div
                                className={`w-4 h-4 border-2 border-t-transparent rounded-full animate-spin ${style.spinner}`}
                              />
                            ) : (
                              <svg className={`w-4 h-4 ${style.accent}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                            <span className="text-xs font-semibold text-text-primary">
                              {formatToolLabel(tool.name)}
                            </span>
                            <span className="text-[11px] text-text-muted font-mono">
                              {tool.name}
                            </span>
                          </div>
                          {rangeLabel && (
                            <span className={`text-[11px] px-2 py-0.5 rounded-full ${style.badge}`}>
                              {rangeLabel}
                            </span>
                          )}
                        </div>
                        <pre className="mt-2 text-[11px] whitespace-pre-wrap text-text-muted">{argsText}</pre>
                      </div>
                    </div>
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
                    item.status === 'thinking' && !item.content ? (
                      <div className="flex items-center gap-2 text-xs text-text-muted">
                        <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                        Thinking...
                      </div>
                    ) : (
                      <div className="chat-markdown">
                        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                          {item.content}
                        </ReactMarkdown>
                      </div>
                    )
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

      {chatError && (
        <div className="mt-4 bg-error/10 border border-error/30 rounded-lg p-3">
          <p className="text-sm text-error">{chatError}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Share progress or ask for guidance..."
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
