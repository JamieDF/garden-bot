import { useEffect, useRef } from 'react';

export function VideoStream() {
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (imgRef.current) {
      imgRef.current.src = '/stream.mjpg?' + Date.now();
    }
  }, []);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🌿 Live Feed</h2>
      <div style={styles.streamWrapper}>
        <img
          ref={imgRef}
          alt="Live camera feed"
          style={styles.stream}
          onError={() => {
            // Retry on error after a short delay
            setTimeout(() => {
              if (imgRef.current) {
                imgRef.current.src = '/stream.mjpg?' + Date.now();
              }
            }, 2000);
          }}
        />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: '#16213e',
    borderRadius: '12px',
    padding: '16px',
  },
  title: {
    fontSize: '18px',
    fontWeight: 600,
    marginBottom: '12px',
    color: '#ccd6f6',
  },
  streamWrapper: {
    background: '#0a0a0f',
    borderRadius: '8px',
    overflow: 'hidden',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '300px',
  },
  stream: {
    maxWidth: '100%',
    maxHeight: '400px',
    objectFit: 'contain',
  },
};
