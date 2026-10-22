import { apiBaseUrl } from "./api/client";
import { CitationPanel } from "./components/citations/CitationPanel";
import { CitationProvider } from "./components/citations/CitationContext";
import { CitizenView } from "./components/citizen/CitizenView";
import { InsurerView } from "./components/insurer/InsurerView";
import { AppHeader } from "./components/shared/AppHeader";
import { useHashRoute } from "./hooks/useHashRoute";

export function App() {
  const [route, navigate] = useHashRoute();

  return (
    <CitationProvider>
      <div className="app">
        <AppHeader route={route} onNavigate={navigate} />
        <main className="app__main">{route === "insurer" ? <InsurerView /> : <CitizenView />}</main>
        <footer className="app__footer muted small">
          FloodSense EU mock UI · except gauges marked Live (PEGELONLINE), all data, quotes and scores are sample values for the Open Agent Hackathon 2026 · official warnings always take priority · FloodSense backend API (not called yet): <code>{apiBaseUrl}</code>
        </footer>
      </div>
      <CitationPanel />
    </CitationProvider>
  );
}
