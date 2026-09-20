import { CurrentReading } from '../types';

const COLORS: Record<string, string> = {
  temperature: 'text-primary',
  humidity: 'text-moss',
  pressure: 'text-muted',
  moisture: 'text-sky',
};

interface Props {
  reading?: CurrentReading;
  sensorKey?: string;
}

export function MetricCard({ reading, sensorKey }: Props) {
  const label = reading?.label || sensorKey?.split('.')[0]?.replace(/_/g, ' ') || sensorKey || 'metric';
  const metric = reading?.metric || sensorKey?.split('.')[1] || '';
  return (
    <div className="bg-card border border-line rounded-2xl p-3.5 h-full overflow-hidden flex flex-col justify-center">
      <p className="text-[11px] text-muted uppercase tracking-wide truncate">
        {label} <span className="normal-case">{metric && metric !== 'value' ? `· ${metric}` : ''}</span>
      </p>
      <p className={`font-mono text-2xl font-medium ${COLORS[metric] || 'text-text'} whitespace-nowrap`}>
        {reading ? reading.value.toFixed(1) : '--'}
        <span className="text-[13px] text-muted"> {reading?.unit || ''}</span>
      </p>
    </div>
  );
}
