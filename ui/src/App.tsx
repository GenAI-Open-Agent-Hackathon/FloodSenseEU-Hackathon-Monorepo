import { ConsoleProvider, useConsole } from "./context/ConsoleContext";
import { CitizenView } from "./components/CitizenView";
import { Header } from "./components/Header";
import { InsurerView } from "./components/InsurerView";

export function App() {
  return (
    <ConsoleProvider>
      <Shell />
    </ConsoleProvider>
  );
}

function Shell() {
  const { route } = useConsole();
  return (
    <div className="app-shell">
      <Header />
      <main id="content">{route === "citizen" ? <CitizenView /> : <InsurerView />}</main>
    </div>
  );
}
