import type { ReactNode } from "react";

interface CardProps {
  title: string;
  /** Small label on the right of the title, e.g. a badge or cache label. */
  aside?: ReactNode;
  /** Teammate area that would own this component; shown as a hint in the mock. */
  ownerHint?: string;
  className?: string;
  children: ReactNode;
}

export function Card({ title, aside, ownerHint, className, children }: CardProps) {
  return (
    <section className={`card ${className ?? ""}`} aria-label={title}>
      <header className="card__header">
        <h2 className="card__title">{title}</h2>
        {aside && <div className="card__aside">{aside}</div>}
      </header>
      <div className="card__body">{children}</div>
      {ownerHint && <footer className="card__owner" title="Suggested owner area (open for discussion)">Component area: {ownerHint}</footer>}
    </section>
  );
}
