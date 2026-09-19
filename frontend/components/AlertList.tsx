export interface Alert {
  id: string;
  text: string;
  severity: "info" | "warning" | "critical";
}

export default function AlertList({ alerts }: { alerts: Alert[] }) {
  const color = { info: "bg-blue-50", warning: "bg-yellow-50", critical: "bg-red-50" };
  return (
    <ul data-testid="alert-list" className="space-y-2">
      {alerts.map((a) => (
        <li key={a.id} className={`rounded border p-2 text-sm ${color[a.severity]}`}>
          {a.text}
        </li>
      ))}
    </ul>
  );
}
