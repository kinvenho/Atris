"use client";

import { findCircuitGeometry } from "@/lib/f1CircuitGeo";
import { useState } from "react";

type CircuitProfile = {
  key: string;
  aliases?: string[];
  name: string;
  length: string;
  laps: string;
  distance: string;
  firstGrandPrix: string;
  fastestLap: string;
  imageUrl?: string;
  mapPath?: string;
  markers?: Array<{ x: number; y: number }>;
};

const CIRCUIT_SVG_BASE = "https://raw.githubusercontent.com/julesr0y/f1-circuits-svg/main/circuits/minimal/white-outline";

function circuitAsset(fileName: string) {
  return `${CIRCUIT_SVG_BASE}/${fileName}`;
}

const CIRCUIT_PROFILES: CircuitProfile[] = [
  {
    key: "suzuka",
    name: "Suzuka Circuit",
    length: "5.807km",
    laps: "53",
    distance: "307.471km",
    firstGrandPrix: "1987",
    fastestLap: "1:30.983",
    aliases: ["suzuka international racing course"],
    imageUrl: circuitAsset("suzuka-2.svg"),
    mapPath:
      "M66 162 C89 133 119 113 154 105 C188 97 217 108 236 132 C253 154 250 180 220 193 C182 210 127 199 94 174 C75 160 79 139 100 128 C130 113 162 123 188 145 C218 170 253 183 292 178 C336 173 363 149 356 118 C350 91 318 80 286 91 C258 101 239 124 224 149 C205 182 173 214 128 214 C91 214 65 199 59 181 C56 173 61 167 66 162 M226 148 C244 118 270 63 317 67 C349 70 368 91 364 116",
    markers: [
      { x: 66, y: 162 },
      { x: 226, y: 148 },
      { x: 317, y: 67 },
      { x: 128, y: 214 },
    ],
  },
  {
    key: "bahrain",
    name: "Bahrain International Circuit",
    length: "5.412km",
    laps: "57",
    distance: "308.238km",
    firstGrandPrix: "2004",
    fastestLap: "1:31.447",
    imageUrl: circuitAsset("bahrain-1.svg"),
    mapPath:
      "M76 151 C96 101 139 84 180 107 C208 123 226 110 247 83 C271 52 317 61 334 94 C351 128 320 154 286 145 C252 137 232 154 222 188 C212 225 156 226 122 205 C92 187 64 181 76 151Z",
    markers: [
      { x: 76, y: 151 },
      { x: 247, y: 83 },
      { x: 222, y: 188 },
    ],
  },
  {
    key: "jeddah",
    name: "Jeddah Corniche Circuit",
    length: "6.174km",
    laps: "50",
    distance: "308.450km",
    firstGrandPrix: "2021",
    fastestLap: "1:30.734",
    imageUrl: circuitAsset("jeddah-1.svg"),
    mapPath:
      "M71 207 C116 172 157 143 183 111 C211 76 247 54 296 58 C336 61 363 88 357 119 C351 150 314 161 281 147 C247 133 220 148 199 178 C174 214 117 234 71 207Z",
    markers: [
      { x: 71, y: 207 },
      { x: 183, y: 111 },
      { x: 296, y: 58 },
    ],
  },
  {
    key: "albert park",
    name: "Albert Park Grand Prix Circuit",
    length: "5.278km",
    laps: "58",
    distance: "306.124km",
    firstGrandPrix: "1996",
    fastestLap: "1:20.260",
    aliases: ["melbourne", "albert park circuit"],
    imageUrl: circuitAsset("melbourne-2.svg"),
    mapPath:
      "M80 167 C96 101 152 70 219 82 C272 91 344 95 358 135 C372 177 318 205 263 197 C212 190 188 218 135 208 C91 200 72 183 80 167Z",
    markers: [
      { x: 80, y: 167 },
      { x: 219, y: 82 },
      { x: 263, y: 197 },
    ],
  },
  {
    key: "shanghai",
    name: "Shanghai International Circuit",
    length: "5.451km",
    laps: "56",
    distance: "305.066km",
    firstGrandPrix: "2004",
    fastestLap: "1:32.238",
    imageUrl: circuitAsset("shanghai-1.svg"),
    mapPath:
      "M73 151 C71 96 137 67 181 95 C218 118 179 167 126 151 C97 142 93 109 122 101 C159 91 204 120 220 159 C238 203 286 218 328 193 C365 171 365 119 328 99 C288 78 246 98 234 134",
    markers: [
      { x: 73, y: 151 },
      { x: 220, y: 159 },
      { x: 328, y: 193 },
    ],
  },
  {
    key: "miami",
    name: "Miami International Autodrome",
    length: "5.412km",
    laps: "57",
    distance: "308.326km",
    firstGrandPrix: "2022",
    fastestLap: "1:29.708",
    imageUrl: circuitAsset("miami-1.svg"),
    mapPath:
      "M64 159 C107 123 146 95 196 96 C242 97 265 126 248 153 C232 179 187 173 174 198 C162 223 210 235 267 214 C328 192 361 150 346 111 C331 74 269 70 232 82",
    markers: [
      { x: 64, y: 159 },
      { x: 196, y: 96 },
      { x: 267, y: 214 },
    ],
  },
  {
    key: "imola",
    aliases: ["autodromo enzo e dino ferrari", "emilia romagna"],
    name: "Autodromo Enzo e Dino Ferrari",
    length: "4.909km",
    laps: "63",
    distance: "309.049km",
    firstGrandPrix: "1980",
    fastestLap: "1:15.484",
    imageUrl: circuitAsset("imola-3.svg"),
  },
  {
    key: "monaco",
    aliases: ["circuit de monaco", "monte carlo"],
    name: "Circuit de Monaco",
    length: "3.337km",
    laps: "78",
    distance: "260.286km",
    firstGrandPrix: "1950",
    fastestLap: "1:12.909",
    imageUrl: circuitAsset("monaco-6.svg"),
  },
  {
    key: "montreal",
    aliases: ["circuit gilles", "canadian"],
    name: "Circuit Gilles-Villeneuve",
    length: "4.361km",
    laps: "70",
    distance: "305.270km",
    firstGrandPrix: "1978",
    fastestLap: "1:13.078",
    imageUrl: circuitAsset("montreal-6.svg"),
  },
  {
    key: "barcelona",
    aliases: ["catalunya", "montmelo", "spanish"],
    name: "Circuit de Barcelona-Catalunya",
    length: "4.657km",
    laps: "66",
    distance: "307.236km",
    firstGrandPrix: "1991",
    fastestLap: "1:16.330",
    imageUrl: circuitAsset("catalunya-6.svg"),
  },
  {
    key: "red bull ring",
    aliases: ["spielberg", "austrian"],
    name: "Red Bull Ring",
    length: "4.318km",
    laps: "71",
    distance: "306.452km",
    firstGrandPrix: "1970",
    fastestLap: "1:05.619",
    imageUrl: circuitAsset("spielberg-3.svg"),
  },
  {
    key: "silverstone",
    aliases: ["british"],
    name: "Silverstone Circuit",
    length: "5.891km",
    laps: "52",
    distance: "306.198km",
    firstGrandPrix: "1950",
    fastestLap: "1:27.097",
    imageUrl: circuitAsset("silverstone-8.svg"),
  },
  {
    key: "hungaroring",
    aliases: ["hungarian"],
    name: "Hungaroring",
    length: "4.381km",
    laps: "70",
    distance: "306.630km",
    firstGrandPrix: "1986",
    fastestLap: "1:16.627",
    imageUrl: circuitAsset("hungaroring-3.svg"),
  },
  {
    key: "spa",
    aliases: ["francorchamps", "belgian"],
    name: "Circuit de Spa-Francorchamps",
    length: "7.004km",
    laps: "44",
    distance: "308.052km",
    firstGrandPrix: "1950",
    fastestLap: "1:46.286",
    imageUrl: circuitAsset("spa-francorchamps-4.svg"),
  },
  {
    key: "zandvoort",
    aliases: ["dutch"],
    name: "Circuit Zandvoort",
    length: "4.259km",
    laps: "72",
    distance: "306.587km",
    firstGrandPrix: "1952",
    fastestLap: "1:11.097",
    imageUrl: circuitAsset("zandvoort-5.svg"),
  },
  {
    key: "monza",
    aliases: ["autodromo nazionale", "italian"],
    name: "Autodromo Nazionale Monza",
    length: "5.793km",
    laps: "53",
    distance: "306.720km",
    firstGrandPrix: "1950",
    fastestLap: "1:21.046",
    imageUrl: circuitAsset("monza-7.svg"),
  },
  {
    key: "baku",
    aliases: ["azerbaijan"],
    name: "Baku City Circuit",
    length: "6.003km",
    laps: "51",
    distance: "306.049km",
    firstGrandPrix: "2016",
    fastestLap: "1:43.009",
    imageUrl: circuitAsset("baku-1.svg"),
  },
  {
    key: "marina bay",
    aliases: ["singapore"],
    name: "Marina Bay Street Circuit",
    length: "4.940km",
    laps: "62",
    distance: "306.143km",
    firstGrandPrix: "2008",
    fastestLap: "1:35.867",
    imageUrl: circuitAsset("marina-bay-4.svg"),
  },
  {
    key: "americas",
    aliases: ["austin", "cota", "united states grand prix"],
    name: "Circuit of the Americas",
    length: "5.513km",
    laps: "56",
    distance: "308.405km",
    firstGrandPrix: "2012",
    fastestLap: "1:36.169",
    imageUrl: circuitAsset("austin-1.svg"),
  },
  {
    key: "mexico",
    aliases: ["hermanos rodriguez", "mexico city"],
    name: "Autodromo Hermanos Rodriguez",
    length: "4.304km",
    laps: "71",
    distance: "305.354km",
    firstGrandPrix: "1963",
    fastestLap: "1:17.774",
    imageUrl: circuitAsset("mexico-city-3.svg"),
  },
  {
    key: "interlagos",
    aliases: ["jose carlos pace", "sao paulo", "brazilian"],
    name: "Autodromo Jose Carlos Pace",
    length: "4.309km",
    laps: "71",
    distance: "305.879km",
    firstGrandPrix: "1973",
    fastestLap: "1:10.540",
    imageUrl: circuitAsset("interlagos-2.svg"),
  },
  {
    key: "las vegas",
    name: "Las Vegas Street Circuit",
    length: "6.201km",
    laps: "50",
    distance: "309.958km",
    firstGrandPrix: "2023",
    fastestLap: "1:35.490",
    imageUrl: circuitAsset("las-vegas-1.svg"),
  },
  {
    key: "lusail",
    aliases: ["losail", "qatar"],
    name: "Lusail International Circuit",
    length: "5.419km",
    laps: "57",
    distance: "308.611km",
    firstGrandPrix: "2021",
    fastestLap: "1:24.319",
    imageUrl: circuitAsset("lusail-1.svg"),
  },
  {
    key: "yas marina",
    aliases: ["abu dhabi"],
    name: "Yas Marina Circuit",
    length: "5.281km",
    laps: "58",
    distance: "306.183km",
    firstGrandPrix: "2009",
    fastestLap: "1:26.103",
    imageUrl: circuitAsset("yas-marina-2.svg"),
  },
];

function normalize(value?: string | null) {
  return (value ?? "").toLowerCase();
}

function circuitProfile(circuitName?: string | null) {
  const normalized = normalize(circuitName);
  return CIRCUIT_PROFILES.find((profile) => {
    const candidates = [profile.key, ...(profile.aliases ?? [])];
    return candidates.some((candidate) => normalized.includes(candidate));
  });
}

function formatKm(meters: number) {
  return `${(meters / 1000).toFixed(3)}km`;
}

export default function F1CircuitPanel({ circuitName }: { circuitName?: string | null }) {
  const [isOpen, setIsOpen] = useState(false);
  const geometry = findCircuitGeometry(circuitName);
  const profile = circuitProfile(circuitName);
  const title = geometry?.name ?? profile?.name ?? circuitName ?? "Track profile";
  const imageUrl = profile?.imageUrl;

  return (
    <section className="f1-side-panel f1-track-panel">
      <div className="f1-panel-header compact">
        <span className="f1-kicker">Circuit</span>
        <strong>{circuitName ?? "Track profile"}</strong>
      </div>
      {imageUrl ? (
        <>
          <button className="f1-track-map-button" type="button" onClick={() => setIsOpen(true)} aria-label={`Open ${title} circuit map`}>
            <img className="f1-track-image" src={imageUrl} alt={`${title} circuit map`} />
          </button>
          {isOpen ? (
            <div className="f1-track-modal" role="dialog" aria-modal="true" aria-label={`${title} expanded circuit map`}>
              <button className="f1-track-modal-backdrop" type="button" onClick={() => setIsOpen(false)} aria-label="Close circuit map" />
              <div className="f1-track-modal-panel">
                <div className="f1-panel-header compact">
                  <div>
                    <span className="f1-kicker">Expanded Circuit</span>
                    <h3>{title}</h3>
                  </div>
                  <button className="f1-command-link" type="button" onClick={() => setIsOpen(false)}>
                    Close
                  </button>
                </div>
                <div className="f1-track-expanded">
                  <img className="f1-track-image expanded" src={imageUrl} alt={`${title} expanded circuit map`} />
                </div>
                <div className="f1-circuit-stats modal-stats">
                  <div>
                    <span>Length</span>
                    <strong>{geometry ? formatKm(geometry.lengthMeters) : profile?.length ?? "-"}</strong>
                  </div>
                  <div>
                    <span>Laps</span>
                    <strong>{profile?.laps ?? "-"}</strong>
                  </div>
                  <div>
                    <span>Distance</span>
                    <strong>{profile?.distance ?? "-"}</strong>
                  </div>
                  <div>
                    <span>First GP</span>
                    <strong>{geometry?.firstGrandPrix ?? profile?.firstGrandPrix ?? "-"}</strong>
                  </div>
                  <div className="wide">
                    <span>Fastest Lap</span>
                    <strong>{profile?.fastestLap ?? "-"}</strong>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </>
      ) : profile?.mapPath ? (
        <>
          <svg viewBox="0 0 420 270" role="img" aria-label={`${profile.name} circuit profile`}>
            <path className="track-shadow" d={profile.mapPath} />
            <path className="track-line" d={profile.mapPath} />
            {(profile.markers ?? []).map((marker) => (
              <circle key={`${marker.x}-${marker.y}`} cx={marker.x} cy={marker.y} r="7" />
            ))}
          </svg>
          <div className="f1-circuit-stats">
            <div>
              <span>Length</span>
              <strong>{profile.length}</strong>
            </div>
            <div>
              <span>Laps</span>
              <strong>{profile.laps}</strong>
            </div>
            <div>
              <span>Distance</span>
              <strong>{profile.distance}</strong>
            </div>
            <div>
              <span>First GP</span>
              <strong>{profile.firstGrandPrix}</strong>
            </div>
            <div className="wide">
              <span>Fastest Lap</span>
              <strong>{profile.fastestLap}</strong>
            </div>
          </div>
        </>
      ) : (
        <div className="f1-circuit-empty">
          <span>Profile Pending</span>
          <strong>{circuitName ?? "Circuit data unavailable"}</strong>
        </div>
      )}
    </section>
  );
}
