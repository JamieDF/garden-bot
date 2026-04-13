import { SensorReadings } from '../types';

interface SensorCardProps {
  title: string;
  sensor: keyof SensorReadings;
  value: number | null;
  unit: string;
  icon: string;
}

export function SensorCard({ title, value, unit, icon }: SensorCardProps) {
  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <span style={styles.icon}>{icon}</span>
        <span style={styles.title}>{title}</span>
      </div>
      <div style={styles.value}>
        {value !== null ? (
          <>
            <span style={styles.number}>{value.toFixed(1)}</span>
            <span style={styles.unit}>{unit}</span>
          </>
        ) : (
          <span style={styles.loading}>--</span>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#16213e',
    borderRadius: '12px',
    padding: '16px',
    minWidth: '160px',
    flex: '1 1 160px',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '8px',
  },
  icon: {
    fontSize: '20px',
  },
  title: {
    fontSize: '14px',
    color: '#8892b0',
    fontWeight: 500,
  },
  value: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '4px',
  },
  number: {
    fontSize: '32px',
    fontWeight: 600,
    color: '#64ffda',
  },
  unit: {
    fontSize: '16px',
    color: '#8892b0',
  },
  loading: {
    fontSize: '32px',
    color: '#8892b0',
  },
};
