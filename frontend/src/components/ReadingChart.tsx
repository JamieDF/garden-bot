import { useEffect, useState } from 'react';
import { Reading } from '../types';

type TimeRange = '1h' | '24h' | '7d' | '30d';

interface ReadingChartProps {
  sensor: string;
  color: string;
}

const TIME_RANGES: Record<TimeRange, { seconds: number; label: string }> = {
  '1h': { seconds: 3600, label: '1h' },
  '24h': { seconds: 86400, label: '24h' },
  '7d': { seconds: 604800, label: '7d' },
  '30d': { seconds: 2592000, label: '30d' },
};

export function ReadingChart({ sensor, color }: ReadingChartProps) {
  const [data, setData] = useState<Reading[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<TimeRange>('1h');

  useEffect(() => {
    async function fetchData() {
      try {
        const fromTime = new Date(Date.now() - TIME_RANGES[timeRange].seconds * 1000).toISOString();
        const params = new URLSearchParams({ sensor, from_time: fromTime, limit: '5000' });
        const res = await fetch(`/api/history?${params}`);
        const json = await res.json();
        setData(json.reverse()); // Oldest first for chart
      } catch (err) {
        console.error('Failed to fetch history:', err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [sensor, timeRange]);

  if (loading) {
    return (
      <div style={styles.container}>
        <h3 style={styles.title}>{formatSensorName(sensor)}</h3>
        <div style={styles.loading}>Loading...</div>
      </div>
    );
  }

  const values = data.map((r) => r.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const height = 120;
  const width = 100;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1 || 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>{formatSensorName(sensor)}</h3>
        <div style={styles.buttons}>
          {(Object.keys(TIME_RANGES) as TimeRange[]).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              style={{
                ...styles.button,
                ...(timeRange === range ? styles.buttonActive : {}),
              }}
            >
              {TIME_RANGES[range].label}
            </button>
          ))}
        </div>
      </div>
      <div style={styles.chartContainer}>
        {values.length > 1 ? (
          <svg viewBox={`0 0 ${width} ${height}`} style={styles.chart}>
            <polyline
              fill="none"
              stroke={color}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={points}
            />
          </svg>
        ) : (
          <div style={styles.noData}>Not enough data</div>
        )}
      </div>
      <div style={styles.stats}>
        <span>Min: {min.toFixed(1)}</span>
        <span>Max: {max.toFixed(1)}</span>
      </div>
    </div>
  );
}

function formatSensorName(sensor: string): string {
  return sensor
    .replace(/_/g, ' ')
    .replace('inside', 'Inside ')
    .replace('outside', 'Outside ')
    .replace('temp', 'Temp')
    .replace('humidity', 'Humidity')
    .replace('probe', 'Probe');
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: '#16213e',
    borderRadius: '12px',
    padding: '16px',
    flex: '1 1 280px',
    minWidth: '200px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  title: {
    fontSize: '14px',
    fontWeight: 500,
    color: '#8892b0',
    margin: 0,
  },
  buttons: {
    display: 'flex',
    gap: '4px',
  },
  button: {
    background: 'transparent',
    border: '1px solid #8892b0',
    borderRadius: '4px',
    color: '#8892b0',
    fontSize: '11px',
    padding: '2px 6px',
    cursor: 'pointer',
  },
  buttonActive: {
    background: '#64ffda',
    borderColor: '#64ffda',
    color: '#0a0a0f',
  },
  chartContainer: {
    height: '120px',
    width: '100%',
  },
  chart: {
    width: '100%',
    height: '100%',
  },
  stats: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '12px',
    color: '#8892b0',
    marginTop: '8px',
  },
  loading: {
    height: '120px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#8892b0',
  },
  noData: {
    height: '120px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#8892b0',
    fontSize: '14px',
  },
};
