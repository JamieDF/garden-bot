import { useState } from 'react';
import { AgentStatus, JournalEntry } from '../types';
import { api } from '../api/client';

interface Props {
  status: AgentStatus | null;
  musings: JournalEntry[];
}

const fmtTime = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';

export function BotCard({ status, musings }: Props) {
  const [q, setQ] = useState('');
  const [reply, setReply] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const latest = musings.find((e) => e.kind === 'decision');
  const speak =
    latest?.data?.decision?.speak || latest?.data?.outcome?.narration || null;
  const mood = latest?.data?.decision?.mood;

  const ask = async () => {
    if (!q.trim() || busy) return;
    setBusy(true);
    try {
      const res = await api.agentChat(q.trim());
      setReply(res.reply);
      setQ('');
    } catch {
      setReply('…no answer. brain unreachable.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-card border border-line rounded-2xl p-4 flex gap-3.5 h-full overflow-hidden">
      <div className="w-12 h-12 rounded-full bg-primary/15 flex items-center justify-center flex-none overflow-hidden">
        <img src="/garden-bot.svg" alt="garden bot" className="w-9 h-9" />
      </div>
      <div className="min-w-0 min-h-0 flex-1 flex flex-col">
        <div className="flex items-center gap-2 flex-wrap mb-2">
          <span className="font-bold text-text">garden bot</span>
          {mood && (
            <span className="text-[11px] font-medium px-2.5 h-6 inline-flex items-center rounded-full bg-card2 text-text font-mono">
              {mood}
            </span>
          )}
          <span className="font-mono text-[11px] text-muted">
            {status?.enabled
              ? `awake · last ${fmtTime(status.last_wake)} · every ${Math.round(status.wake_interval / 60)}m`
              : 'sleeping · llm disabled'}
          </span>

        </div>
        <div className="bg-primary/15 rounded-xl px-4 py-3 font-mono text-[15px] leading-relaxed text-text flex items-end gap-3">
          <span className="min-w-0">{speak ? `“${speak}”` : '…'}</span>
          {latest && (
            <span className="text-[10px] text-muted flex-none ml-auto">
              {fmtTime(latest.timestamp)}
            </span>
          )}
        </div>
        {reply && (
          <div className="mt-2 bg-card2 rounded-xl px-4 py-3 font-mono text-[13px] leading-relaxed text-text">
            {reply}
          </div>
        )}
        <div className="mt-3 border-t border-line pt-2 flex-1 min-h-0 flex flex-col">
          <div className="flex-1 min-h-0 overflow-y-auto">
            {musings
              .filter((e) => e.kind === 'decision' && e.id !== latest?.id)
              .slice(0, 12)
              .map((e) => (
                <div key={e.id} className="flex gap-3 py-1.5 border-b border-line/60 last:border-0">
                  <span className="font-mono text-[11px] text-muted pt-0.5 w-11 flex-none">
                    {fmtTime(e.timestamp)}
                  </span>
                  <span className="font-mono text-[12.5px] text-text/90 leading-snug">
                    {e.data.decision?.speak || e.data.outcome?.narration || e.data.decision?.observation}
                  </span>
                </div>
              ))}
          </div>
          <div className="flex gap-2 mt-2.5">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && ask()}
              placeholder="ask it anything…"
              className="flex-1 bg-card2 border border-line rounded-lg px-3 py-2.5 font-mono text-[13px] text-text placeholder:text-muted min-h-[42px]"
            />
            <button
              onClick={ask}
              disabled={busy || !status?.enabled}
              className="min-h-[42px] px-4 rounded-lg bg-primary text-dark font-semibold text-xs disabled:opacity-40"
            >
              {busy ? '…' : 'Ask'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
