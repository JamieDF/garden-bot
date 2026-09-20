import { useState } from 'react';
import { Device } from '../types';

export function CameraWidget({ device }: { device?: Device }) {
  const [err, setErr] = useState(false);
  return (
    <div className="bg-black border border-line rounded-2xl h-full overflow-hidden flex items-center justify-center">
      {err ? (
        <div className="text-center font-mono text-muted text-xs">
          <div className="text-xl mb-1">📹</div>
          no signal{device ? ` · ${device.label}` : ''}
        </div>
      ) : (
        <img
          src="/stream.mjpg"
          alt={device?.label || 'live feed'}
          className="max-w-full max-h-full object-contain"
          onError={() => setErr(true)}
        />
      )}
    </div>
  );
}
