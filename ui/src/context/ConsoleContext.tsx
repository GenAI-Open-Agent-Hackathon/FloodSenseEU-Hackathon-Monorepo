import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { loadLiveViews } from "../api/client";
import { loadFixtures, type FixtureBundle } from "../fixtures/load";
import { datesOf, pointById, pointsCrossing } from "../lib/series";
import { formatDay } from "../lib/format";
import type { Answer, Approval, ApprovalStatus } from "../types/contract";
import type { EvidenceTopic, Notice, RouteId } from "../types/ui";
import { SIMULATED_ALERT_M3S } from "../types/ui";
import type {
  DataOrigin,
  DischargeDailyRow,
  ExposureJoinRow,
  HazardTimelineRow,
  ProvenanceRow,
  ValenciaPoint,
} from "../types/views";

const FIXTURE_DETAILS = {
  discharge_daily: "Fixture copy of floodsense_seed.discharge_daily (migration 012).",
  hazard_timeline: "Fixture copy of floodsense_seed.hazard_timeline for 28–30 Oct 2024 (migration 013).",
  exposure_join: "Fixture copy of floodsense_seed.exposure_join (migration 016).",
  provenance: "Fixture copy of floodsense_seed.provenance columns (migration 017).",
} as const;

interface ViewSlice<T> {
  rows: T;
  origin: DataOrigin;
  detail: string;
}

export interface ConsoleValue {
  route: RouteId;
  healthOk: boolean;
  healthDetail: string;
  discharge: ViewSlice<DischargeDailyRow[]>;
  hazard: ViewSlice<HazardTimelineRow[]>;
  exposure: ViewSlice<ExposureJoinRow[]>;
  provenance: ViewSlice<ProvenanceRow[]>;
  points: ValenciaPoint[];
  answer: Answer;
  dates: string[];
  date: string;
  setDate: (date: string) => void;
  pointId: string;
  setPointId: (pointId: string) => void;
  evidenceOpen: boolean;
  evidenceTopic: EvidenceTopic;
  openEvidence: (topic: EvidenceTopic) => void;
  closeEvidence: () => void;
  approval: Approval;
  decide: (status: ApprovalStatus, note: string) => void;
  resetApproval: () => void;
  notices: Notice[];
  markNotificationsRead: () => void;
  playing: boolean;
  playSimulation: () => void;
  stopSimulation: () => void;
}

const ConsoleContext = createContext<ConsoleValue | null>(null);

function readRoute(): RouteId {
  const hash = window.location.hash.replace(/^#\/?/, "");
  return hash.startsWith("citizen") ? "citizen" : "insurer";
}

function initialApproval(answer: Answer): Approval {
  const action = answer.playbook_actions?.[0];
  return {
    approval_id: "apr_fixture_valencia",
    run_id: answer.run_id,
    action_id: action?.action_id ?? "act_fixture_review_footprint",
    status: "pending",
    judge: answer.judge,
  };
}

const INITIAL_NOTICES: Notice[] = [
  {
    id: "replay-loaded",
    tone: "info",
    read: false,
    title: "Replay on the insurer desk",
    body: "The reviewed answer is a fixture with served_from replay. Its banner says cached at 14:32. It is not a live run.",
  },
  {
    id: "seed-loaded",
    tone: "info",
    read: false,
    title: "Discharge seed loaded",
    body: "Eight Valencia points, 20 Oct–5 Nov 2024. The source column is seed:open-meteo-flood-glofas.",
  },
];

function slice<T>(rows: T, detail: string): ViewSlice<T> {
  return { rows, origin: "fixture", detail };
}

export function ConsoleProvider({ children }: { children: ReactNode }) {
  const bundle = useMemo<FixtureBundle | { error: string }>(() => {
    try {
      return loadFixtures();
    } catch (error) {
      return { error: error instanceof Error ? error.message : "Fixtures failed to load." };
    }
  }, []);

  if ("error" in bundle) {
    return (
      <p className="boot-error" role="alert">
        {bundle.error}
      </p>
    );
  }

  return <ReadyConsole bundle={bundle}>{children}</ReadyConsole>;
}

function ReadyConsole({ bundle, children }: { bundle: FixtureBundle; children: ReactNode }) {
  const [route, setRoute] = useState<RouteId>(readRoute);
  const [healthOk, setHealthOk] = useState(false);
  const [healthDetail, setHealthDetail] = useState("Checking API health. Rows on screen are fixtures until a view route answers.");
  const [discharge, setDischarge] = useState<ViewSlice<DischargeDailyRow[]>>(
    slice(bundle.discharge, FIXTURE_DETAILS.discharge_daily),
  );
  const [hazard, setHazard] = useState<ViewSlice<HazardTimelineRow[]>>(
    slice(bundle.hazard, FIXTURE_DETAILS.hazard_timeline),
  );
  const [exposure, setExposure] = useState<ViewSlice<ExposureJoinRow[]>>(
    slice(bundle.exposure, FIXTURE_DETAILS.exposure_join),
  );
  const [provenance, setProvenance] = useState<ViewSlice<ProvenanceRow[]>>(
    slice(bundle.provenance, FIXTURE_DETAILS.provenance),
  );
  const dates = useMemo(() => datesOf(discharge.rows), [discharge.rows]);
  const [date, setDateState] = useState("2024-10-29");
  const [pointId, setPointId] = useState("VAL01");
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [evidenceTopic, setEvidenceTopic] = useState<EvidenceTopic>("discharge");
  const [approval, setApproval] = useState<Approval>(() => initialApproval(bundle.answer));
  const [notices, setNotices] = useState<Notice[]>(INITIAL_NOTICES);
  const [playing, setPlaying] = useState(false);
  const playingRef = useRef(false);
  playingRef.current = playing;
  const playUntilRef = useRef("2024-10-31");
  const raisedFor = useRef(new Set<string>());
  const previousDate = useRef(date);

  const setDate = useCallback((next: string) => {
    setDateState(next);
  }, []);

  useEffect(() => {
    if (!window.location.hash) {
      window.history.replaceState(null, "", "#/insurer");
    }
    const onHash = () => setRoute(readRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (dates.length > 0 && !dates.includes(date)) setDateState(dates[0]);
  }, [dates, date]);

  useEffect(() => {
    let cancelled = false;
    loadLiveViews().then((live) => {
      if (cancelled) return;
      setHealthOk(live.health.ok);
      setHealthDetail(live.health.detail);
      const adopt = <T,>(
        rows: T[] | null,
        miss: string,
        fixtureDetail: string,
        setSlice: (value: ViewSlice<T[]> | ((current: ViewSlice<T[]>) => ViewSlice<T[]>)) => void,
      ) => {
        if (rows) {
          setSlice({ rows, origin: "live", detail: miss });
          return;
        }
        if (live.health.ok) {
          setSlice((current) => ({ ...current, detail: `${fixtureDetail} ${miss}.` }));
        }
      };
      adopt(live.discharge_daily, live.details.discharge_daily, FIXTURE_DETAILS.discharge_daily, setDischarge);
      adopt(live.hazard_timeline, live.details.hazard_timeline, FIXTURE_DETAILS.hazard_timeline, setHazard);
      adopt(live.exposure_join, live.details.exposure_join, FIXTURE_DETAILS.exposure_join, setExposure);
      adopt(live.provenance, live.details.provenance, FIXTURE_DETAILS.provenance, setProvenance);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setDateState((current) => {
        if (current >= playUntilRef.current) return current;
        const index = dates.indexOf(current);
        return dates[index + 1] ?? current;
      });
    }, 900);
    return () => window.clearInterval(id);
  }, [playing, dates]);

  useEffect(() => {
    const before = previousDate.current;
    previousDate.current = date;
    if (!playingRef.current) return;
    if (before < date) {
      const ids = pointsCrossing(discharge.rows, before, date, SIMULATED_ALERT_M3S);
      const key = `${date}:${ids.join(",")}`;
      if (ids.length > 0 && !raisedFor.current.has(key)) {
        raisedFor.current.add(key);
        const names = ids.map((id) => {
          const point = pointById(bundle.points, id);
          return point ? `${id} ${point.name}` : id;
        });
        setNotices((list) => [
          {
            id: `sim-${key}`,
            tone: "sim",
            read: false,
            title: "Simulated alert",
            body: `Modelled discharge crossed ${SIMULATED_ALERT_M3S} m³/s on ${formatDay(date)} at ${names.join(", ")}. Simulation only. Not an official warning.`,
          },
          ...list,
        ]);
      }
    }
    if (date >= playUntilRef.current) setPlaying(false);
  }, [date, discharge.rows, bundle.points]);

  const openEvidence = useCallback((topic: EvidenceTopic) => {
    setEvidenceTopic(topic);
    setEvidenceOpen(true);
  }, []);

  const closeEvidence = useCallback(() => setEvidenceOpen(false), []);

  const decide = useCallback((status: ApprovalStatus, note: string) => {
    setApproval((current) => ({ ...current, status, note }));
  }, []);

  const resetApproval = useCallback(() => {
    setApproval(initialApproval(bundle.answer));
  }, [bundle.answer]);

  const markNotificationsRead = useCallback(() => {
    setNotices((list) => (list.some((notice) => !notice.read) ? list.map((notice) => ({ ...notice, read: true })) : list));
  }, []);

  const stopSimulation = useCallback(() => setPlaying(false), []);

  const playSimulation = useCallback(() => {
    if (playingRef.current) {
      setPlaying(false);
      return;
    }
    if (dates.length < 2) return;
    setNotices((list) => list.filter((notice) => notice.tone !== "sim"));
    raisedFor.current.clear();
    const end = dates.includes("2024-10-31") ? "2024-10-31" : dates[dates.length - 1];
    playUntilRef.current = end;
    const start = dates.find((item) => item >= "2024-10-28" && item < end) ?? dates[0];
    setDateState(start);
    setPlaying(true);
  }, [dates]);

  const value = useMemo<ConsoleValue>(
    () => ({
      route,
      healthOk,
      healthDetail,
      discharge,
      hazard,
      exposure,
      provenance,
      points: bundle.points,
      answer: bundle.answer,
      dates,
      date,
      setDate,
      pointId,
      setPointId,
      evidenceOpen,
      evidenceTopic,
      openEvidence,
      closeEvidence,
      approval,
      decide,
      resetApproval,
      notices,
      markNotificationsRead,
      playing,
      playSimulation,
      stopSimulation,
    }),
    [
      route,
      healthOk,
      healthDetail,
      discharge,
      hazard,
      exposure,
      provenance,
      bundle.points,
      bundle.answer,
      dates,
      date,
      setDate,
      pointId,
      evidenceOpen,
      evidenceTopic,
      openEvidence,
      closeEvidence,
      approval,
      decide,
      resetApproval,
      notices,
      markNotificationsRead,
      playing,
      playSimulation,
      stopSimulation,
    ],
  );

  return <ConsoleContext.Provider value={value}>{children}</ConsoleContext.Provider>;
}

export function useConsole(): ConsoleValue {
  const value = useContext(ConsoleContext);
  if (!value) throw new Error("useConsole must be used inside ConsoleProvider");
  return value;
}
