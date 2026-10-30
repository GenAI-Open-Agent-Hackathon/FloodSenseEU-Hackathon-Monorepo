import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export function LoadingState({ what }: { what: string }) {
  return (
    <Stack direction="row" spacing={1.5} role="status" sx={{ p: 2, alignItems: "center" }}>
      <CircularProgress size={20} aria-hidden="true" />
      <Typography variant="body2">Loading {what}…</Typography>
    </Stack>
  );
}
