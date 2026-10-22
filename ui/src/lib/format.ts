import type { RiskLevel } from "../types";

const timeFormat = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" });
const dateFormat = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" });
const eurCompact = new Intl.NumberFormat("en-GB", { style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("en-GB");

export const formatTime = (iso: string): string => timeFormat.format(new Date(iso));
export const formatDate = (iso: string): string => dateFormat.format(new Date(iso));
export const formatEur = (value: number): string => eurCompact.format(value);
export const formatInt = (value: number): string => integer.format(value);
export const formatPercent = (ratio: number): string => `${Math.round(ratio * 100)}%`;

/** Whole minutes from now until `iso` plus `seconds`; never negative. */
export function minutesUntilExpiry(iso: string, seconds: number, now: number = Date.now()): number {
  const remainingMs = Date.parse(iso) + seconds * 1000 - now;
  return Math.max(0, Math.ceil(remainingMs / 60_000));
}

export function minutesSince(iso: string, now: number = Date.now()): number {
  return Math.max(0, Math.floor((now - Date.parse(iso)) / 60_000));
}

export const riskLevels: readonly RiskLevel[] = ["low", "moderate", "high", "severe"];

export const riskLabel: Record<RiskLevel, string> = {
  low: "Low",
  moderate: "Moderate",
  high: "High",
  severe: "Severe",
};
