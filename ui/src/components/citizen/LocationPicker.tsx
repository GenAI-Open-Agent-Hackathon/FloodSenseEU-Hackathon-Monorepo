import { useId, useState } from "react";
import type { Location } from "../../types";

interface LocationPickerProps {
  locations: readonly Location[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function LocationPicker({ locations, selectedId, onSelect }: LocationPickerProps) {
  const [query, setQuery] = useState("");
  const inputId = useId();
  const needle = query.trim().toLowerCase();
  const matches = locations.filter((l) => `${l.name} ${l.region} ${l.river}`.toLowerCase().includes(needle));

  return (
    <div className="location-picker">
      <label htmlFor={inputId} className="visually-hidden">
        Search a town or river
      </label>
      <input
        id={inputId}
        type="search"
        placeholder="Search a town or river, e.g. Passau or Ahr"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <div className="location-picker__options" role="listbox" aria-label="Locations">
        {matches.map((location) => (
          <button
            key={location.id}
            type="button"
            role="option"
            aria-selected={location.id === selectedId}
            className={`location-option ${location.id === selectedId ? "is-selected" : ""}`}
            onClick={() => onSelect(location.id)}
          >
            <strong>{location.name}</strong>
            <span>
              {location.region} · {location.country}
            </span>
          </button>
        ))}
        {matches.length === 0 && <p className="muted">No mock location matches “{query}”.</p>}
      </div>
    </div>
  );
}
