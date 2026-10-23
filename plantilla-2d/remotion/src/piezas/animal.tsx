// «Animal»: an animal that stands and acts like a person (fables, folk tales, the cat of the house). One drawing,
// many species: ears, muzzle, nose, tail and fur colours change with «especie»; the expressions, poses, talking
// mouth, things in the hand and gags are the same as Persona's. Origin = between the feet; ~520 px tall at scale 1.
import React from "react";
import { Brow, Cheeks, Eye, Hand, Limb, Mouth, blink, breathe, talkMouth, transition, type Pt } from "../kit/draw";
import { color, darker, LINE, lighter, mix, usePalette, type Palette } from "../kit/style";
import type { Piece, PieceProps } from "../kit/types";
import { num, str } from "../kit/types";
import { EXPRESIONES, Gag, Held } from "./persona";

export const ESPECIES = ["lobo", "zorro", "gato", "perro", "oso", "cerdo", "conejo", "raton"] as const;

type Species = {
  fur: (p: Palette) => string;
  belly: (p: Palette) => string;
  ears: "punta" | "redonda" | "larga" | "caida" | "pico";
  muzzle: "largo" | "corto" | "cerdo";
  nose: (p: Palette) => string;
  tail: "tupida" | "fina" | "rizada" | "pompon" | "corta";
  whiskers: boolean;
  teeth: boolean;
  size: number;
};

const SPECIES: Record<string, Species> = {
  lobo: { fur: (p) => mix(p.gris, p.azul, 0.35), belly: (p) => lighter(mix(p.gris, p.azul, 0.35), 0.55), ears: "punta", muzzle: "largo", nose: (p) => p.negro, tail: "tupida", whiskers: false, teeth: true, size: 1.05 },
  zorro: { fur: (p) => p.naranja, belly: (p) => p.papelLuz, ears: "punta", muzzle: "largo", nose: (p) => p.negro, tail: "tupida", whiskers: true, teeth: false, size: 0.95 },
  gato: { fur: (p) => p.ocre, belly: (p) => p.papelLuz, ears: "punta", muzzle: "corto", nose: (p) => p.rosa, tail: "fina", whiskers: true, teeth: false, size: 0.85 },
  perro: { fur: (p) => p.madera, belly: (p) => lighter(p.madera, 0.55), ears: "caida", muzzle: "largo", nose: (p) => p.negro, tail: "fina", whiskers: false, teeth: false, size: 0.95 },
  oso: { fur: (p) => darker(p.madera, 0.15), belly: (p) => lighter(p.madera, 0.35), ears: "redonda", muzzle: "corto", nose: (p) => p.negro, tail: "corta", whiskers: false, teeth: false, size: 1.2 },
  cerdo: { fur: (p) => p.rosa, belly: (p) => lighter(p.rosa, 0.4), ears: "pico", muzzle: "cerdo", nose: (p) => darker(p.rosa, 0.2), tail: "rizada", whiskers: false, teeth: false, size: 1.0 },
  conejo: { fur: (p) => p.blanco, belly: (p) => lighter(p.rosa, 0.6), ears: "larga", muzzle: "corto", nose: (p) => p.rosa, tail: "pompon", whiskers: true, teeth: true, size: 0.85 },
  raton: { fur: (p) => p.gris, belly: (p) => lighter(p.gris, 0.5), ears: "redonda", muzzle: "corto", nose: (p) => p.rosa, tail: "fina", whiskers: true, teeth: true, size: 0.7 },
};

type Face = { up: number; tilt: number; open: number; scared: boolean; happy: boolean; mouth: "sonrisa" | "risa" | "triste" | "recta" | "o" | "grito" | "picara" | "dientes" };
const FACES: Record<string, Partial<Face>> = {
  alegre: { up: 0.35, mouth: "sonrisa" }, risa: { up: 0.5, mouth: "risa", happy: true }, triste: { up: 0.2, tilt: 1, mouth: "triste", open: 0.8 },
  enfado: { up: -0.4, tilt: -1, mouth: "dientes" }, sorpresa: { up: 1, mouth: "o", scared: true }, miedo: { up: 0.7, tilt: 0.7, mouth: "o", scared: true },
  picaro: { up: 0.1, tilt: -0.5, mouth: "picara", open: 0.62 }, aburrido: { up: -0.2, open: 0.48 }, ilusion: { up: 0.85, mouth: "sonrisa" },
  decepcion: { up: 0.1, tilt: 0.8, open: 0.55, mouth: "triste" }, loco: { up: 1, mouth: "grito", scared: true },
  orgullo: { up: 0.25, mouth: "sonrisa", happy: true }, dormido: { up: -0.1, open: 0.05, mouth: "o" },
};
const faceOf = (e: string): Face => ({ up: 0, tilt: 0, open: 1, scared: false, happy: false, mouth: "recta", ...(FACES[e] ?? {}) });

const ARMS = (pose: string, dir: number): { L: [Pt, Pt]; R: [Pt, Pt] } => {
  const down = { L: [[-92, -250], [-84, -186]] as [Pt, Pt], R: [[92, -250], [84, -186]] as [Pt, Pt] };
  switch (pose) {
    case "saluda": return { L: down.L, R: [[130, -330], [140, -420]] };
    case "señala": return dir >= 0 ? { L: down.L, R: [[140, -300], [210, -330]] } : { L: [[-140, -300], [-210, -330]], R: down.R };
    case "brazos_arriba": return { L: [[-120, -360], [-110, -450]], R: [[120, -360], [110, -450]] };
    case "jarras": return { L: [[-128, -268], [-66, -210]], R: [[128, -268], [66, -210]] };
    case "cruzado": return { L: [[-70, -250], [40, -256]], R: [[70, -250], [-40, -246]] };
    case "encoge": return { L: [[-124, -280], [-164, -320]], R: [[124, -280], [164, -320]] };
    case "sujeta": return { L: [[-86, -240], [-30, -232]], R: [[86, -240], [30, -232]] };
    default: return down;
  }
};

export const Animal: Piece = ({ frame, props, prev, since, talk, seed }: PieceProps) => {
  const p = usePalette();
  const ink = p.tinta;
  const sp = SPECIES[str(props.especie, "gato")] ?? SPECIES.gato;
  const fur = color(p, props.color as string, sp.fur(p));
  const belly = color(p, props.color2 as string, sp.belly(p));
  const furDark = darker(fur, 0.25);
  const ropa = str(props.ropa, "nada");
  const cloth = color(p, props.ropa_color as string, p.azul);
  const expr = str(props.expresion, "neutral");
  const f = faceOf(expr);
  const pose = str(props.pose, "quieto");
  const dir = num(props.hacia, 1);
  const look = num(props.mira, 0);
  const r = breathe(frame, seed, 3);
  const open = Math.min(blink(frame, seed % 50, 83 + (seed % 13)), f.open);
  const mouthOpen = talkMouth(frame + seed, talk);
  const now = ARMS(pose, dir);
  const before = ARMS(str(prev.pose, pose), num(prev.hacia, dir));
  const mixPt = (a: Pt, c: Pt): Pt => [transition(a[0], c[0], since, 8, 0.1), transition(a[1], c[1], since, 8, 0.1)];
  const L: [Pt, Pt] = [mixPt(before.L[0], now.L[0]), mixPt(before.L[1], now.L[1])];
  const R: [Pt, Pt] = [mixPt(before.R[0], now.R[0]), mixPt(before.R[1], now.R[1])];
  const wag = Math.sin(frame / 7 + seed) * (expr === "alegre" || expr === "risa" ? 12 : 4);
  const hy = -430;
  const holds = str(props.sostiene, "");
  const legColor = ropa === "pantalon" || ropa === "traje" ? cloth : fur;

  const arm = (side: "L" | "R", pts: [Pt, Pt]) => (
    <g key={side}>
      <Limb p={[[side === "R" ? 62 : -62, -312], pts[0], pts[1]]} color={ropa === "camisa" || ropa === "traje" || ropa === "vestido" ? cloth : fur} width={22} />
      <Hand x={pts[1][0]} y={pts[1][1]} color={belly} r={16} />
      {side === "R" && holds && <Held what={holds} x={pts[1][0]} y={pts[1][1]} frame={frame} />}
    </g>
  );

  const tail = () => {
    const tf = { fill: fur, stroke: ink, strokeWidth: LINE, strokeLinejoin: "round" as const };
    switch (sp.tail) {
      case "tupida":
        return (
          <g transform={`rotate(${wag} 50 -200)`}>
            <path d="M44 -214 Q150 -230 196 -330 Q226 -250 176 -180 Q120 -146 44 -176 Z" {...tf} />
            <path d="M196 -330 Q214 -280 200 -250 Q186 -282 168 -292 Z" fill={belly} stroke={ink} strokeWidth={LINE - 2} strokeLinejoin="round" />
          </g>
        );
      case "fina":
        return <g transform={`rotate(${wag} 50 -190)`}><Limb p={[[50, -190], [150, -170], [170, -290]]} color={fur} width={14} /></g>;
      case "rizada":
        return <path d={`M52 -200 q30 -10 36 10 q4 22 -18 22 q-16 -2 -10 -18 q10 -14 28 -6`} fill="none" stroke={ink} strokeWidth={LINE + 3} strokeLinecap="round" />;
      case "pompon":
        return <circle cx={70} cy={-200} r={30} fill={lighter(fur, 0.5)} stroke={ink} strokeWidth={LINE} />;
      default:
        return <ellipse cx={62} cy={-200} rx={26} ry={20} {...tf} />;
    }
  };

  const ears = () => {
    const ef = { fill: fur, stroke: ink, strokeWidth: LINE, strokeLinejoin: "round" as const };
    const inner = lighter(p.rosa, 0.2);
    switch (sp.ears) {
      case "punta":
        return [-1, 1].map((s) => (
          <g key={s}>
            <path d={`M${s * 74} ${hy - 40} L${s * 82} ${hy - 140} L${s * 24} ${hy - 72} Z`} {...ef} />
            <path d={`M${s * 68} ${hy - 56} L${s * 74} ${hy - 116} L${s * 40} ${hy - 78} Z`} fill={inner} />
          </g>
        ));
      case "redonda":
        return [-1, 1].map((s) => (
          <g key={s}>
            <circle cx={s * 70} cy={hy - 70} r={sp === SPECIES.raton ? 46 : 32} {...ef} />
            <circle cx={s * 70} cy={hy - 70} r={sp === SPECIES.raton ? 30 : 18} fill={inner} />
          </g>
        ));
      case "larga":
        return [-1, 1].map((s) => (
          <g key={s} transform={`rotate(${s * (8 + Math.sin(frame / 9 + s) * 3)} ${s * 34} ${hy - 70})`}>
            <path d={`M${s * 14} ${hy - 70} Q${s * 20} ${hy - 250} ${s * 44} ${hy - 252} Q${s * 70} ${hy - 250} ${s * 60} ${hy - 70} Z`} {...ef} />
            <path d={`M${s * 28} ${hy - 90} Q${s * 32} ${hy - 220} ${s * 44} ${hy - 224} Q${s * 54} ${hy - 220} ${s * 50} ${hy - 90} Z`} fill={inner} />
          </g>
        ));
      case "caida":
        return [-1, 1].map((s) => (
          <path key={s} d={`M${s * 60} ${hy - 70} Q${s * 120} ${hy - 60} ${s * 104} ${hy + 40} Q${s * 86} ${hy + 60} ${s * 70} ${hy + 20} Z`} fill={furDark} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
        ));
      default: // pico (pig)
        return [-1, 1].map((s) => (
          <path key={s} d={`M${s * 50} ${hy - 70} L${s * 96} ${hy - 110} L${s * 80} ${hy - 40} Z`} fill={fur} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
        ));
    }
  };

  const muzzle = () => {
    if (sp.muzzle === "cerdo") {
      return (
        <g>
          <ellipse cx={0} cy={hy + 34} rx={40} ry={28} fill={sp.nose(p)} stroke={ink} strokeWidth={LINE - 1} />
          <ellipse cx={-13} cy={hy + 34} rx={6} ry={10} fill={darker(sp.nose(p), 0.4)} />
          <ellipse cx={13} cy={hy + 34} rx={6} ry={10} fill={darker(sp.nose(p), 0.4)} />
        </g>
      );
    }
    const long = sp.muzzle === "largo";
    return (
      <g>
        <ellipse cx={0} cy={hy + (long ? 46 : 38)} rx={long ? 60 : 46} ry={long ? 50 : 34} fill={belly} stroke={ink} strokeWidth={LINE - 1} />
        <path d={`M-${long ? 24 : 14} ${hy + 18} Q0 ${hy + 8} ${long ? 24 : 14} ${hy + 18} Q${long ? 20 : 12} ${hy + 36} 0 ${hy + 40} Q-${long ? 20 : 12} ${hy + 36} -${long ? 24 : 14} ${hy + 18} Z`}
          fill={sp.nose(p)} stroke={ink} strokeWidth={LINE - 2} strokeLinejoin="round" />
        {sp.whiskers && [-1, 1].map((s) => (
          <g key={s} stroke={ink} strokeWidth={3} strokeLinecap="round">
            <line x1={s * 40} y1={hy + 44} x2={s * 98} y2={hy + 34} />
            <line x1={s * 40} y1={hy + 54} x2={s * 100} y2={hy + 58} />
          </g>
        ))}
      </g>
    );
  };

  return (
    <g transform={`scale(${sp.size}) translate(0 ${(1 - sp.size) * 0})`}>
      {tail()}
      <Limb p={[[-38, -176], [-44, -22]]} color={legColor} width={32} curve={false} />
      <Limb p={[[38, -176], [44, -22]]} color={legColor} width={32} curve={false} />
      <ellipse cx={-58} cy={-12} rx={42} ry={18} fill={furDark} stroke={ink} strokeWidth={LINE - 1} />
      <ellipse cx={58} cy={-12} rx={42} ry={18} fill={furDark} stroke={ink} strokeWidth={LINE - 1} />
      <g transform={`translate(0 ${r * 0.5})`}>
        {pose !== "cruzado" && arm("L", L)}
        <path d="M-66 -330 Q-96 -250 -78 -176 Q0 -150 78 -176 Q96 -250 66 -330 Q0 -352 -66 -330 Z" fill={fur} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
        <path d="M-36 -318 Q-50 -250 -30 -186 Q0 -178 30 -186 Q50 -250 36 -318 Q0 -326 -36 -318 Z" fill={belly} />
        {(ropa === "camisa" || ropa === "traje") && (
          <path d="M-68 -328 Q-94 -250 -80 -190 Q0 -170 80 -190 Q94 -250 68 -328 Q0 -346 -68 -328 Z" fill={cloth} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
        )}
        {ropa === "vestido" && (
          <path d="M-66 -326 Q-90 -230 -112 -120 Q0 -100 112 -120 Q90 -230 66 -326 Q0 -344 -66 -326 Z" fill={cloth} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
        )}
        {(ropa === "pantalon" || ropa === "traje") && (
          <path d="M-80 -196 Q0 -178 80 -196 L84 -150 Q0 -136 -84 -150 Z" fill={cloth} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
        )}
        {ropa === "pañuelo" && <path d="M-60 -330 Q0 -300 60 -330 L0 -270 Z" fill={cloth} stroke={ink} strokeWidth={LINE - 1} strokeLinejoin="round" />}
        {pose === "cruzado" ? [arm("L", L), arm("R", R)] : arm("R", R)}
        <g transform={`translate(0 ${r * 0.4}) rotate(${f.scared && expr === "loco" ? Math.sin(frame / 2) * 3 : 0} 0 ${hy + 60})`}>
          {ears()}
          <ellipse cx={0} cy={hy + 6} rx={92} ry={88} fill={fur} stroke={ink} strokeWidth={LINE} />
          {muzzle()}
          <Cheeks x={0} y={hy + 26} sep={68} r={13} opacity={f.happy || f.mouth === "sonrisa" ? 0.6 : 0.3} />
          {f.happy ? (
            [-1, 1].map((s) => <path key={s} d={`M${s * 34 - 13} ${hy - 26} Q${s * 34} ${hy - 42} ${s * 34 + 13} ${hy - 26}`} stroke={ink} strokeWidth={LINE} fill="none" strokeLinecap="round" />)
          ) : (
            <g>
              <Eye x={-34} y={hy - 28} r={f.scared ? 16 : 13} style={f.scared ? "blanco" : "punto"} scared={f.scared} mx={look} open={open} />
              <Eye x={34} y={hy - 28} r={f.scared ? 16 : 13} style={f.scared ? "blanco" : "punto"} scared={f.scared} mx={look} open={open} />
            </g>
          )}
          <Brow x={-36} y={hy - 58} side={-1} up={f.up} tilt={f.tilt} length={36} color={darker(fur, 0.6)} width={12} />
          <Brow x={36} y={hy - 58} side={1} up={f.up + (expr === "picaro" ? 0.6 : 0)} tilt={f.tilt} length={36} color={darker(fur, 0.6)} width={12} />
          <Mouth x={0} y={hy + (sp.muzzle === "largo" ? 72 : sp.muzzle === "cerdo" ? 74 : 62)} open={mouthOpen} width={22} shape={f.mouth} />
          {sp.teeth && mouthOpen < 0.15 && f.mouth !== "o" && f.mouth !== "grito" && (
            sp === SPECIES.lobo ? (
              <g fill={p.papelLuz} stroke={ink} strokeWidth={3} strokeLinejoin="round">
                <path d={`M-20 ${hy + 74} L-14 ${hy + 90} L-8 ${hy + 75}`} />
                <path d={`M8 ${hy + 75} L14 ${hy + 90} L20 ${hy + 74}`} />
              </g>
            ) : (
              <rect x={-9} y={hy + 66} width={18} height={16} rx={2} fill={p.papelLuz} stroke={ink} strokeWidth={3} />
            )
          )}
          <g transform={`translate(0 ${hy})`}>
            <Gag kind={str(props.gag, "")} frame={frame + seed} rx={92} ry={88} />
          </g>
        </g>
      </g>
    </g>
  );
};
Animal.kind = "actor";
Animal.about = "Animal que actúa como una persona. props: especie (lobo|zorro|gato|perro|oso|cerdo|conejo|raton), color, color2 (barriga), ropa (nada|camisa|pantalon|traje|vestido|pañuelo), ropa_color, expresion (las de Persona), pose (quieto|saluda|señala|brazos_arriba|jarras|cruzado|encoge|sujeta), hacia, mira, sostiene, gag";
Animal.head = (props) => [0, -560 * (SPECIES[str(props.especie, "gato")] ?? SPECIES.gato).size];
Animal.sheet = [
  ...ESPECIES.map((e) => ({ label: e, props: { especie: e } })),
  ...EXPRESIONES.filter((e) => e !== "neutral").map((e) => ({ label: `lobo · ${e}`, props: { especie: "lobo", expresion: e } })),
  { label: "zorro · habla", props: { especie: "zorro", _talk: 1, ropa: "camisa", ropa_color: "verde" } },
  { label: "oso · saluda", props: { especie: "oso", pose: "saluda", ropa: "pantalon" } },
  { label: "conejo · señala", props: { especie: "conejo", pose: "señala", ropa: "vestido", ropa_color: "rosa" } },
  { label: "cerdo · cesta", props: { especie: "cerdo", sostiene: "cesta", pose: "sujeta" } },
];
