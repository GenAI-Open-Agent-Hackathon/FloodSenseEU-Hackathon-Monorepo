import { ThemeProvider } from "@mui/material/styles";
import { muiTheme } from "./lib/muiTheme";
import { useLoadLlmBackend } from "./hooks/useLlmBackend";
import { ConsoleProvider } from "./context/ConsoleContext";
import { AskFloodSense } from "./components/AskFloodSense";
import { Colophon } from "./components/Banners";
import { DemoOffer } from "./components/ModeSwitch";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { Header } from "./components/Header";
import { PageOutlet } from "./components/PageOutlet";
import { ReplayBar } from "./components/ReplayBar";
import { SideNav } from "./components/SideNav";
import { useCollapsedNav } from "./hooks/useCollapsedNav";

export function App() {
  return (
    <ThemeProvider theme={muiTheme}>
      <ConsoleProvider>
        <Shell />
      </ConsoleProvider>
    </ThemeProvider>
  );
}

function Shell() {
  const nav = useCollapsedNav();
  useLoadLlmBackend();
  return (
    <div className="app-shell" data-nav={nav.collapsed ? "collapsed" : "open"}>
      <div className="shell-stage">
        <Header />
        <SideNav collapsed={nav.collapsed} onToggle={nav.toggle} onNavigate={nav.closeIfDrawer} drawer={nav.drawer} />
        <ReplayBar />
        <DemoOffer />
        <main id="content">
          <PageOutlet />
        </main>
        <Colophon />
      </div>
      <AskFloodSense />
      <EvidenceDrawer />
    </div>
  );
}
