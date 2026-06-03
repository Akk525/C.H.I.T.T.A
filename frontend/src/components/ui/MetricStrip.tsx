export function MetricStrip({
  items,
}: {
  items: { value: string; label: string }[];
}) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="text-center sm:text-left">
          <div className="chitta-mono text-2xl font-semibold tracking-tight text-[var(--chitta-ink)] sm:text-3xl">
            {item.value}
          </div>
          <div className="mt-1 text-xs text-[var(--chitta-muted)]">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
