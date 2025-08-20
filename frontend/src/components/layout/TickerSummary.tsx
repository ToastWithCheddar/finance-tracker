import { useMemo, useState } from 'react';
import { BarChart3, X } from 'lucide-react';
import { useRealtimeStore } from '../../stores/realtimeStore';

interface TickerSummaryProps {
  className?: string;
}

export function TickerSummary({ className = '' }: TickerSummaryProps) {
  const newTx = useRealtimeStore((s) => s.recentTransactions.filter((t) => t.isNew).length);
  const totalTx = useRealtimeStore((s) => s.recentTransactions.length);
  const unread = useRealtimeStore((s) => s.notifications.filter((n) => !n.read).length);
  const [open, setOpen] = useState(false);

  const items = useMemo(() => {
    const summary = [] as Array<{ label: string; value: string; color: string }>;
    summary.push({ label: 'New Tx', value: String(newTx), color: 'text-amber-300' });
    summary.push({ label: 'Notifications', value: String(unread), color: 'text-fuchsia-300' });
    summary.push({ label: 'Total Tx', value: String(totalTx), color: 'text-indigo-300' });
    return summary;
  }, [newTx, totalTx, unread]);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className={`hidden md:inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-border bg-[hsl(var(--surface))] text-sm hover:bg-[hsl(var(--border)/0.25)] ${className}`}
        aria-label="Open financial summary ticker"
      >
        <BarChart3 className="h-4 w-4" />
        <span>Show summary</span>
      </button>
    );
  }

  return (
    <div className={`relative mx-2 w-64 sm:w-80 md:w-[420px] ${className}`}>
      <div className="flex items-stretch rounded-md border border-border bg-[hsl(var(--surface)/0.8)] h-9 overflow-hidden">
        {/* Left: scrolling ticker */}
        <div className="relative flex-1 h-full overflow-hidden">
          <div className="absolute inset-y-0 left-0 w-8 pointer-events-none bg-gradient-to-r from-[hsl(var(--surface)/1)] to-transparent" />
          <div className="absolute inset-y-0 right-0 w-8 pointer-events-none bg-gradient-to-l from-[hsl(var(--surface)/1)] to-transparent" />
          <div className="h-full flex items-center">
            <div className="flex items-center gap-2 min-w-max animate-[ticker_12s_linear_infinite] will-change-transform pointer-events-none pl-2 pr-2">
              {[...items, ...items].map((it, idx) => (
                <div
                  key={`${it.label}-${idx}`}
                  className="flex items-center gap-2 px-3 py-1 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface))] mr-2"
                >
                  <span className="text-xs opacity-70">{it.label}</span>
                  <span className={`text-sm font-semibold ${it.color}`}>{it.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        {/* Right: close segment */}
        <div className="flex items-center justify-center px-2 border-l border-border bg-[hsl(var(--surface))]">
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded-md hover:bg-[hsl(var(--border)/0.25)]"
            aria-label="Close summary"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}


