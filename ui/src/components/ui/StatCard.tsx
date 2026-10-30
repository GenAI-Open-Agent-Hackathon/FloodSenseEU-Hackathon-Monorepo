import type { ReactNode } from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";

/** One labelled figure, as a term/definition pair so a screen reader hears "label, value". */
export function StatCard({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent component="dl" sx={{ m: 0 }}>
        <Typography component="dt" variant="overline" color="text.secondary">
          {label}
        </Typography>
        <Typography component="dd" variant="h3" sx={{ m: 0 }}>
          {value}
        </Typography>
        {hint && (
          <Typography component="dd" variant="caption" color="text.secondary" sx={{ m: 0, display: "block" }}>
            {hint}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
