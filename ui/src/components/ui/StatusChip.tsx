import Chip from "@mui/material/Chip";
import type { StatusTone } from "../../lib/muiTheme";

/** Tone is a view tone from lib/places. Colour never carries the meaning alone: the word is always shown. */
export function StatusChip({ tone, label, large }: { tone: StatusTone; label: string; large?: boolean }) {
  return (
    <Chip
      label={label}
      size={large ? "medium" : "small"}
      data-tone={tone}
      sx={(theme) => {
        const c = theme.vars!.palette.status[tone];
        return { bgcolor: c.soft, color: c.ink, border: 1, borderColor: c.border, fontSize: large ? "1.05rem" : undefined };
      }}
    />
  );
}
