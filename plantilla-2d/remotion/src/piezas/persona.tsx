// «Persona»: the parametric human of the house. One drawing, many people: body, skin, hair, clothes, hat, beard,
// glasses, 13 expressions and 11 poses, with blinking, breathing, a mouth that moves with its voice and hands that
// can hold things. Origin (0, 0) = between the feet; about 470 px tall at scale 1.
import React from "react";
import { Brow, Cheeks, Eye, Hand, Limb, Mouth, blink, breathe, talkMouth, transition, type MouthShape, type Pt } from "../kit/draw";
import { color, darker, LINE, lighter, usePalette, type Palette } from "../kit/style";
import type { Piece, PieceProps } from "../kit/types";
import { bool, num, str } from "../kit/types";

export const EXPRESIONES = ["neutral", "alegre", "risa", "triste", "enfado", "sorpresa", "miedo", "picaro", "aburrido", "ilusion", "decepcion", "loco", "orgullo", "dormido"] as const;
export const POSES = ["quieto", "saluda", "señala", "brazos_arriba", "jarras", "cruzado", "piensa", "encoge", "alcanza", "sujeta", "carga"] as const;

type Face = { up: number; tilt: number; open: number; look: number; mouth: MouthShape; eyes: "punto" | "blanco"; scared: boolean; happy: boolean; cheeks: number; wild: boolean };

const FACES: Record<string, Partial<Face>> = {
  neutral: {},
  alegre: { up: 0.35, mouth: "sonrisa", cheeks: 0.75 },
  risa: { up: 0.5, mouth: "risa", happy: true, cheeks: 0.85 },
  triste: { up: 0.25, tilt: 1, mouth: "triste", open: 0.8, look: 0.5 },
  enfado: { up: -0.4, tilt: -1, mouth: "dientes" },
  sorpresa: { up: 1, mouth: "o", scared: true },
  miedo: { up: 0.75, tilt: 0.7, mouth: "o", scared: true },
  picaro: { up: 0.1, tilt: -0.4, mouth: "picara", open: 0.62 },
  aburrido: { up: -0.2, open: 0.48, mouth: "recta" },
  ilusion: { up: 0.85, mouth: "sonrisa", cheeks: 0.9, eyes: "blanco" },
  decepcion: { up: 0.1, tilt: 0.8, open: 0.55, mouth: "triste", look: 0.7 },
  loco: { up: 1, mouth: "grito", scared: true, wild: true },
  orgullo: { up: 0.25, mouth: "sonrisa", happy: true, cheeks: 0.6 },
  dormido: { up: -0.1, open: 0.05, mouth: "o", cheeks: 0.4 },
};

const face = (expr: string): Face => ({
  up: 0, tilt: 0, open: 1, look: 0, mouth: "recta", eyes: "punto", scared: false, happy: false, cheeks: 0.5, wild: false,
  ...(FACES[expr] ?? {}),
});

type Body = { legH: number; torsoH: number; shoulder: number; hip: number; headR: number; headRy: number; belly: number; limb: number };
export const BODIES: Record<string, Body> = {
  normal: { legH: 150, torsoH: 150, shoulder: 56, hip: 46, headR: 66, headRy: 70, belly: 0, limb: 18 },
  alto: { legH: 185, torsoH: 175, shoulder: 52, hip: 40, headR: 56, headRy: 74, belly: 0, limb: 16 },
  ancho: { legH: 115, torsoH: 160, shoulder: 80, hip: 74, headR: 70, headRy: 70, belly: 26, limb: 20 },
  peque: { legH: 95, torsoH: 105, shoulder: 42, hip: 36, headR: 68, headRy: 68, belly: 0, limb: 15 },
};

/** Where both hands go for each pose (screen-left arm «L», screen-right arm «R»), relative to the shoulders. */
export const armPose = (pose: string, b: Body, dir: number): { L: [Pt, Pt]; R: [Pt, Pt] } => {
  const s = b.shoulder;
  const down: { L: [Pt, Pt]; R: [Pt, Pt] } = { L: [[-s - 24, 60], [-s - 14, 128]], R: [[s + 24, 60], [s + 14, 128]] };
  switch (pose) {
    case "saluda":
      return { L: down.L, R: [[s + 66, -10], [s + 76, -112]] };
    case "señala":
      return dir >= 0 ? { L: down.L, R: [[s + 80, 8], [s + 172, -16]] } : { L: [[-s - 80, 8], [-s - 172, -16]], R: down.R };
    case "brazos_arriba":
      return { L: [[-s - 52, -40], [-s - 40, -150]], R: [[s + 52, -40], [s + 40, -150]] };
    case "jarras":
      return { L: [[-s - 62, 52], [-s + 2, 118]], R: [[s + 62, 52], [s - 2, 118]] };
    case "cruzado":
      return { L: [[-s - 10, 78], [s - 24, 74]], R: [[s + 10, 78], [-s + 24, 82]] };
    case "piensa":
      return { L: [[-s - 10, 84], [-6, 70]], R: [[s + 46, 70], [12, -18]] };
    case "encoge":
      return { L: [[-s - 62, 40], [-s - 104, -6]], R: [[s + 62, 40], [s + 104, -6]] };
    case "sujeta":
      return { L: [[-s - 14, 82], [-26, 92]], R: [[s + 14, 82], [26, 92]] };
    case "carga":
      return { L: [[-s - 30, 50], [-s - 70, 20]], R: [[s + 50, -30], [s + 110, -120]] };
    default:
      return down;
  }
};

const HAIR_FRONT: Record<string, (r: number, ry: number) => string> = {
  corto: (r, ry) => `M${-r - 4} ${-ry * 0.15} Q${-r - 8} ${-ry - 14} 0 ${-ry - 18} Q${r + 8} ${-ry - 14} ${r + 4} ${-ry * 0.15} Q${r * 0.6} ${-ry * 0.62} ${r * 0.1} ${-ry * 0.55} Q${-r * 0.5} ${-ry * 0.78} ${-r - 4} ${-ry * 0.15} Z`,
  flequillo: (r, ry) => `M${-r - 5} ${-ry * 0.05} Q${-r - 10} ${-ry - 16} 0 ${-ry - 20} Q${r + 10} ${-ry - 16} ${r + 5} ${-ry * 0.05} L${r * 0.75} ${-ry * 0.45} L${r * 0.4} ${-ry * 0.3} L${r * 0.05} ${-ry * 0.46} L${-r * 0.35} ${-ry * 0.3} L${-r * 0.75} ${-ry * 0.45} Z`,
  punta: (r, ry) => `M${-r - 2} ${-ry * 0.3} L${-r * 0.8} ${-ry - 34} L${-r * 0.4} ${-ry - 10} L${-r * 0.1} ${-ry - 44} L${r * 0.25} ${-ry - 12} L${r * 0.6} ${-ry - 38} L${r * 0.75} ${-ry - 6} L${r + 2} ${-ry * 0.3} Q0 ${-ry * 0.72} ${-r - 2} ${-ry * 0.3} Z`,
  rizos: (r, ry) => {
    let d = `M${-r - 14} ${-ry * 0.05}`;
    for (let i = 0; i <= 8; i++) {
      const a = Math.PI + (i / 8) * Math.PI;
      const x = Math.cos(a) * (r + 14);
      const y = Math.sin(a) * (ry + 16) - 6;
      d += ` Q${x * 1.18} ${y * 1.15 - 10} ${x} ${y}`;
    }
    return d + ` Q0 ${-ry * 0.55} ${-r - 14} ${-ry * 0.05} Z`;
  },
};

export const hairOf = (p: Palette, props: Record<string, unknown>) => color(p, props.pelo_color as string, p.pelos[1]);

/** Where things are on a Persona (piece coordinates, at rest): to draw ON TOP of one without copying its numbers
 *  (a hood, a crown of flowers, something on the shoulder…). */
export const personaAnchors = (props: Record<string, unknown>) => {
  const b = BODIES[str(props.cuerpo, "normal")] ?? BODIES.normal;
  const hipY = -b.legH;
  const shY = hipY - b.torsoH + 10;
  const neckY = hipY - b.torsoH;
  const headY = neckY - b.headRy + 6;
  return { head: [0, headY] as Pt, headR: b.headR, headRy: b.headRy, neck: [0, neckY] as Pt, hip: [0, hipY] as Pt,
           shoulderL: [-b.shoulder, shY] as Pt, shoulderR: [b.shoulder, shY] as Pt, top: [0, headY - b.headRy] as Pt };
};

export const Persona: Piece = ({ frame, props, prev, since, talk, seed, place }: PieceProps) => {
  const p = usePalette();
  const b = BODIES[str(props.cuerpo, "normal")] ?? BODIES.normal;
  const skin = color(p, props.piel as string, p.pieles[0]);
  const top = color(p, props.color as string, p.turquesa);
  const bottom = color(p, props.color2 as string, p.azul);
  const hairC = hairOf(p, props);
  const shoes = color(p, props.zapatos as string, p.negro);
  const ropa = str(props.ropa, "camisa");
  const pelo = str(props.pelo, "corto");
  const expr = str(props.expresion, "neutral");
  const pose = str(props.pose, "quieto");
  const dir = num(props.hacia, 1);
  const f = face(expr);
  const look = num(props.mira, dir * 0.4);
  const r = breathe(frame, seed, 2.6);
  const open = Math.min(blink(frame, seed % 60, 89 + (seed % 17)), f.open);
  const mouthOpen = talkMouth(frame + seed, talk);

  const hipY = -b.legH;
  const shY = hipY - b.torsoH + 10;
  const neckY = hipY - b.torsoH;
  const headY = neckY - b.headRy + 6;
  const legSpread = ropa === "vestido" ? 18 : 24;
  const carga = pose === "carga";

  // hands: interpolate from the previous pose (since) and aim at a target for «alcanza»
  const target = (props.objetivo as Pt | undefined) ?? null;
  const armsNow = armPose(pose, b, dir);
  const armsPrev = armPose(str(prev.pose, pose), b, num(prev.hacia, dir));
  if (pose === "alcanza") {
    const k = place.scale || 1;
    const local: Pt = target ? [(target[0] - place.x) / k * (place.flip ? -1 : 1), (target[1] - place.y) / k - shY] : [b.shoulder + 170, -20];
    const side = local[0] >= 0 ? "R" : "L";
    const sx = side === "R" ? b.shoulder : -b.shoulder;
    const hand: Pt = [local[0], local[1]];
    const elbow: Pt = [(sx + hand[0]) / 2, (0 + hand[1]) / 2 + 36];
    armsNow[side] = [elbow, hand];
  }
  const mixPt = (a: Pt, c: Pt): Pt => [transition(a[0], c[0], since, 8, 0.08), transition(a[1], c[1], since, 8, 0.08)];
  const L: [Pt, Pt] = [mixPt(armsPrev.L[0], armsNow.L[0]), mixPt(armsPrev.L[1], armsNow.L[1])];
  const R: [Pt, Pt] = [mixPt(armsPrev.R[0], armsNow.R[0]), mixPt(armsPrev.R[1], armsNow.R[1])];
  const sleeve = ropa === "vestido" ? skin : ropa === "armadura" ? p.gris : top;
  const holds = str(props.sostiene, "");
  const glasses = transition(num(prev.gafas, num(props.gafas, 0)), num(props.gafas, 0), since, 10, 0.2);

  const arm = (side: "L" | "R", pts: [Pt, Pt]) => {
    const sx = side === "R" ? b.shoulder : -b.shoulder;
    const hand: Pt = [pts[1][0], shY + pts[1][1]];
    return (
      <g key={side}>
        <Limb p={[[sx, shY + 8], [pts[0][0], shY + pts[0][1]], hand]} color={sleeve} width={b.limb} />
        <Hand x={hand[0]} y={hand[1]} color={skin} />
        {side === "R" && holds && <Held what={holds} x={hand[0]} y={hand[1]} frame={frame} />}
      </g>
    );
  };

  const lean = carga ? 10 : 0;
  const legColor = ropa === "vestido" || ropa === "tunica" ? color(p, props.medias as string, skin) : ropa === "armadura" ? color(p, props.medias as string, bottom) : bottom;
  const hop = carga ? -Math.abs(Math.sin(frame / 2.4)) * 16 : 0;
  return (
    <g transform={`translate(0 ${hop}) rotate(${lean})`}>
      {/* legs */}
      <Limb p={[[-legSpread, hipY + 10], [-legSpread - (carga ? 30 : 0) * Math.sin(frame / 2.4), -16]]} color={legColor} width={b.limb + 1} curve={false} />
      <Limb p={[[legSpread, hipY + 10], [legSpread + (carga ? 30 : 0) * Math.sin(frame / 2.4), -16]]} color={legColor} width={b.limb + 1} curve={false} />
      <ellipse cx={-legSpread - 10} cy={-8} rx={30} ry={13} fill={shoes} stroke={p.tinta} strokeWidth={LINE - 1} />
      <ellipse cx={legSpread + 10} cy={-8} rx={30} ry={13} fill={shoes} stroke={p.tinta} strokeWidth={LINE - 1} />

      <g transform={`translate(0 ${r * 0.4})`}>
        {(bool(props.capa) || bool(props.capucha)) && (
          <path d={`M${-b.shoulder - 10} ${shY - 10} Q${-b.shoulder - 60} ${hipY + 40} ${-b.shoulder - 40} ${hipY + 110} Q0 ${hipY + 130} ${b.shoulder + 40} ${hipY + 110} Q${b.shoulder + 60} ${hipY + 40} ${b.shoulder + 10} ${shY - 10} Z`}
            fill={color(p, props.capa_color as string, p.rojo)} stroke={p.tinta} strokeWidth={LINE} strokeLinejoin="round" />
        )}
        {/* back arm when crossed / thinking goes first */}
        {(pose === "cruzado" ? [] : [arm("L", L)])}
        <Torso ropa={ropa} b={b} hipY={hipY} shY={shY} neckY={neckY} top={top} bottom={bottom} skin={skin} p={p} />
        {pose === "cruzado" ? [arm("L", L), arm("R", R)] : arm("R", R)}
        {/* neck + head */}
        <rect x={-14} y={neckY - 20} width={28} height={30} fill={skin} stroke={p.tinta} strokeWidth={LINE - 1} />
        <g transform={`translate(0 ${headY + r * 0.6}) rotate(${f.wild ? Math.sin(frame / 2) * 3 : pose === "piensa" ? -6 : 0})`}>
          <Head props={props} b={b} f={f} p={p} skin={skin} hairC={hairC} pelo={pelo} open={open} look={look} mouthOpen={mouthOpen} glasses={glasses} frame={frame} />
          {bool(props.capucha) && <Hood rx={b.headR} ry={b.headRy} c={color(p, props.capa_color as string, p.rojo)} />}
          <Gag kind={str(props.gag, "")} frame={frame + seed} rx={b.headR} ry={b.headRy} />
        </g>
      </g>
    </g>
  );
};
Persona.kind = "actor";
Persona.about = "Persona por parámetros. props: cuerpo (normal|alto|ancho|peque), piel, ropa (camisa|vestido|tunica|traje|armadura|sudadera), color, color2, zapatos, pelo (corto|flequillo|punta|rizos|largo|moño|coleta|calvo), pelo_color, barba (no|barba|bigote|perilla|tres_dias), sombrero (no|gorro|sombrero|corona|pañuelo|gorra|casco), gafas (0..1), expresion, pose, hacia (1|-1), mira (-1..1), objetivo [x,y] (pose alcanza), sostiene (gafas|libro|carta|telefono|taza|flor|lanza|saco|llave|cesta|hacha|espada|vela|varita|paraguas|bolsa), capa y capucha (true) con capa_color, gag (moscas|corazones|sudor|zzz|idea|rabia|olor|estrellas)";
Persona.head = (props) => {
  const b = BODIES[str(props.cuerpo, "normal")] ?? BODIES.normal;
  return [0, -b.legH - b.torsoH - b.headRy - 10];
};
Persona.sheet = [
  ...EXPRESIONES.map((e) => ({ label: e, props: { expresion: e } })),
  { label: "habla", props: { _talk: 1 } },
  ...POSES.filter((x) => x !== "quieto" && x !== "alcanza").map((x) => ({ label: x, props: { pose: x } })),
];

const Torso: React.FC<{ ropa: string; b: Body; hipY: number; shY: number; neckY: number; top: string; bottom: string; skin: string; p: Palette }> = ({
  ropa, b, hipY, shY, neckY, top, bottom, skin, p,
}) => {
  const s = b.shoulder;
  const h = b.hip + b.belly * 0.5;
  const ink = p.tinta;
  const stroke = { stroke: ink, strokeWidth: LINE, strokeLinejoin: "round" as const };
  if (ropa === "vestido") {
    return (
      <g>
        <path d={`M${-s + 6} ${shY} Q${-s - 8} ${shY + 60} ${-h - 4} ${hipY + 10} L${-h - 46} ${hipY + 74} Q0 ${hipY + 96} ${h + 46} ${hipY + 74} L${h + 4} ${hipY + 10} Q${s + 8} ${shY + 60} ${s - 6} ${shY} Q0 ${shY - 16} ${-s + 6} ${shY} Z`} fill={top} {...stroke} />
        <path d={`M${-h - 30} ${hipY + 52} Q0 ${hipY + 74} ${h + 30} ${hipY + 52}`} fill="none" stroke={lighter(top, 0.35)} strokeWidth={7} />
        <path d={`M-22 ${neckY + 6} Q0 ${neckY + 32} 22 ${neckY + 6}`} fill={skin} stroke={ink} strokeWidth={3} />
      </g>
    );
  }
  if (ropa === "tunica") {
    return (
      <g>
        <path d={`M${-s + 4} ${shY} Q${-s - 6} ${hipY - 40} ${-h - 14} ${hipY + 70} Q0 ${hipY + 86} ${h + 14} ${hipY + 70} Q${s + 6} ${hipY - 40} ${s - 4} ${shY} Q0 ${shY - 14} ${-s + 4} ${shY} Z`} fill={top} {...stroke} />
        <path d={`M${-s - 2} ${hipY - 4} Q0 ${hipY + 16} ${s + 2} ${hipY - 4}`} stroke={ink} strokeWidth={20} fill="none" strokeLinecap="round" />
        <path d={`M${-s - 2} ${hipY - 4} Q0 ${hipY + 16} ${s + 2} ${hipY - 4}`} stroke={bottom} strokeWidth={10} fill="none" strokeLinecap="round" />
      </g>
    );
  }
  if (ropa === "armadura") {
    return (
      <g>
        <path d={`M${-h} ${hipY - 6} L${-h - 8} ${hipY + 46} Q0 ${hipY + 60} ${h + 8} ${hipY + 46} L${h} ${hipY - 6} Z`} fill={bottom} {...stroke} />
        <path d={`M${-s + 2} ${shY - 4} Q${-s - 12} ${(shY + hipY) / 2} ${-h + 2} ${hipY + 4} Q0 ${hipY + 18} ${h - 2} ${hipY + 4} Q${s + 12} ${(shY + hipY) / 2} ${s - 2} ${shY - 4} Q0 ${shY - 22} ${-s + 2} ${shY - 4} Z`} fill={lighter(p.gris, 0.25)} {...stroke} />
        <path d={`M${-s * 0.5} ${shY + 10} Q${-s * 0.62} ${(shY + hipY) / 2} ${-h * 0.5} ${hipY - 8}`} stroke={p.papelLuz} strokeWidth={10} fill="none" strokeLinecap="round" opacity={0.8} />
        <circle cx={-s} cy={shY + 6} r={b.limb + 6} fill={lighter(p.gris, 0.25)} stroke={ink} strokeWidth={LINE} />
        <circle cx={s} cy={shY + 6} r={b.limb + 6} fill={lighter(p.gris, 0.25)} stroke={ink} strokeWidth={LINE} />
        <rect x={-h - 2} y={hipY - 18} width={(h + 2) * 2} height={18} rx={3} fill={p.maderaSombra} stroke={ink} strokeWidth={LINE - 2} />
      </g>
    );
  }
  // camisa, traje, sudadera: trousers + top
  return (
    <g>
      <path d={`M${-h} ${hipY - 10} L${-h - 4} ${hipY + 24} L${h + 4} ${hipY + 24} L${h} ${hipY - 10} Z`} fill={bottom} {...stroke} />
      <path d={`M${-s + 4} ${shY} Q${-s - 10 - b.belly} ${(shY + hipY) / 2} ${-h} ${hipY + 4} Q0 ${hipY + 14 + b.belly * 0.4} ${h} ${hipY + 4} Q${s + 10 + b.belly} ${(shY + hipY) / 2} ${s - 4} ${shY} Q0 ${shY - 16} ${-s + 4} ${shY} Z`} fill={top} {...stroke} />
      {ropa === "traje" && (
        <g>
          <path d={`M-18 ${neckY + 4} L0 ${neckY + 60} L18 ${neckY + 4} Z`} fill={p.papelLuz} stroke={ink} strokeWidth={3} />
          <path d={`M-6 ${neckY + 14} L6 ${neckY + 14} L10 ${neckY + 90} L0 ${neckY + 104} L-10 ${neckY + 90} Z`} fill={bottom} stroke={ink} strokeWidth={3} />
          <path d={`M-30 ${neckY + 2} L-6 ${neckY + 74} M30 ${neckY + 2} L6 ${neckY + 74}`} stroke={ink} strokeWidth={4} />
        </g>
      )}
      {ropa === "sudadera" && (
        <g>
          <path d={`M${-s * 0.55} ${hipY - 54} L${s * 0.55} ${hipY - 54} L${s * 0.62} ${hipY - 6} L${-s * 0.62} ${hipY - 6} Z`} fill={darker(top, 0.1)} stroke={ink} strokeWidth={3} />
          <path d={`M-30 ${neckY + 8} Q0 ${neckY + 30} 30 ${neckY + 8}`} fill="none" stroke={ink} strokeWidth={4} />
          <line x1={-10} x2={-12} y1={neckY + 22} y2={neckY + 62} stroke={ink} strokeWidth={3} />
          <line x1={10} x2={12} y1={neckY + 22} y2={neckY + 62} stroke={ink} strokeWidth={3} />
        </g>
      )}
      {ropa === "camisa" && (
        <g>
          <path d={`M-20 ${neckY + 4} L0 ${neckY + 24} L20 ${neckY + 4}`} fill={skin} stroke={ink} strokeWidth={3} />
          {[0, 1, 2].map((i) => <circle key={i} cx={0} cy={neckY + 44 + i * 30} r={3.5} fill={ink} />)}
        </g>
      )}
    </g>
  );
};

const Head: React.FC<{
  props: Record<string, unknown>; b: Body; f: Face; p: Palette; skin: string; hairC: string; pelo: string; open: number; look: number;
  mouthOpen: number; glasses: number; frame: number;
}> = ({ props, b, f, p, skin, hairC, pelo, open, look, mouthOpen, glasses, frame }) => {
  const rx = b.headR;
  const ry = b.headRy;
  const ink = p.tinta;
  const barba = str(props.barba, "no");
  const sombrero = str(props.sombrero, "no");
  const beardC = color(p, props.barba_color as string, hairC);
  const eyeY = -ry * 0.08;
  const eyeX = rx * 0.36;
  const er = rx * 0.19;
  const longHair = pelo === "largo" || pelo === "moño" || pelo === "coleta";
  return (
    <g>
      {/* hair behind the head */}
      {longHair && (
        <path d={`M${-rx - 12} ${-ry * 0.3} Q${-rx - 22} ${ry * 0.9} ${-rx + 8} ${ry * 1.15} L${rx - 8} ${ry * 1.15} Q${rx + 22} ${ry * 0.9} ${rx + 12} ${-ry * 0.3} Z`}
          fill={hairC} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
      )}
      {pelo === "coleta" && <path d={`M${rx * 0.6} ${-ry * 0.6} Q${rx + 70} ${-ry * 0.2} ${rx + 40} ${ry * 0.7} Q${rx + 20} ${ry * 0.2} ${rx * 0.4} ${-ry * 0.2} Z`} fill={hairC} stroke={ink} strokeWidth={LINE} />}
      {pelo === "moño" && <circle cx={0} cy={-ry - 26} r={rx * 0.42} fill={hairC} stroke={ink} strokeWidth={LINE} />}
      {/* ears */}
      <ellipse cx={-rx + 2} cy={eyeY + 10} rx={13} ry={17} fill={skin} stroke={ink} strokeWidth={LINE - 1} />
      <ellipse cx={rx - 2} cy={eyeY + 10} rx={13} ry={17} fill={skin} stroke={ink} strokeWidth={LINE - 1} />
      <ellipse cx={0} cy={0} rx={rx} ry={ry} fill={skin} stroke={ink} strokeWidth={LINE} />
      {barba === "tres_dias" && <path d={`M${-rx * 0.82} ${ry * 0.15} Q${-rx * 0.7} ${ry * 0.95} 0 ${ry * 0.98} Q${rx * 0.7} ${ry * 0.95} ${rx * 0.82} ${ry * 0.15} Q0 ${ry * 0.42} ${-rx * 0.82} ${ry * 0.15} Z`} fill={beardC} opacity={0.25} />}
      <Cheeks x={0} y={ry * 0.32} sep={rx * 0.55} r={rx * 0.15} opacity={f.cheeks} />
      {/* eyes */}
      {f.happy ? (
        <g>
          {[-1, 1].map((s) => <path key={s} d={`M${s * eyeX - er} ${eyeY + 4} Q${s * eyeX} ${eyeY - er * 1.2} ${s * eyeX + er} ${eyeY + 4}`} stroke={ink} strokeWidth={LINE} fill="none" strokeLinecap="round" />)}
        </g>
      ) : (
        <g>
          <Eye x={-eyeX} y={eyeY} r={f.wild ? er * 1.25 : er} style={f.eyes} scared={f.scared} mx={look} my={f.look} open={open} />
          <Eye x={eyeX} y={eyeY} r={f.wild ? er * 0.95 : er} style={f.eyes} scared={f.scared} mx={look} my={f.look} open={open} />
        </g>
      )}
      <Brow x={-eyeX} y={eyeY - er * 1.9} side={-1} up={f.up + (f.wild ? Math.sin(frame / 3) * 0.3 : 0)} tilt={f.tilt} length={rx * 0.42} color={pelo === "calvo" ? darker(skin, 0.4) : hairC === p.pelos[4] ? p.gris : ink} />
      <Brow x={eyeX} y={eyeY - er * 1.9} side={1} up={f.up + (str(props.expresion, "") === "picaro" ? 0.6 : 0)} tilt={f.tilt} length={rx * 0.42} color={pelo === "calvo" ? darker(skin, 0.4) : hairC === p.pelos[4] ? p.gris : ink} />
      {/* nose */}
      <path d={`M${2} ${eyeY + er * 0.9} Q${10} ${eyeY + er * 2.2} ${-2} ${eyeY + er * 2.5}`} fill="none" stroke={darker(skin, 0.35)} strokeWidth={4} strokeLinecap="round" />
      {/* beard / moustache */}
      {barba === "barba" && <path d={`M${-rx * 0.86} ${ry * 0.05} Q${-rx * 0.8} ${ry * 1.25} 0 ${ry * 1.32} Q${rx * 0.8} ${ry * 1.25} ${rx * 0.86} ${ry * 0.05} Q${rx * 0.5} ${ry * 0.55} 0 ${ry * 0.5} Q${-rx * 0.5} ${ry * 0.55} ${-rx * 0.86} ${ry * 0.05} Z`} fill={beardC} stroke={ink} strokeWidth={LINE - 1} strokeLinejoin="round" />}
      {barba === "perilla" && <path d={`M${-rx * 0.28} ${ry * 0.62} Q${-rx * 0.2} ${ry * 1.3} 0 ${ry * 1.45} Q${rx * 0.2} ${ry * 1.3} ${rx * 0.28} ${ry * 0.62} Q0 ${ry * 0.72} ${-rx * 0.28} ${ry * 0.62} Z`} fill={beardC} stroke={ink} strokeWidth={LINE - 1} strokeLinejoin="round" />}
      <Mouth x={0} y={ry * 0.5} open={mouthOpen} width={rx * 0.27} shape={f.mouth} />
      {(barba === "bigote" || barba === "barba" || barba === "perilla") && (
        <path d={`M0 ${ry * 0.38} Q${-rx * 0.3} ${ry * 0.22} ${-rx * 0.62} ${ry * 0.44} Q${-rx * 0.66} ${ry * 0.54} ${-rx * 0.5} ${ry * 0.54} Q${-rx * 0.3} ${ry * 0.4} 0 ${ry * 0.44} Q${rx * 0.3} ${ry * 0.4} ${rx * 0.5} ${ry * 0.54} Q${rx * 0.66} ${ry * 0.54} ${rx * 0.62} ${ry * 0.44} Q${rx * 0.3} ${ry * 0.22} 0 ${ry * 0.38} Z`}
          fill={beardC} stroke={ink} strokeWidth={LINE - 2} strokeLinejoin="round" />
      )}
      {/* hair on top */}
      {pelo !== "calvo" && (pelo in HAIR_FRONT ? (
        <path d={HAIR_FRONT[pelo](rx, ry)} fill={hairC} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
      ) : (
        <path d={HAIR_FRONT.flequillo(rx, ry)} fill={hairC} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
      ))}
      {glasses > 0.02 && (
        <g transform={`translate(0 ${eyeY - (1 - Math.min(1, glasses)) * 160})`} opacity={Math.min(1, glasses * 2)}>
          <Glasses w={eyeX} r={er * 1.55} />
        </g>
      )}
      <Hat kind={sombrero} rx={rx} ry={ry} c={color(p, props.sombrero_color as string, sombrero === "corona" ? p.ocre : p.rojo)} />
    </g>
  );
};

export const Glasses: React.FC<{ w: number; r: number; tint?: boolean }> = ({ w, r }) => {
  const p = usePalette();
  return (
    <g>
      <path d={`M${-w - r} 0 L${-w - r - 16} -6 M${w + r} 0 L${w + r + 16} -6`} stroke={p.tinta} strokeWidth={5} strokeLinecap="round" />
      <path d={`M${-w + r - 2} -2 Q0 ${-r * 0.6} ${w - r + 2} -2`} stroke={p.tinta} strokeWidth={5} fill="none" />
      {[-w, w].map((cx) => (
        <g key={cx}>
          <circle cx={cx} cy={0} r={r} fill="#DDEFF2" fillOpacity={0.35} stroke={p.tinta} strokeWidth={6} />
          <path d={`M${cx - r * 0.5} ${-r * 0.2} L${cx - r * 0.1} ${-r * 0.6}`} stroke={p.papelLuz} strokeWidth={4} strokeLinecap="round" />
        </g>
      ))}
    </g>
  );
};

const Hat: React.FC<{ kind: string; rx: number; ry: number; c: string }> = ({ kind, rx, ry, c }) => {
  const p = usePalette();
  const ink = p.tinta;
  const st = { stroke: ink, strokeWidth: LINE, strokeLinejoin: "round" as const };
  switch (kind) {
    case "gorro":
      return (
        <g>
          <path d={`M${-rx - 6} ${-ry * 0.45} Q${-rx} ${-ry - 50} 0 ${-ry - 52} Q${rx} ${-ry - 50} ${rx + 6} ${-ry * 0.45} Q0 ${-ry * 0.75} ${-rx - 6} ${-ry * 0.45} Z`} fill={c} {...st} />
          <path d={`M${-rx - 10} ${-ry * 0.46} Q0 ${-ry * 0.82} ${rx + 10} ${-ry * 0.46}`} stroke={ink} strokeWidth={22} fill="none" strokeLinecap="round" />
          <path d={`M${-rx - 10} ${-ry * 0.46} Q0 ${-ry * 0.82} ${rx + 10} ${-ry * 0.46}`} stroke={darker(c, 0.2)} strokeWidth={11} fill="none" strokeLinecap="round" />
        </g>
      );
    case "sombrero":
      return (
        <g>
          <ellipse cx={0} cy={-ry * 0.62} rx={rx * 1.75} ry={20} fill={c} {...st} />
          <path d={`M${-rx * 0.8} ${-ry * 0.62} L${-rx * 0.72} ${-ry - 46} Q0 ${-ry - 62} ${rx * 0.72} ${-ry - 46} L${rx * 0.8} ${-ry * 0.62} Z`} fill={c} {...st} />
          <rect x={-rx * 0.8} y={-ry * 0.62 - 26} width={rx * 1.6} height={16} fill={darker(c, 0.35)} />
        </g>
      );
    case "corona":
      return <path d={`M${-rx * 0.62} ${-ry * 0.8} L${-rx * 0.72} ${-ry - 50} L${-rx * 0.3} ${-ry - 14} L0 ${-ry - 64} L${rx * 0.3} ${-ry - 14} L${rx * 0.72} ${-ry - 50} L${rx * 0.62} ${-ry * 0.8} Z`} fill={c} {...st} />;
    case "pañuelo":
      return (
        <g>
          <path d={`M${-rx - 8} ${-ry * 0.1} Q${-rx - 10} ${-ry - 26} 0 ${-ry - 28} Q${rx + 10} ${-ry - 26} ${rx + 8} ${-ry * 0.1} Q${rx * 0.6} ${-ry * 0.6} 0 ${-ry * 0.6} Q${-rx * 0.6} ${-ry * 0.6} ${-rx - 8} ${-ry * 0.1} Z`} fill={c} {...st} />
          <path d={`M${rx * 0.8} ${-ry * 0.25} Q${rx + 40} ${-ry * 0.05} ${rx + 30} ${ry * 0.35} Q${rx + 6} ${ry * 0.05} ${rx * 0.75} ${-ry * 0.05} Z`} fill={c} {...st} />
          {[-0.45, 0, 0.45].map((k) => <circle key={k} cx={rx * k} cy={-ry * 0.82} r={6} fill={p.papelLuz} />)}
        </g>
      );
    case "gorra":
      return (
        <g>
          <path d={`M${-rx - 4} ${-ry * 0.35} Q${-rx} ${-ry - 34} 0 ${-ry - 36} Q${rx} ${-ry - 34} ${rx + 4} ${-ry * 0.35} Z`} fill={c} {...st} />
          <path d={`M${rx * 0.2} ${-ry * 0.38} Q${rx + 60} ${-ry * 0.42} ${rx + 74} ${-ry * 0.2} Q${rx * 0.6} ${-ry * 0.16} ${rx * 0.2} ${-ry * 0.25} Z`} fill={darker(c, 0.15)} {...st} />
        </g>
      );
    case "casco":
      return (
        <g>
          <path d={`M${-rx - 8} ${-ry * 0.3} Q${-rx - 8} ${-ry - 50} 0 ${-ry - 54} Q${rx + 8} ${-ry - 50} ${rx + 8} ${-ry * 0.3} Z`} fill={c} {...st} />
          <ellipse cx={0} cy={-ry * 0.3} rx={rx + 24} ry={13} fill={c} {...st} />
          <path d={`M${-rx * 0.4} ${-ry - 20} Q${-rx * 0.45} ${-ry * 0.6} ${-rx * 0.2} ${-ry * 0.45}`} stroke={lighter(c, 0.45)} strokeWidth={8} fill="none" strokeLinecap="round" />
        </g>
      );
    default:
      return null;
  }
};

/** Small things a hand can hold (drawn at the hand). */
export const Held: React.FC<{ what: string; x: number; y: number; frame: number }> = ({ what, x, y, frame }) => {
  const p = usePalette();
  const ink = p.tinta;
  const st = { stroke: ink, strokeWidth: LINE - 1, strokeLinejoin: "round" as const };
  switch (what) {
    case "gafas":
      return <g transform={`translate(${x + 6} ${y - 30}) scale(0.9)`}><Glasses w={24} r={20} /></g>;
    case "libro":
      return <g transform={`translate(${x} ${y - 10}) rotate(-8)`}><rect x={-38} y={-52} width={76} height={98} rx={3} fill={p.rojo} {...st} /><rect x={-28} y={-40} width={56} height={10} fill={p.ocre} /></g>;
    case "carta":
      return <g transform={`translate(${x + 4} ${y - 18}) rotate(6)`}><rect x={-42} y={-30} width={84} height={56} fill={p.papelLuz} {...st} /><path d="M-42 -30 L0 2 L42 -30" fill="none" stroke={ink} strokeWidth={4} /></g>;
    case "telefono":
      return <g transform={`translate(${x} ${y - 30})`}><rect x={-24} y={-44} width={48} height={88} rx={8} fill={p.negro} {...st} /><rect x={-17} y={-34} width={34} height={62} rx={3} fill={p.aguaLuz} /></g>;
    case "taza":
      return <g transform={`translate(${x + 4} ${y - 22})`}><path d="M-28 -30 L-24 26 Q0 34 24 26 L28 -30 Z" fill={p.papelLuz} {...st} /><path d="M28 -16 Q48 -12 44 6 Q40 18 26 14" fill="none" stroke={ink} strokeWidth={6} /></g>;
    case "flor":
      return <g transform={`translate(${x} ${y})`}><line x1={0} y1={0} x2={10} y2={-90} stroke={p.verde} strokeWidth={8} /><g transform="translate(10 -100)">{[0, 72, 144, 216, 288].map((a) => <ellipse key={a} cx={0} cy={-18} rx={11} ry={18} transform={`rotate(${a + Math.sin(frame / 9) * 6})`} fill={p.rosa} {...st} />)}<circle r={10} fill={p.ocre} {...st} /></g></g>;
    case "lanza":
      return <g transform={`translate(${x} ${y})`}><line x1={-30} y1={180} x2={40} y2={-380} stroke={ink} strokeWidth={20} strokeLinecap="round" /><line x1={-30} y1={180} x2={40} y2={-380} stroke={p.madera} strokeWidth={9} strokeLinecap="round" /><path d="M28 -372 L48 -450 L62 -370 Z" fill={lighter(p.gris, 0.4)} {...st} /></g>;
    case "saco":
      return <g transform={`translate(${x + 20} ${y - 40})`}><path d="M-50 10 Q-60 -70 0 -76 Q60 -70 50 10 Q0 30 -50 10 Z" fill={p.kraft} {...st} /><path d="M-14 -70 L0 -96 L14 -70" fill="none" stroke={ink} strokeWidth={5} /></g>;
    case "cesta":
      return (
        <g transform={`translate(${x} ${y + 4})`}>
          <path d="M-40 -2 Q0 -86 40 -2" fill="none" stroke={ink} strokeWidth={11} />
          <path d="M-40 -2 Q0 -86 40 -2" fill="none" stroke={p.madera} strokeWidth={5} />
          <path d="M-52 -4 L-42 44 Q0 54 42 44 L52 -4 Z" fill={p.madera} {...st} />
          <path d="M-46 14 L46 14 M-44 30 L44 30" stroke={darker(p.madera, 0.3)} strokeWidth={4} />
          <path d="M-36 -6 Q-10 -26 14 -8 Q32 -22 42 -6 Z" fill={p.papelLuz} {...st} />
        </g>
      );
    case "hacha":
      return (
        <g transform={`translate(${x} ${y}) rotate(-10)`}>
          <line x1={0} y1={70} x2={0} y2={-150} stroke={ink} strokeWidth={20} strokeLinecap="round" />
          <line x1={0} y1={70} x2={0} y2={-150} stroke={p.madera} strokeWidth={9} strokeLinecap="round" />
          <path d="M-4 -150 Q50 -170 60 -120 Q50 -84 -4 -100 Z" fill={lighter(p.gris, 0.35)} {...st} />
        </g>
      );
    case "espada":
      return (
        <g transform={`translate(${x} ${y}) rotate(-15)`}>
          <path d="M-8 -20 L0 -200 L8 -20 Z" fill={lighter(p.gris, 0.5)} {...st} />
          <rect x={-30} y={-24} width={60} height={12} rx={3} fill={p.ocre} {...st} />
          <rect x={-6} y={-12} width={12} height={40} rx={3} fill={p.madera} {...st} />
        </g>
      );
    case "vela":
      return (
        <g transform={`translate(${x} ${y - 20})`}>
          <rect x={-12} y={-60} width={24} height={64} rx={3} fill={p.papelLuz} {...st} />
          <path d={`M0 -64 Q${-10 + Math.sin(frame / 3) * 3} -84 0 -104 Q10 -84 0 -64 Z`} fill={p.sol} {...st} />
          <ellipse cx={0} cy={6} rx={30} ry={8} fill={p.ocre} {...st} />
        </g>
      );
    case "varita":
      return (
        <g transform={`translate(${x} ${y}) rotate(-25)`}>
          <line x1={0} y1={10} x2={0} y2={-110} stroke={ink} strokeWidth={12} strokeLinecap="round" />
          <line x1={0} y1={10} x2={0} y2={-110} stroke={p.negro} strokeWidth={6} strokeLinecap="round" />
          <path transform={`translate(0 -124) rotate(${frame * 4})`} d="M0 -20 L5 -5 L20 0 L5 5 L0 20 L-5 5 L-20 0 L-5 -5 Z" fill={p.sol} {...st} />
        </g>
      );
    case "paraguas":
      return (
        <g transform={`translate(${x} ${y})`}>
          <line x1={0} y1={0} x2={0} y2={-190} stroke={ink} strokeWidth={8} />
          <path d="M-110 -170 Q0 -270 110 -170 Q82 -186 55 -170 Q28 -186 0 -170 Q-28 -186 -55 -170 Q-82 -186 -110 -170 Z" fill={p.rojo} {...st} />
          <path d="M0 0 Q0 18 -16 16" fill="none" stroke={ink} strokeWidth={8} strokeLinecap="round" />
        </g>
      );
    case "bolsa":
      return <g transform={`translate(${x} ${y + 30})`}><path d="M-34 -20 L-40 40 L40 40 L34 -20 Z" fill={p.kraft} {...st} /><path d="M-16 -20 Q0 -46 16 -20" fill="none" stroke={ink} strokeWidth={5} /></g>;
    case "llave":
      return <g transform={`translate(${x + 10} ${y - 10}) rotate(-30)`}><circle cx={0} cy={0} r={16} fill="none" stroke={ink} strokeWidth={9} /><circle cx={0} cy={0} r={16} fill="none" stroke={p.ocre} strokeWidth={4} /><path d="M16 0 L64 0 M50 0 L50 14 M60 0 L60 12" stroke={ink} strokeWidth={8} strokeLinecap="round" /></g>;
    default:
      return null;
  }
};

/** Little gags around a head (any character can use them): flies, hearts, sweat, zzz, a light bulb, anger marks,
 *  a smell, dizzy stars. */
export const Gag: React.FC<{ kind: string; frame: number; rx: number; ry: number }> = ({ kind, frame, rx, ry }) => {
  const p = usePalette();
  const ink = p.tinta;
  switch (kind) {
    case "moscas":
      return (
        <g>
          {[0, 1, 2].map((i) => {
            const a = frame / 6 + i * 2.1;
            const x = rx * 1.3 + Math.cos(a) * 54;
            const y = -ry * 0.9 + Math.sin(a * 1.3) * 36;
            return (
              <g key={i} transform={`translate(${x} ${y})`}>
                <ellipse cx={-5} cy={-7} rx={7} ry={4.5} fill={p.papelLuz} stroke={ink} strokeWidth={2} opacity={0.9} transform={`rotate(${Math.sin(frame * 2 + i) * 25} -5 -7)`} />
                <ellipse cx={5} cy={-7} rx={7} ry={4.5} fill={p.papelLuz} stroke={ink} strokeWidth={2} opacity={0.9} />
                <circle r={5.5} fill={ink} />
              </g>
            );
          })}
        </g>
      );
    case "olor":
      return (
        <g>
          {[0, 1, 2].map((i) => {
            const k = (frame * 2 + i * 30) % 60;
            return <path key={i} d={`M${rx * 0.9 + i * 34} ${-ry * 0.4 - k} q12 -14 0 -28 q-12 -14 0 -28`} stroke={p.verde} strokeWidth={6} fill="none" strokeLinecap="round" opacity={0.9 - k / 70} />;
          })}
        </g>
      );
    case "corazones":
      return (
        <g transform={`translate(${-rx * 0.2} ${-ry - 40})`}>
          {[0, 1, 2].map((i) => {
            const k = (frame * 2 + i * 25) % 75;
            return (
              <path key={i} transform={`translate(${i * 46 - 30} ${-k * 2.4}) scale(${0.8 + i * 0.2})`} opacity={1 - k / 75}
                d="M0 10 C-20 -10 -30 -26 -14 -34 C-4 -38 0 -30 0 -26 C0 -30 4 -38 14 -34 C30 -26 20 -10 0 10 Z" fill={p.rojo} stroke={ink} strokeWidth={4} />
            );
          })}
        </g>
      );
    case "sudor":
      return (
        <g>
          {[0, 1].map((i) => {
            const k = (frame * 1.5 + i * 20) % 40;
            return <path key={i} transform={`translate(${rx * (0.95 - i * 1.9)} ${-ry * 0.5 + k})`} opacity={1 - k / 40} d="M0 -14 Q9 0 0 8 Q-9 0 0 -14 Z" fill={p.aguaLuz} stroke={ink} strokeWidth={3} />;
          })}
        </g>
      );
    case "zzz":
      return (
        <g>
          {[0, 1, 2].map((i) => {
            const k = (frame + i * 15) % 45;
            return <text key={i} x={rx * 0.9 + i * 24 + k * 0.6} y={-ry - k * 1.6} fontFamily="Big Shoulders" fontWeight={900} fontSize={34 + i * 10} fill={ink} opacity={1 - k / 45}>Z</text>;
          })}
        </g>
      );
    case "idea":
      return (
        <g transform={`translate(${rx * 0.7} ${-ry - 70}) scale(${1 + Math.sin(frame / 4) * 0.05})`}>
          {[0, 1, 2, 3, 4].map((i) => <line key={i} x1={0} y1={-46} x2={0} y2={-64} stroke={ink} strokeWidth={5} strokeLinecap="round" transform={`rotate(${-60 + i * 30})`} />)}
          <circle r={30} fill={p.sol} stroke={ink} strokeWidth={5} />
          <rect x={-13} y={26} width={26} height={18} rx={3} fill={p.gris} stroke={ink} strokeWidth={4} />
        </g>
      );
    case "rabia":
      return (
        <g transform={`translate(${rx * 0.75} ${-ry * 0.8}) scale(${1 + Math.abs(Math.sin(frame / 3)) * 0.15})`}>
          {[0, 90, 180, 270].map((a) => <path key={a} d="M6 6 Q14 14 24 8" stroke={p.rojo} strokeWidth={6} fill="none" strokeLinecap="round" transform={`rotate(${a})`} />)}
        </g>
      );
    case "estrellas":
      return (
        <g transform={`translate(0 ${-ry - 20})`}>
          {[0, 1, 2, 3].map((i) => {
            const a = frame / 5 + (i * Math.PI) / 2;
            return <path key={i} transform={`translate(${Math.cos(a) * rx} ${Math.sin(a) * 18})`} d="M0 -14 L4 -4 L14 0 L4 4 L0 14 L-4 4 L-14 0 L-4 -4 Z" fill={p.sol} stroke={ink} strokeWidth={3} />;
          })}
        </g>
      );
    default:
      return null;
  }
};

/** A hood over the head (for capes: Little Red Riding Hood, a monk, a wizard). */
const Hood: React.FC<{ rx: number; ry: number; c: string }> = ({ rx, ry, c }) => {
  const p = usePalette();
  return (
    <path d={`M${-rx - 22} ${ry * 0.6} Q${-rx - 34} ${-ry - 40} 0 ${-ry - 44} Q${rx + 34} ${-ry - 40} ${rx + 22} ${ry * 0.6} Q${rx + 6} ${-ry * 0.2} ${rx - 6} ${-ry * 0.55} Q0 ${-ry - 6} ${-rx + 6} ${-ry * 0.55} Q${-rx - 6} ${-ry * 0.2} ${-rx - 22} ${ry * 0.6} Z`}
      fill={c} stroke={p.tinta} strokeWidth={LINE} strokeLinejoin="round" />
  );
};
