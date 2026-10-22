import type { RecommendedAction } from "../../types";

const urgencyLabel: Record<RecommendedAction["urgency"], string> = {
  now: "Now",
  today: "Today",
  prepare: "Prepare",
};

export function RecommendedActions({ actions }: { actions: readonly RecommendedAction[] }) {
  return (
    <ol className="actions">
      {actions.map((action) => (
        <li key={action.id} className={`action action--${action.urgency}`}>
          <span className="action__urgency">{urgencyLabel[action.urgency]}</span>
          <div>
            <strong>{action.title}</strong>
            <p>{action.detail}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
