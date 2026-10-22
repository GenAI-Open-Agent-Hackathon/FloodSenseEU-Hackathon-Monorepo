import type { Region } from "../../types";

interface RegionSelectorProps {
  regions: readonly Region[];
  selectedId: string;
  onSelect: (id: string) => void;
  disabled?: boolean;
}

export function RegionSelector({ regions, selectedId, onSelect, disabled }: RegionSelectorProps) {
  return (
    <div className="segmented" role="radiogroup" aria-label="Map region">
      {regions.map((region) => (
        <button
          key={region.id}
          type="button"
          role="radio"
          aria-checked={region.id === selectedId}
          className={`segmented__option ${region.id === selectedId ? "is-active" : ""}`}
          onClick={() => onSelect(region.id)}
          disabled={disabled}
          title={`${region.name}, ${region.country}`}
        >
          {region.name}
        </button>
      ))}
    </div>
  );
}
