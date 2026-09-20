import { useCallback, useEffect, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../api/client';
import { CurrentReading } from '../types';

type Range = '1h' | '24h' | '7d' | '30d';

const RANGES: Record<Range, { seconds: number; label: string }> = {
  '1h': { seconds: 3600, label: '1H' },
  '24h': { seconds: 86400, label: '24H' },
  '7d': { seconds: 604800, label: '7D' },
  '30d': { seconds: 2592000, label: '30D' },
};

const LINE_COLORS = ['#64ffda', '#79b8ff', '#7ee787', '#f0b72f', '#ff7b72', '#a8ff78'];

const fmtX = (ts: string, range: Range) => {
  const d = new Date(ts);
  return range === '7d' || range === '30d'
    ? d.toLocaleDateString([], { month: 'numeric', day: 'numeric' })
    : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

export function ChartWidget({ current }: { current: CurrentReading[] }) {
  const [range, setRange] = useState<Range>('24h');
  const [metric, setMetric] = useState('temperature');
  const [data, setData] = useState<Record<string, unknown>[]>([]);

  const metrics = [...new Set(current.map((r) => r.metric))];
  const keys = current
    .filter((r) => r.metric === metric)
    .map((r) => ({ key: `${r.device}.${r.metric}`, label: r.label }));

  const load = useCallback(async () => {
    if (!keys.length) {
      setData([]);
      return;
    }
    const from = new Date(Date.now() - RANGES[range].seconds * 1000).toISOString();
    const results = await Promise.all(
      keys.map((k) => api.history(k.key, from).catch(() => []))
    );
    const merged: Record<string, Record<string, unknown>> = {};
    results.forEach((rows, i) => {
      rows.forEach((r) => {
        merged[r.timestamp] = {
          ...merged[r.timestamp],
          timestamp: r.timestamp,
          [keys[i].key]: r.value,
        };
      });
    });
    setData(
      Object.values(merged).sort(
        (a, b) =>
          new Date(a.timestamp as string).getTime() -
          new Date(b.timestamp as string).getTime()
      )
    );
  }, [range, metric, current]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (metrics.length && !metrics.includes(metric)) setMetric(metrics[0]);
  }, [current]);

  return (
    <div className="bg-card border border-line rounded-2xl p-4 h-full overflow-hidden flex flex-col">
      <div className="flex gap-1.5 flex-wrap items-center mb-2">
        {metrics.map((m) => (
          <button
            key={m}
            onClick={() => setMetric(m)}
            className={`px-3 min-h-[32px] rounded-full text-xs font-medium capitalize ${
              metric === m ? 'bg-primary text-dark' : 'bg-card2 text-muted'
            }`}
          >
            {m}
          </button>
        ))}
        <span className="ml-auto flex gap-1.5">
          {(Object.keys(RANGES) as Range[]).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-3 min-h-[32px] rounded-full text-xs font-medium ${
                range === r ? 'bg-primary text-dark' : 'bg-card2 text-muted'
              }`}
            >
              {RANGES[r].label}
            </button>
          ))}
        </span>
      </div>
      <div className="flex-1 min-h-0">
        {keys.length === 0 ? (
          <p className="font-mono text-xs text-muted pt-6 text-center">
            no sensors reporting {metric}
          </p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#263242" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(ts) => fmtX(ts, range)}
                stroke="#8b98a5"
                fontSize={10}
                minTickGap={40}
              />
              <YAxis stroke="#8b98a5" fontSize={10} width={40} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{
                  background: '#141b24',
                  border: '1px solid #263242',
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {keys.map((k, i) => (
                <Line
                  key={k.key}
                  type="monotone"
                  dataKey={k.key}
                  name={k.label}
                  stroke={LINE_COLORS[i % LINE_COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
