export function MockBadge({ label = "MOCK DATA" }: { label?: string }) {
  return <span className="mock-badge">{label}</span>;
}
