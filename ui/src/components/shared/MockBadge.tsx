export function MockBadge({ label = "MOCK DATA", title }: { label?: string; title?: string }) {
  return (
    <span className="mock-badge" title={title}>
      {label}
    </span>
  );
}
