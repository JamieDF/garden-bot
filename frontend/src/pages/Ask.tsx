import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { AgentStatus, JournalEntry } from '../types';

interface Msg {
  user: string;
  bot: string;
}

const SUGGESTIONS = ["how's it going?", 'should i water?', 'what changed today?'];

export function Ask() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    const [entries, st] = await Promise.all([
      api.agentJournal(30, 'chat').catch(() => [] as JournalEntry[]),
      api.agentStatus().catch(() => null),
    ]);
    setStatus(st);
    setMsgs(
      [...entries]
        .reverse()
        .map((e) => ({ user: e.data.user || '', bot: e.data.bot || '' }))
        .filter((m) => m.user || m.bot)
    );
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [msgs]);

  const send = async (text: string) => {
    if (!text.trim() || busy) return;
    setBusy(true);
    setMsgs((m) => [...m, { user: text.trim(), bot: '…' }]);
    try {
      const res = await api.agentChat(text.trim());
      setMsgs((m) => [...m.slice(0, -1), { user: text.trim(), bot: res.reply }]);
    } catch {
      setMsgs((m) => [...m.slice(0, -1), { user: text.trim(), bot: '…no answer. brain unreachable.' }]);
    } finally {
      setBusy(false);
      setQ('');
    }
  };

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-3">
      <div className="bg-card border border-line rounded-2xl p-4 flex flex-col min-h-[420px]">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-base">🌱</span>
          <span className="font-semibold text-sm text-text">ask garden bot</span>
          <span className="ml-auto font-mono text-[11px] text-muted">
            {status?.enabled ? `${status.model} · has sensor context` : 'llm disabled'}
          </span>
        </div>
        <div className="flex-1 overflow-y-auto">
          {msgs.length === 0 && (
            <p className="font-mono text-xs text-muted py-6 text-center">
              nothing asked yet. it has opinions, i promise.
            </p>
          )}
          {msgs.map((m, i) => (
            <div key={i}>
              <div className="flex justify-end mb-1.5">
                <div className="max-w-[78%] bg-primary text-dark rounded-2xl px-3.5 py-2.5 font-mono text-[13px] leading-snug">
                  {m.user}
                </div>
              </div>
              <div className="flex mb-3">
                <div className="max-w-[78%] bg-card2 rounded-2xl px-3.5 py-2.5 font-mono text-[13px] leading-snug text-text">
                  {m.bot}
                </div>
              </div>
            </div>
          ))}
          <div ref={bottom} />
        </div>
        <div className="flex gap-2 flex-wrap mb-2.5">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="px-3 min-h-[32px] rounded-full border border-dashed border-line font-mono text-xs text-muted"
            >
              {s}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send(q)}
            placeholder="ask it anything…"
            className="flex-1 bg-card2 border border-line rounded-lg px-3.5 py-2.5 font-mono text-[13px] text-text placeholder:text-muted min-h-[44px]"
          />
          <button
            onClick={() => send(q)}
            disabled={busy || !status?.enabled}
            className="min-h-[44px] px-5 rounded-lg bg-primary text-dark font-semibold text-sm disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
