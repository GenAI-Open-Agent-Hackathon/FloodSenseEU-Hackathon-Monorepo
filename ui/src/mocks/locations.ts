import type { Location } from "../types";

export const locations: Location[] = [
  {
    id: "bad-neuenahr-ahrweiler",
    name: "Bad Neuenahr-Ahrweiler",
    region: "Rhineland-Palatinate",
    country: "DE",
    lat: 50.5447,
    lon: 7.1133,
    river: "Ahr",
  },
  { id: "cologne", name: "Cologne", region: "North Rhine-Westphalia", country: "DE", lat: 50.9375, lon: 6.9603, river: "Rhine" },
  { id: "passau", name: "Passau", region: "Bavaria", country: "DE", lat: 48.5667, lon: 13.4319, river: "Danube" },
  { id: "valencia", name: "Valencia", region: "Valencian Community", country: "ES", lat: 39.4699, lon: -0.3763, river: "Rambla del Poyo" },
];
