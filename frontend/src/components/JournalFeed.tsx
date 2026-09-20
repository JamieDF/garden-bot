import { JournalEntry } from '../types';

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

function line(e: JournalEntry): { mood?: string; text: string; cls: string } {
  if (e.kind === 'chat')
    return { mood: 'chat', text: `you: ${e.data.user} → ${e.data.bot}`, cls: 'text-sky' };
  if (e.kind === 'error')
    return { mood: 'error', text: String(e.data.error || 'error'), cls: 'text-danger' };
  const d = e.data.decision;
  return {
    mood: d?.mood,
    text: d?.speak || d?.observation || e.data.outcome?.narration || '—',
    cls: 'text-text/90',
  };
}

export function JournalFeed({ entries }: { entries: JournalEntry[] }) {
  return (
    <div className="bg-card border border-line rounded-2xl px-4 py-2 h-full overflow-y-auto">
      <div className="flex items-center justify-between py-2">
        <span className="text-[11px] text-muted uppercase tracking-wider">Journal</span>
        <span className="font-mono text-[11px] text-muted">agent · every wake</span>
      </div>
      {entries.length === 0 && (
        <p className="font-mono text-xs text-muted py-4">no entries yet — wake the bot.</p>
      )}
      {entries.map((e) => {
        const { mood, text, cls } = line(e);
        return (
          <div key={e.id} className="flex gap-3 py-2 border-b border-line/60 last:border-0">
            <span className="font-mono text-[11px] text-muted pt-0.5 w-11 flex-none">
              {fmtTime(e.timestamp)}
            </span>
            <div className="min-w-0">
              {mood && (
                <span className="font-mono text-[10.5px] text-muted mr-2">{mood}</span>
              )}
              <span className={`font-mono text-[12.5px] leading-snug ${cls}`}>{text}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
