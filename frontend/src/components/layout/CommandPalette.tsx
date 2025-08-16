import { useEffect, useMemo, useState } from 'react';
import { Command, Search, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface CommandItem {
  label: string;
  hint?: string;
  action: () => void;
  group?: string;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (open) {
        if (e.key === 'Escape') setOpen(false);
        if (e.key === 'ArrowDown') setSelected((s) => s + 1);
        if (e.key === 'ArrowUp') setSelected((s) => Math.max(0, s - 1));
        if (e.key === 'Enter') items[selected]?.action();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, selected]);

  const items: CommandItem[] = useMemo(() => ([
    { label: 'Go to Dashboard', group: 'Navigation', action: () => navigate('/dashboard') },
    { label: 'Go to Transactions', group: 'Navigation', action: () => navigate('/transactions') },
    { label: 'Go to Budgets', group: 'Navigation', action: () => navigate('/budgets') },
    { label: 'Go to Goals', group: 'Navigation', action: () => navigate('/goals') },
    { label: 'Go to Insights', group: 'Navigation', action: () => navigate('/insights') },
    { label: 'Go to Timeline', group: 'Navigation', action: () => navigate('/timeline') },
    { label: 'Open Settings', group: 'Navigation', action: () => navigate('/settings') },
    { label: 'Add Transaction', group: 'Actions', action: () => navigate('/transactions?new=1') },
  ]), [navigate]);

  const filtered = items.filter((it) => it.label.toLowerCase().includes(query.toLowerCase()));
  const boundedSelected = Math.min(selected, Math.max(0, filtered.length - 1));

  useEffect(() => setSelected(0), [query, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
      <div className="absolute left-1/2 top-24 -translate-x-1/2 w-full max-w-xl">
        <div className="glass-surface p-2 rounded-xl border border-border">
          <div className="flex items-center gap-2 px-2 py-1.5 border-b border-border">
            <Command className="h-4 w-4 opacity-70" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search commands..."
              className="flex-1 bg-transparent outline-none text-sm"
            />
            <span className="text-[10px] opacity-60">Ctrl/⌘+K</span>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="p-4 text-sm opacity-70">No results</div>
            ) : (
              filtered.map((it, idx) => (
                <button
                  key={it.label}
                  className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between ${idx === boundedSelected ? 'bg-[hsl(var(--border)/0.25)]' : ''}`}
                  onMouseEnter={() => setSelected(idx)}
                  onClick={() => { it.action(); setOpen(false); }}
                >
                  <span>{it.label}</span>
                  <ArrowRight className="h-3 w-3 opacity-70" />
                </button>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


