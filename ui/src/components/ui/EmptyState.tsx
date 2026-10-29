import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <Box role="status" sx={{ textAlign: "center", p: 3, border: 1, borderStyle: "dashed", borderColor: "divider", borderRadius: 2 }}>
      <Typography variant="subtitle1">{title}</Typography>
      {children && (
        <Typography variant="body2" color="text.secondary" component="div" sx={{ mt: 0.5 }}>
          {children}
        </Typography>
      )}
      {action && <Box sx={{ mt: 1.5 }}>{action}</Box>}
    </Box>
  );
}
