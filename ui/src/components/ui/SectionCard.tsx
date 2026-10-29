import { useId, type ReactNode } from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

/** A labelled region: <section aria-labelledby> with a heading, optional actions, and a body. */
export function SectionCard({ title, actions, children, headingLevel = 3 }: { title: ReactNode; actions?: ReactNode; children: ReactNode; headingLevel?: 2 | 3 | 4 }) {
  const id = useId();
  return (
    <Card component="section" aria-labelledby={id} sx={{ minWidth: 0 }}>
      <CardContent sx={{ display: "grid", gap: 1.5 }}>
        <Stack direction="row" spacing={1} useFlexGap sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
          <Typography id={id} variant="h3" component={`h${headingLevel}`}>
            {title}
          </Typography>
          {actions}
        </Stack>
        {children}
      </CardContent>
    </Card>
  );
}
