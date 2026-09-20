import { useState } from 'react';
import { Dashboard } from './pages/Dashboard';
import { Devices } from './pages/Devices';
import { Ask } from './pages/Ask';

type Page = 'dash' | 'devices' | 'ask';

const NAV: { id: Page; label: string }[] = [
  { id: 'dash', label: 'dashboard' },
  { id: 'devices', label: 'devices' },
  { id: 'ask', label: 'ask' },
];

function App() {
  const [page, setPage] = useState<Page>('dash');

  return (
    <div className="min-h-screen bg-dark p-4 md:p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-2 mb-4">
          <span className="font-bold text-text text-base">garden bot</span>
          <nav className="ml-3 flex gap-1">
            {NAV.map((n) => (
              <button
                key={n.id}
                onClick={() => setPage(n.id)}
                className={`min-h-[36px] px-3.5 rounded-lg text-[13px] font-medium ${
                  page === n.id ? 'bg-primary/15 text-primary font-bold' : 'text-muted'
                }`}
              >
                {n.label}
              </button>
            ))}
          </nav>
        </div>
        {page === 'dash' && <Dashboard />}
        {page === 'devices' && <Devices />}
        {page === 'ask' && <Ask />}
      </div>
    </div>
  );
}

export default App;
