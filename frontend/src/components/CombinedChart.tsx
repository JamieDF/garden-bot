import { useEffect, useState } from 'react';
import { Reading } from '../types';

interface CombinedChartProps {
  sensors: { sensor: string; color: string; label: string }[];
}

export function CombinedChart({ sensors }: CombinedChartProps) {
  const [data, setData] = useState<Record<string, Reading[]>>({});
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d' | '30d'>('24h');

  const timeRanges = {
    '1h': { seconds: 3600, label: '1h' },
    '24h': { seconds: 86400, label: '24h' },
    '7d': { seconds: 604800, label: '7d' },
    '30d': { seconds: 2592000, label: '30d' },
  };

  useEffect(() => {
    async function fetchData() {
      try {
        const fromTime = new Date(Date.now() - timeRanges[timeRange].seconds * 1000).toISOString();
        const results: Record<string, Reading[]> = {};
        
        for (const { sensor } of sensors) {
          const params = new URLSearchParams({ sensor, from_time: fromTime, limit: '5000' });
          const res = await fetch(`/api/history?${params}`);
          const json = await res.json();
          results[sensor] = json.reverse();
        }
        
        setData(results);
      } catch (err) {
        console.error('Failed to fetch history:', err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [timeRange]);

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h3 style={styles.title}>Temperature History</h3>
          <div style={styles.buttons}>
            {(Object.keys(timeRanges) as Array<keyof typeof timeRanges>).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                style={{
                  ...styles.button,
                  ...(timeRange === range ? styles.buttonActive : {}),
                }}
              >
                {timeRanges[range].label}
              </button>
            ))}
          </div>
        </div>
        <div style={styles.loading}>Loading...</div>
      </div>
    );
  }

  // Find min/max across all sensors
  let allValues: number[] = [];
  Object.values(data).forEach((readings) => {
    readings.forEach((r) => allValues.push(r.value));
  });

  if (allValues.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h3 style={styles.title}>Temperature History</h3>
        </div>
        <div style={styles.noData}>No data available</div>
      </div>
    );
  }

  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = max - min || 1;
  const height = 200;
  const width = 100;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>Temperature History</h3>
        <div style={styles.buttons}>
          {(Object.keys(timeRanges) as Array<keyof typeof timeRanges>).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              style={{
                ...styles.button,
                ...(timeRange === range ? styles.buttonActive : {}),
              }}
            >
              {timeRanges[range].label}
            </button>
          ))}
        </div>
      </div>
      <div style={styles.chartContainer}>
        <svg viewBox={`0 0 ${width} ${height}`} style={styles.chart}>
          {sensors.map(({ sensor, color }) => {
            const readings = data[sensor] || [];
            if (readings.length < 2) return null;
            
            const points = readings.map((r, i) => {
              const x = (i / (readings.length - 1)) * width;
              const y = height - ((r.value - min) / range) * height;
              return `${x},${y}`;
            }).join(' ');

            return (
              <polyline
                key={sensor}
                fill="none"
                stroke={color}
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={points}
              />
            );
          })}
        </svg>
        <div style={styles.legend}>
          {sensors.map(({ label, color }) => (
            <div key={label} style={styles.legendItem}>
              <span style={{ ...styles.legendColor, backgroundColor: color }} />
              {label}
            </div>
          ))}
        </div>
      </div>
      <div style={styles.stats}>
        <span>Min: {min.toFixed(1)}°C</span>
        <span>Max: {max.toFixed(1)}°C</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: '#16213e',
    borderRadius: '12px',
    padding: '16px',
    flex: '1 1 100%',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
    flexWrap: 'wrap',
    gap: '8px',
  },
  title: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#ccd6f6',
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
    fontSize: '12px',
    padding: '4px 10px',
    cursor: 'pointer',
  },
  buttonActive: {
    background: '#64ffda',
    borderColor: '#64ffda',
    color: '#0a0a0f',
  },
  chartContainer: {
    height: '200px',
    width: '100%',
    position: 'relative',
  },
  chart: {
    width: '100%',
    height: '180px',
  },
  legend: {
    display: 'flex',
    justifyContent: 'center',
    gap: '16px',
    marginTop: '8px',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    color: '#8892b0',
  },
  legendColor: {
    width: '12px',
    height: '12px',
    borderRadius: '2px',
  },
  stats: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '12px',
    color: '#8892b0',
    marginTop: '8px',
  },
  loading: {
    height: '200px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#8892b0',
  },
  noData: {
    height: '200px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#8892b0',
  },
};
