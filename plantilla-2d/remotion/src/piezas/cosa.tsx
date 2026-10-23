// «Cosa»: an object with a face (a mug, a jar, a box, a ball, a bottle, a book, a phone, a plant pot), with tube arms
// and little legs if wanted. Same expressions and talking mouth as Persona. Origin = the bottom centre.
import React from "react";
import { Brow, Cheeks, Eye, Hand, Limb, Mouth, blink, breathe, talkMouth, transition, type MouthShape, type Pt } from "../kit/draw";
import { color, darker, LINE, lighter, usePalette } from "../kit/style";
import type { Piece, PieceProps } from "../kit/types";
import { bool, num, str } from "../kit/types";
import { EXPRESIONES, Held } from "./persona";

export const FORMAS = ["taza", "bote", "caja", "bola", "botella", "libro", "telefono", "maceta"] as const;

const SHAPES: Record<string, { w: number; h: number; d: (w: number, h: number) => string; face: number }> = {
  taza: { w: 240, h: 250, face: 0.5, d: (w, h) => `M${-w / 2} ${-h} L${-w / 2 + 14} -10 Q0 8 ${w / 2 - 14} -10 L${w / 2} ${-h} Z` },
  bote: { w: 230, h: 300, face: 0.52, d: (w, h) => `M${-w / 2 + 20} ${-h + 40} Q${-w / 2 - 20} ${-h * 0.4} ${-w / 2 + 6} -16 Q0 10 ${w / 2 - 6} -16 Q${w / 2 + 20} ${-h * 0.4} ${w / 2 - 20} ${-h + 40} Q0 ${-h + 24} ${-w / 2 + 20} ${-h + 40} Z` },
  caja: { w: 270, h: 240, face: 0.5, d: (w, h) => `M${-w / 2} ${-h} L${w / 2} ${-h} L${w / 2} 0 L${-w / 2} 0 Z` },
  bola: { w: 260, h: 260, face: 0.48, d: (w, h) => `M0 0 A${w / 2} ${h / 2} 0 1 1 0.1 0 Z` },
  botella: { w: 150, h: 360, face: 0.42, d: (w, h) => `M${-w / 2} -10 L${-w / 2} ${-h * 0.55} Q${-w / 2} ${-h * 0.72} ${-w / 5} ${-h * 0.78} L${-w / 5} ${-h} L${w / 5} ${-h} L${w / 5} ${-h * 0.78} Q${w / 2} ${-h * 0.72} ${w / 2} ${-h * 0.55} L${w / 2} -10 Q0 4 ${-w / 2} -10 Z` },
  libro: { w: 230, h: 300, face: 0.52, d: (w, h) => `M${-w / 2} ${-h} L${w / 2} ${-h} L${w / 2} 0 L${-w / 2} 0 Z` },
  telefono: { w: 180, h: 330, face: 0.5, d: (w, h) => `M${-w / 2 + 22} ${-h} L${w / 2 - 22} ${-h} Q${w / 2} ${-h} ${w / 2} ${-h + 22} L${w / 2} -22 Q${w / 2} 0 ${w / 2 - 22} 0 L${-w / 2 + 22} 0 Q${-w / 2} 0 ${-w / 2} -22 L${-w / 2} ${-h + 22} Q${-w / 2} ${-h} ${-w / 2 + 22} ${-h} Z` },
  maceta: { w: 230, h: 200, face: 0.5, d: (w, h) => `M${-w / 2} ${-h} L${w / 2} ${-h} L${w / 2 - 26} 0 L${-w / 2 + 26} 0 Z` },
};

const FACES: Record<string, { up: number; tilt: number; open: number; mouth: MouthShape; scared: boolean; happy: boolean }> = {
  neutral: { up: 0, tilt: 0, open: 1, mouth: "recta", scared: false, happy: false },
  alegre: { up: 0.35, tilt: 0, open: 1, mouth: "sonrisa", scared: false, happy: false },
  risa: { up: 0.5, tilt: 0, open: 1, mouth: "risa", scared: false, happy: true },
  triste: { up: 0.2, tilt: 1, open: 0.8, mouth: "triste", scared: false, happy: false },
  enfado: { up: -0.4, tilt: -1, open: 1, mouth: "dientes", scared: false, happy: false },
  sorpresa: { up: 1, tilt: 0, open: 1, mouth: "o", scared: true, happy: false },
  miedo: { up: 0.7, tilt: 0.7, open: 1, mouth: "o", scared: true, happy: false },
  picaro: { up: 0.1, tilt: -0.4, open: 0.62, mouth: "picara", scared: false, happy: false },
  aburrido: { up: -0.2, tilt: 0, open: 0.48, mouth: "recta", scared: false, happy: false },
  ilusion: { up: 0.85, tilt: 0, open: 1, mouth: "sonrisa", scared: false, happy: false },
  decepcion: { up: 0.1, tilt: 0.8, open: 0.55, mouth: "triste", scared: false, happy: false },
  loco: { up: 1, tilt: 0, open: 1, mouth: "grito", scared: true, happy: false },
  orgullo: { up: 0.25, tilt: 0, open: 1, mouth: "sonrisa", scared: false, happy: true },
};

const ARMS: Record<string, [Pt, Pt]> = {
  quieto: [[-30, 50], [-22, 96]],
  saluda: [[-56, -26], [-46, -108]],
  brazos_arriba: [[-46, -46], [-34, -128]],
  señala: [[-70, 6], [-150, -10]],
  jarras: [[-56, 40], [-4, 70]],
  encoge: [[-56, 22], [-96, -16]],
};

export const Cosa: Piece = ({ frame, props, prev, since, talk, seed }: PieceProps) => {
  const p = usePalette();
  const forma = str(props.forma, "taza");
  const sh = SHAPES[forma] ?? SHAPES.taza;
  const size = num(props.tamano, 1);
  const w = sh.w * size;
  const h = sh.h * size;
  const c = color(p, props.color as string, p.naranja);
  const c2 = color(p, props.color2 as string, p.papelLuz);
  const expr = str(props.expresion, "neutral");
  const f = FACES[expr] ?? FACES.neutral;
  const open = Math.min(blink(frame, seed % 50, 83 + (seed % 19)), f.open);
  const r = breathe(frame, seed, 3);
  const squash = 1 + Math.sin((frame + seed) / 15) * 0.012;
  const faceY = -h * sh.face;
  const er = Math.min(w, h) * 0.075;
  const ex = w * 0.17;
  const pose = str(props.pose, "quieto");
  const arms = bool(props.brazos, true);
  const legs = bool(props.piernas, false);
  const ink = p.tinta;
  const mix = (a: Pt, b: Pt): Pt => [transition(a[0], b[0], since, 8), transition(a[1], b[1], since, 8)];
  const dir = num(props.hacia, 1);
  // one arm points (towards «hacia»), the other rests; every other pose is symmetric
  const sideL = (ps: string, d: number) => ARMS[ps === "señala" && d > 0 ? "quieto" : ps] ?? ARMS.quieto;
  const sideR = (ps: string, d: number) => ARMS[ps === "señala" && d < 0 ? "quieto" : ps] ?? ARMS.quieto;
  const prevPose = str(prev.pose, pose);
  const prevDir = num(prev.hacia, dir);
  const fL = sideL(prevPose, prevDir);
  const tL = sideL(pose, dir);
  const fR = sideR(prevPose, prevDir);
  const tR = sideR(pose, dir);
  const armL: [Pt, Pt] = [mix(fL[0], tL[0]), mix(fL[1], tL[1])];
  const rawR: [Pt, Pt] = [mix(fR[0], tR[0]), mix(fR[1], tR[1])];
  const R: [Pt, Pt] = [[-rawR[0][0], rawR[0][1]], [-rawR[1][0], rawR[1][1]]];
  const shoulderY = -h * 0.48;
  return (
    <g transform={`translate(0 ${legs ? -60 : 0})`}>
      {legs && (
        <g>
          <Limb p={[[-w * 0.2, -10], [-w * 0.22, 54]]} color={darker(c, 0.25)} width={16} curve={false} />
          <Limb p={[[w * 0.2, -10], [w * 0.22, 54]]} color={darker(c, 0.25)} width={16} curve={false} />
          <ellipse cx={-w * 0.22 - 8} cy={60} rx={24} ry={11} fill={p.negro} stroke={ink} strokeWidth={LINE - 1} />
          <ellipse cx={w * 0.22 + 8} cy={60} rx={24} ry={11} fill={p.negro} stroke={ink} strokeWidth={LINE - 1} />
        </g>
      )}
      {arms && (
        <g>
          <Limb p={[[-w / 2 + 10, shoulderY], [-w / 2 + armL[0][0], shoulderY + armL[0][1]], [-w / 2 + armL[1][0], shoulderY + armL[1][1]]]} color={darker(c, 0.18)} width={17} />
          <Hand x={-w / 2 + armL[1][0]} y={shoulderY + armL[1][1]} color={c2} r={15} />
        </g>
      )}
      <g transform={`translate(0 ${r * 0.3}) scale(${1 / squash} ${squash})`}>
        {forma === "taza" && <path d={`M${w / 2 - 8} ${-h * 0.78} Q${w / 2 + 70} ${-h * 0.75} ${w / 2 + 62} ${-h * 0.42} Q${w / 2 + 52} ${-h * 0.18} ${w / 2 - 10} ${-h * 0.24}`} fill="none" stroke={ink} strokeWidth={30} strokeLinecap="round" />}
        {forma === "taza" && <path d={`M${w / 2 - 8} ${-h * 0.78} Q${w / 2 + 70} ${-h * 0.75} ${w / 2 + 62} ${-h * 0.42} Q${w / 2 + 52} ${-h * 0.18} ${w / 2 - 10} ${-h * 0.24}`} fill="none" stroke={c} strokeWidth={17} strokeLinecap="round" />}
        <path d={sh.d(w, h)} fill={c} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
        {forma === "taza" && <ellipse cx={0} cy={-h} rx={w / 2} ry={18} fill={darker(c, 0.35)} stroke={ink} strokeWidth={LINE} />}
        {forma === "bote" && <rect x={-w / 2 + 14} y={-h - 4} width={w - 28} height={50} rx={6} fill={c2} stroke={ink} strokeWidth={LINE} />}
        {forma === "botella" && <rect x={-w / 5 - 4} y={-h - 26} width={w * 0.4 + 8} height={34} rx={4} fill={c2} stroke={ink} strokeWidth={LINE} />}
        {forma === "libro" && <g><rect x={-w / 2} y={-h} width={26} height={h} fill={darker(c, 0.2)} stroke={ink} strokeWidth={LINE - 2} /><rect x={-w / 2 + 44} y={-h + 26} width={w - 70} height={34} fill={c2} opacity={0.85} /></g>}
        {forma === "telefono" && <rect x={-w / 2 + 16} y={-h + 34} width={w - 32} height={h - 80} rx={6} fill={c2} stroke={ink} strokeWidth={LINE - 2} />}
        {forma === "maceta" && <g><rect x={-w / 2 - 12} y={-h - 6} width={w + 24} height={46} rx={4} fill={darker(c, 0.12)} stroke={ink} strokeWidth={LINE} />
          {[-1, 0, 1].map((k) => <path key={k} d={`M${k * 40} ${-h - 6} Q${k * 70} ${-h - 120} ${k * 34 + 12} ${-h - 180}`} stroke={p.verde} strokeWidth={14} fill="none" strokeLinecap="round" />)}</g>}
        {forma === "caja" && <path d={`M${-w / 2} ${-h} L${-w / 2 + 30} ${-h - 30} L${w / 2 + 30} ${-h - 30} L${w / 2} ${-h} M${w / 2} 0 L${w / 2 + 30} -30 L${w / 2 + 30} ${-h - 30}`} fill={lighter(c, 0.2)} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />}
        <path d={`M${-w * 0.32} ${-h * 0.9} Q${-w * 0.38} ${-h * 0.55} ${-w * 0.3} ${-h * 0.25}`} stroke={lighter(c, 0.4)} strokeWidth={12} fill="none" strokeLinecap="round" opacity={0.8} />
        {/* face */}
        <Cheeks x={0} y={faceY + er * 2.6} sep={ex * 1.45} r={er * 1.1} opacity={0.5} />
        {f.happy ? (
          [-1, 1].map((s) => <path key={s} d={`M${s * ex - er} ${faceY + 3} Q${s * ex} ${faceY - er * 1.3} ${s * ex + er} ${faceY + 3}`} stroke={ink} strokeWidth={LINE} fill="none" strokeLinecap="round" />)
        ) : (
          <g>
            <Eye x={-ex} y={faceY} r={er} scared={f.scared} open={open} mx={num(props.mira, 0)} />
            <Eye x={ex} y={faceY} r={er} scared={f.scared} open={open} mx={num(props.mira, 0)} />
          </g>
        )}
        <Brow x={-ex} y={faceY - er * 2} side={-1} up={f.up} tilt={f.tilt} length={er * 2.4} />
        <Brow x={ex} y={faceY - er * 2} side={1} up={f.up} tilt={f.tilt} length={er * 2.4} />
        <Mouth x={0} y={faceY + er * 2.4} open={talkMouth(frame + seed, talk)} width={er * 1.7} shape={f.mouth} />
      </g>
      {arms && (
        <g>
          <Limb p={[[w / 2 - 10, shoulderY], [w / 2 + R[0][0], shoulderY + R[0][1]], [w / 2 + R[1][0], shoulderY + R[1][1]]]} color={darker(c, 0.18)} width={17} />
          <Hand x={w / 2 + R[1][0]} y={shoulderY + R[1][1]} color={c2} r={15} />
          {str(props.sostiene, "") && <Held what={str(props.sostiene, "")} x={w / 2 + R[1][0]} y={shoulderY + R[1][1]} frame={frame} />}
        </g>
      )}
    </g>
  );
};
Cosa.kind = "actor";
Cosa.about = "Objeto con cara. props: forma (taza|bote|caja|bola|botella|libro|telefono|maceta), tamano (0.6..1.6), color, color2, expresion, pose (quieto|saluda|brazos_arriba|señala|jarras|encoge), hacia (1|-1: a qué lado señala), brazos, piernas, mira, sostiene";
Cosa.head = (props) => [0, -(SHAPES[str(props.forma, "taza")] ?? SHAPES.taza).h * num(props.tamano, 1) - 20];
Cosa.sheet = [
  ...EXPRESIONES.map((e) => ({ label: e, props: { expresion: e } })),
  { label: "habla", props: { _talk: 1 } },
  ...["saluda", "brazos_arriba", "señala", "jarras", "encoge"].map((x) => ({ label: x, props: { pose: x } })),
];

/** A loose object on its own (a big version of the things hands hold, plus a few more). */
export const Objeto: Piece = ({ frame, props }: PieceProps) => {
  const p = usePalette();
  const que = str(props.que, "libro");
  const ink = p.tinta;
  const st = { stroke: ink, strokeWidth: LINE, strokeLinejoin: "round" as const };
  const c = color(p, props.color as string, p.rojo);
  switch (que) {
    case "reloj":
      return (
        <g>
          <circle cx={0} cy={-150} r={140} fill={p.papelLuz} {...st} />
          {Array.from({ length: 12 }, (_, i) => <line key={i} x1={0} y1={-262} x2={0} y2={-246} stroke={ink} strokeWidth={6} transform={`rotate(${i * 30} 0 -150)`} />)}
          <line x1={0} y1={-150} x2={0} y2={-230} stroke={ink} strokeWidth={10} strokeLinecap="round" transform={`rotate(${frame * 6} 0 -150)`} />
          <line x1={0} y1={-150} x2={60} y2={-150} stroke={ink} strokeWidth={12} strokeLinecap="round" transform={`rotate(${frame * 0.5} 0 -150)`} />
          <circle cx={0} cy={-150} r={10} fill={ink} />
        </g>
      );
    case "calendario":
      return (
        <g>
          <rect x={-150} y={-320} width={300} height={320} rx={4} fill={p.papelLuz} {...st} />
          <rect x={-150} y={-320} width={300} height={80} rx={4} fill={c} {...st} />
          <text x={0} y={-266} textAnchor="middle" fontFamily="Big Shoulders" fontWeight={900} fontSize={44} fill={p.papelLuz}>{str(props.mes, "ENERO")}</text>
          <text x={0} y={-70} textAnchor="middle" fontFamily="Big Shoulders" fontWeight={900} fontSize={170} fill={ink}>{str(props.texto, "1")}</text>
        </g>
      );
    case "cartel":
      return (
        <g>
          <line x1={0} y1={0} x2={0} y2={-240} stroke={ink} strokeWidth={22} />
          <line x1={0} y1={0} x2={0} y2={-240} stroke={p.madera} strokeWidth={10} />
          <rect x={-170} y={-380} width={340} height={150} rx={4} fill={p.kraft} {...st} />
          <text x={0} y={-282} textAnchor="middle" fontFamily="Big Shoulders" fontWeight={900} fontSize={66} fill={ink}>{str(props.texto, "CARTEL")}</text>
        </g>
      );
    case "corazon":
      return <path transform={`scale(${4 + Math.sin(frame / 6) * 0.15}) translate(0 -40)`} d="M0 10 C-20 -10 -30 -26 -14 -34 C-4 -38 0 -30 0 -26 C0 -30 4 -38 14 -34 C30 -26 20 -10 0 10 Z" fill={c} stroke={ink} strokeWidth={1.6} />;
    default:
      return <g transform="scale(2.4)"><Held what={que} x={0} y={0} frame={frame} /></g>;
  }
};
Objeto.kind = "objeto";
Objeto.about = "Objeto suelo. props: que (reloj|calendario|cartel|corazon|libro|carta|telefono|taza|flor|lanza|saco|llave|gafas), color, texto, mes";
