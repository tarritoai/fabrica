// Pieces of the example episode «¿Y si Don Quijote llevara gafas?» — what the «dibujante» worker writes for a new
// story: the characters and places the generic pieces do not cover. Sancho, Aldonza and Dulcinea are the generic
// Persona with parameters (see the episode's script.json); here only what is unique to this story.
import React from "react";
import { Sparkles } from "../../kit/effects";
import { Brow, Cheeks, Eye, Hand, Limb, Mouth, blink, breathe, talkMouth, transition } from "../../kit/draw";
import { darker, LINE, lighter, usePalette } from "../../kit/style";
import type { Piece, PieceProps } from "../../kit/types";
import { bool, num, str } from "../../kit/types";
import { Campo } from "../../piezas/fondos";
import { Glasses } from "../../piezas/persona";

// ---------------------------------------------------------------------------------------------- DON QUIJOTE

export const Quijote: Piece = ({ frame, props, prev, since, talk, seed }: PieceProps) => {
  const p = usePalette();
  const ink = p.tinta;
  const skin = p.pieles[0];
  const grey = p.blanco;
  const armor = lighter(p.gris, 0.15);
  const gold = p.ocre;
  const expr = str(props.expresion, "serio");
  const mad = expr === "loco";
  const r = breathe(frame, seed, 3);
  const open = blink(frame, 11, 87);
  const up = expr === "ilusion" || mad ? 0.9 : expr === "decepcion" ? 0.1 : -0.3;
  const tilt = expr === "decepcion" ? 0.9 : expr === "serio" ? -0.5 : 0;
  const lookY = expr === "decepcion" ? 0.6 : 0;
  const gafas = transition(num(prev.gafas, num(props.gafas, 0)), num(props.gafas, 0), since, 10, 0.25);
  const gotGlasses = num(props.gafas, 0) > num(prev.gafas, 0) && since < 16;
  const arm = transition(num(prev.brazo, num(props.brazo, 0)), num(props.brazo, 0), since, 9);
  const handR: [number, number] = [120 + arm * 20, -228 - arm * 150];
  const lanza = bool(props.lanza, true);
  const look = num(props.mira, 0.3);
  const mouthShape = mad ? "grito" : expr === "ilusion" ? "sonrisa" : expr === "decepcion" ? "triste" : "recta";
  return (
    <g>
      {lanza && (
        <g transform={`rotate(${8 - arm * 50} ${handR[0]} ${handR[1]})`}>
          <path d={`M${handR[0] - 20} ${handR[1] + 230} L${handR[0] + 24} ${handR[1] - 420}`} stroke={ink} strokeWidth={22} strokeLinecap="round" />
          <path d={`M${handR[0] - 20} ${handR[1] + 230} L${handR[0] + 24} ${handR[1] - 420}`} stroke={p.madera} strokeWidth={9} strokeLinecap="round" />
          <path d={`M${handR[0] + 10} ${handR[1] - 415} L${handR[0] + 30} ${handR[1] - 490} L${handR[0] + 42} ${handR[1] - 412} Z`} fill={lighter(p.gris, 0.5)} stroke={ink} strokeWidth={LINE - 1} strokeLinejoin="round" />
          <path d={`M${handR[0] + 22} ${handR[1] - 380} L${handR[0] + 72} ${handR[1] - 360 + Math.sin(frame / 4) * 6} L${handR[0] + 20} ${handR[1] - 340} Z`} fill={p.rojo} stroke={ink} strokeWidth={LINE - 2} strokeLinejoin="round" />
        </g>
      )}
      <Limb p={[[-22, -150], [-26, -14]]} color={p.maderaSombra} width={17} curve={false} />
      <Limb p={[[22, -150], [28, -14]]} color={p.maderaSombra} width={17} curve={false} />
      <path d="M-60 -2 Q-58 -32 -24 -28 L-14 -2 Z" fill={p.negro} stroke={ink} strokeWidth={LINE - 1} strokeLinejoin="round" />
      <path d="M60 -2 Q58 -32 24 -28 L14 -2 Z" fill={p.negro} stroke={ink} strokeWidth={LINE - 1} strokeLinejoin="round" />
      <g transform={`translate(0 ${r * 0.4})`}>
        <path d="M-56 -212 L-76 -130 Q0 -114 76 -130 L56 -212 Z" fill={p.rojo} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
        <Limb p={[[-62, -318], [-94, -252], [-80, -196]]} color={armor} />
        <Hand x={-80} y={-192} color={skin} />
        <path d="M-62 -334 Q-74 -258 -58 -200 Q0 -186 58 -200 Q74 -258 62 -334 Q0 -352 -62 -334 Z" fill={armor} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
        <path d="M-36 -322 Q-44 -268 -34 -214" stroke={p.papelLuz} strokeWidth={11} strokeLinecap="round" fill="none" opacity={0.8} />
        <rect x={-60} y={-214} width={120} height={18} rx={3} fill={p.maderaSombra} stroke={ink} strokeWidth={LINE - 2} />
        <rect x={-10} y={-216} width={20} height={22} rx={3} fill={gold} stroke={ink} strokeWidth={3} />
        <circle cx={-64} cy={-322} r={25} fill={armor} stroke={ink} strokeWidth={LINE} />
        <circle cx={64} cy={-322} r={25} fill={armor} stroke={ink} strokeWidth={LINE} />
        <Limb p={[[64, -318], [100 + arm * 10, -270 - arm * 90], handR]} color={armor} />
        <Hand x={handR[0]} y={handR[1]} color={skin} />
        <rect x={-15} y={-378} width={30} height={46} fill={skin} stroke={ink} strokeWidth={LINE - 1} />
        <g transform={`translate(0 ${r * 0.6}) rotate(${mad ? Math.sin(frame / 2) * 2.5 : 0} 0 -440)`}>
          <circle cx={-61} cy={-440} r={15} fill={skin} stroke={ink} strokeWidth={LINE - 1} />
          <circle cx={61} cy={-440} r={15} fill={skin} stroke={ink} strokeWidth={LINE - 1} />
          <path d="M-62 -470 Q-82 -440 -64 -408 L-52 -470 Z" fill={grey} stroke={ink} strokeWidth={LINE - 2} strokeLinejoin="round" />
          <path d="M62 -470 Q82 -440 64 -408 L52 -470 Z" fill={grey} stroke={ink} strokeWidth={LINE - 2} strokeLinejoin="round" />
          <ellipse cx={0} cy={-442} rx={60} ry={84} fill={skin} stroke={ink} strokeWidth={LINE} />
          <Cheeks x={0} y={-410} sep={36} r={11} opacity={0.55} />
          <Eye x={-23} y={-458} r={mad ? 15 : 12} style={mad ? "blanco" : "punto"} scared={mad} mx={look} my={lookY} open={mad ? 1 : expr === "decepcion" ? Math.min(open, 0.6) : open} />
          <Eye x={23} y={-458} r={mad ? 15 : 12} style={mad ? "blanco" : "punto"} scared={mad} mx={look} my={lookY} open={mad ? 1 : expr === "decepcion" ? Math.min(open, 0.6) : open} />
          <Brow x={-25} y={-486} side={-1} up={up} tilt={tilt} length={30} color={grey} width={11} />
          <Brow x={25} y={-486} side={1} up={up} tilt={tilt} length={30} color={grey} width={11} />
          <path d="M-2 -452 Q6 -430 14 -416 Q4 -408 -6 -414" fill={skin} stroke={ink} strokeWidth={LINE - 2} strokeLinecap="round" strokeLinejoin="round" />
          <path d="M-30 -398 Q-26 -350 0 -318 Q26 -350 30 -398 Q0 -386 -30 -398 Z" fill={grey} stroke={ink} strokeWidth={LINE - 1} strokeLinejoin="round" />
          <Mouth x={0} y={-386} open={talkMouth(frame, talk)} width={mad ? 20 : 15} shape={mouthShape} />
          <path d="M0 -404 Q-22 -414 -44 -398 Q-50 -390 -40 -386 Q-24 -400 0 -398 Q24 -400 40 -386 Q50 -390 44 -398 Q22 -414 0 -404 Z" fill={grey} stroke={ink} strokeWidth={LINE - 2} strokeLinejoin="round" />
          {/* the barber's basin (the helmet of Mambrino) */}
          <path d="M-58 -500 Q-58 -572 0 -574 Q58 -572 58 -500 Z" fill={gold} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
          <path d="M-36 -512 Q-36 -556 -6 -562" stroke={lighter(gold, 0.45)} strokeWidth={9} strokeLinecap="round" fill="none" />
          <ellipse cx={0} cy={-500} rx={88} ry={15} fill={gold} stroke={ink} strokeWidth={LINE} />
          <path d="M-18 -487 Q0 -506 18 -487" fill={skin} stroke={ink} strokeWidth={LINE - 2} />
          {gafas > 0.01 && (
            <g transform={`translate(0 ${-458 - (1 - Math.min(1, gafas)) * 220})`} opacity={Math.min(1, gafas * 2)}>
              <Glasses w={27} r={23} />
            </g>
          )}
          {gotGlasses && (
            <g transform={`translate(44 -486) scale(${Math.sin((since / 16) * Math.PI)}) rotate(${since * 6})`}>
              <path d="M0 -40 L8 -8 L40 0 L8 8 L0 40 L-8 8 L-40 0 L-8 -8 Z" fill={p.papelLuz} stroke={ink} strokeWidth={4} strokeLinejoin="round" />
            </g>
          )}
        </g>
      </g>
    </g>
  );
};
Quijote.kind = "actor";
Quijote.about = "Don Quijote (episodio de ejemplo). props: expresion (serio|ilusion|decepcion|loco), gafas (0..1: caen y brillan), brazo (0..1), lanza, mira";
Quijote.head = () => [0, -560];
Quijote.sheet = [
  { label: "serio", props: { expresion: "serio" } },
  { label: "ilusion", props: { expresion: "ilusion", gafas: 1 } },
  { label: "decepcion", props: { expresion: "decepcion", gafas: 1 } },
  { label: "loco", props: { expresion: "loco", lanza: false } },
  { label: "habla", props: { _talk: 1 } },
  { label: "brazo arriba", props: { brazo: 1, expresion: "ilusion" } },
];

// ---------------------------------------------------------------------------------------------- PLACES AND THINGS

/** La Mancha: the generic Campo plus two windmills far away (optional). */
export const LaMancha: Piece = (props: PieceProps) => {
  const far = bool(props.props.molinos, true);
  return (
    <g>
      <Campo {...props} />
      {far && [140, 930].map((x, i) => (
        <g key={x} transform={`translate(${x} ${i ? 930 : 945}) scale(0.3)`}>
          <MillTower />
          <Sails frame={props.frame} speed={0.6 + i * 0.3} />
        </g>
      ))}
    </g>
  );
};
LaMancha.kind = "fondo";
LaMancha.about = "La Mancha: el Campo con dos molinos a lo lejos. opciones: las del Campo + molinos (true|false)";

const MillTower: React.FC = () => {
  const p = usePalette();
  const ink = p.tinta;
  return (
    <g>
      <path d="M-90 0 L-64 -330 L64 -330 L90 0 Z" fill={p.blanco} stroke={ink} strokeWidth={LINE + 2} strokeLinejoin="round" />
      <path d="M-60 -250 Q0 -240 60 -250 M-74 -140 Q0 -130 74 -140" stroke={ink} strokeWidth={4} fill="none" opacity={0.35} />
      <path d="M-26 0 L-26 -70 Q0 -96 26 -70 L26 0 Z" fill={p.maderaSombra} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
      <rect x={-16} y={-230} width={32} height={40} rx={3} fill={p.cifra} stroke={ink} strokeWidth={LINE - 2} />
      <path d="M-84 -326 Q0 -460 84 -326 Z" fill={darker(p.gris, 0.25)} stroke={ink} strokeWidth={LINE + 2} strokeLinejoin="round" />
    </g>
  );
};

const Sails: React.FC<{ frame: number; speed?: number }> = ({ frame, speed = 1 }) => {
  const p = usePalette();
  const ink = p.tinta;
  return (
    <g transform={`translate(0 -360) rotate(${frame * speed * 2.2})`}>
      {[0, 90, 180, 270].map((a) => (
        <g key={a} transform={`rotate(${a})`}>
          <rect x={-8} y={-300} width={16} height={300} fill={p.madera} stroke={ink} strokeWidth={LINE - 1} />
          <rect x={8} y={-290} width={58} height={230} fill={p.papel} stroke={ink} strokeWidth={LINE - 1} />
          {[0, 1, 2, 3].map((k) => <line key={k} x1={8} x2={66} y1={-232 + k * 46} y2={-232 + k * 46} stroke={ink} strokeWidth={4} />)}
          <line x1={37} x2={37} y1={-290} y2={-60} stroke={ink} strokeWidth={4} />
        </g>
      ))}
      <circle r={20} fill={p.madera} stroke={ink} strokeWidth={LINE} />
    </g>
  );
};

export const Molino: Piece = ({ frame }: PieceProps) => (
  <g>
    <MillTower />
    <Sails frame={frame} />
  </g>
);
Molino.kind = "objeto";
Molino.about = "Molino de viento con aspas que giran";

/** What he sees without glasses: a four-armed giant (the arms are the sails). */
export const Gigante: Piece = ({ frame }: PieceProps) => {
  const p = usePalette();
  const ink = p.tinta;
  const body = p.cifra;
  const skin = lighter(p.azul, 0.15);
  const g = Math.sin(frame / 8) * 6;
  return (
    <g>
      <g transform={`translate(0 -360) rotate(${frame * 1.4})`}>
        {[45, 135, 225, 315].map((a) => (
          <g key={a} transform={`rotate(${a})`}>
            <path d="M0 0 Q30 -150 0 -290" stroke={ink} strokeWidth={58} fill="none" strokeLinecap="round" />
            <path d="M0 0 Q30 -150 0 -290" stroke={skin} strokeWidth={42} fill="none" strokeLinecap="round" />
            <circle cx={0} cy={-300} r={32} fill={skin} stroke={ink} strokeWidth={LINE} />
          </g>
        ))}
      </g>
      <path d="M-110 0 Q-130 -200 -90 -330 Q0 -380 90 -330 Q130 -200 110 0 Z" fill={body} stroke={ink} strokeWidth={LINE + 2} strokeLinejoin="round" />
      <g transform={`translate(0 ${g - 470})`}>
        <circle r={110} fill={skin} stroke={ink} strokeWidth={LINE + 2} />
        <path d="M-70 -30 L-20 -10 M70 -30 L20 -10" stroke={ink} strokeWidth={14} strokeLinecap="round" />
        <circle cx={-38} cy={10} r={14} fill={p.sol} stroke={ink} strokeWidth={5} />
        <circle cx={38} cy={10} r={14} fill={p.sol} stroke={ink} strokeWidth={5} />
        <path d="M-56 50 Q0 90 56 50 Z" fill={p.papelLuz} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
        <path d="M-30 52 L-24 70 L-16 56 M16 56 L24 70 L30 52" stroke={ink} strokeWidth={4} fill="none" />
        <path d="M-60 -100 L-40 -150 L-20 -104 M20 -104 L40 -150 L60 -100" fill={body} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
      </g>
    </g>
  );
};
Gigante.kind = "actor";
Gigante.about = "Gigante de cuatro brazos (lo que ve don Quijote en vez del molino)";

export const Castillo: Piece = ({ frame }: PieceProps) => {
  const p = usePalette();
  const ink = p.tinta;
  const wall = lighter(p.rosa, 0.55);
  const roof = darker(p.rosa, 0.25);
  const wave = Math.sin(frame / 4) * 8;
  const tower = (x: number, h: number, w: number) => (
    <g key={x}>
      <rect x={x - w / 2} y={-h} width={w} height={h} fill={wall} stroke={ink} strokeWidth={LINE} />
      <path d={`M${x - w / 2 - 14} ${-h} L${x} ${-h - w * 1.3} L${x + w / 2 + 14} ${-h} Z`} fill={roof} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
      <line x1={x} x2={x} y1={-h - w * 1.3} y2={-h - w * 1.3 - 70} stroke={ink} strokeWidth={6} />
      <path d={`M${x} ${-h - w * 1.3 - 70} Q${x + 30} ${-h - w * 1.3 - 60 + wave} ${x + 60} ${-h - w * 1.3 - 62} L${x} ${-h - w * 1.3 - 36} Z`} fill={p.ocre} stroke={ink} strokeWidth={4} strokeLinejoin="round" />
      <rect x={x - 12} y={-h + 40} width={24} height={44} rx={12} fill={p.cifra} stroke={ink} strokeWidth={4} />
    </g>
  );
  return (
    <g>
      <rect x={-200} y={-300} width={400} height={300} fill={wall} stroke={ink} strokeWidth={LINE} />
      {[-160, -80, 0, 80].map((x) => <rect key={x} x={x + 10} y={-336} width={50} height={40} fill={wall} stroke={ink} strokeWidth={LINE} />)}
      {tower(-200, 470, 110)}
      {tower(200, 470, 110)}
      {tower(0, 600, 130)}
      <path d="M-60 0 L-60 -130 Q0 -200 60 -130 L60 0 Z" fill={p.maderaSombra} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
    </g>
  );
};
Castillo.kind = "objeto";
Castillo.about = "Castillo de cuento con banderas que ondean";

export const Venta: Piece = ({ frame }: PieceProps) => {
  const p = usePalette();
  const ink = p.tinta;
  const swing = Math.sin(frame / 10) * 4;
  const peck = frame % 40 < 6 ? 12 : 0;
  return (
    <g>
      <rect x={-270} y={-250} width={540} height={250} fill={p.blanco} stroke={ink} strokeWidth={LINE} />
      <path d="M-300 -240 L-230 -360 L230 -360 L300 -240 Z" fill={p.rojo} stroke={ink} strokeWidth={LINE} strokeLinejoin="round" />
      {[-180, -90, 0, 90, 180].map((x) => <path key={x} d={`M${x} -360 L${x * 1.2} -244`} stroke={ink} strokeWidth={4} opacity={0.35} />)}
      <rect x={-50} y={-150} width={100} height={150} fill={p.madera} stroke={ink} strokeWidth={LINE} />
      <rect x={-200} y={-180} width={80} height={70} fill={p.azul} stroke={ink} strokeWidth={LINE} />
      <rect x={130} y={-180} width={80} height={70} fill={p.azul} stroke={ink} strokeWidth={LINE} />
      <line x1={70} y1={-230} x2={150} y2={-230} stroke={ink} strokeWidth={8} />
      <g transform={`rotate(${swing} 120 -230)`}>
        <line x1={92} y1={-230} x2={92} y2={-206} stroke={ink} strokeWidth={4} />
        <line x1={148} y1={-230} x2={148} y2={-206} stroke={ink} strokeWidth={4} />
        <rect x={60} y={-206} width={120} height={50} rx={3} fill={p.kraft} stroke={ink} strokeWidth={LINE - 1} />
        <text x={120} y={-170} textAnchor="middle" fontFamily="Big Shoulders" fontWeight={900} fontSize={34} fill={ink}>VENTA</text>
      </g>
      <g transform="translate(330 0)">
        <ellipse cx={0} cy={-40} rx={42} ry={34} fill={p.papelLuz} stroke={ink} strokeWidth={LINE - 1} />
        <g transform={`rotate(${peck} 30 -60)`}>
          <circle cx={34} cy={-74} r={20} fill={p.papelLuz} stroke={ink} strokeWidth={LINE - 1} />
          <path d="M50 -76 L66 -70 L50 -64 Z" fill={p.ocre} stroke={ink} strokeWidth={3} />
          <path d="M28 -94 Q34 -106 40 -92" fill={p.rojo} stroke={ink} strokeWidth={3} />
          <circle cx={40} cy={-78} r={3} fill={ink} />
        </g>
        <path d="M-10 -6 L-10 8 M10 -6 L10 8" stroke={ink} strokeWidth={5} />
      </g>
    </g>
  );
};
Venta.kind = "objeto";
Venta.about = "Venta (posada) con cartel que se balancea y una gallina que picotea";

/** The book: «Don Quijote de la Mancha», crossed out (tachado 0..1) into «Un señor con gafas». */
export const Libro: Piece = ({ props, prev, since }: PieceProps) => {
  const p = usePalette();
  const ink = p.tinta;
  const k = transition(num(prev.tachado, 0), num(props.tachado, 0), since, 20, 0);
  const cover = darker(p.rojo, 0.2);
  const gold = lighter(p.ocre, 0.3);
  return (
    <g transform="translate(0 -230)">
      <rect x={-170} y={-230} width={340} height={460} rx={6} fill={cover} stroke={ink} strokeWidth={LINE + 1} />
      <rect x={-170} y={-230} width={30} height={460} fill={darker(cover, 0.25)} stroke={ink} strokeWidth={LINE - 2} />
      <rect x={-120} y={-190} width={260} height={380} rx={4} fill="none" stroke={gold} strokeWidth={6} />
      <text x={10} y={-90} textAnchor="middle" fontFamily="Big Shoulders" fontWeight={900} fontSize={50} fill={gold}>DON QUIJOTE</text>
      <text x={10} y={-40} textAnchor="middle" fontFamily="Big Shoulders" fontWeight={800} fontSize={38} fill={gold}>DE LA MANCHA</text>
      <text x={10} y={150} textAnchor="middle" fontFamily="Archivo" fontWeight={700} fontSize={26} fill={gold}>M. DE CERVANTES</text>
      {k > 0 && (
        <>
          <path d={`M-110 -78 L${-110 + 240 * Math.min(1, k * 2)} -100`} stroke={p.sello} strokeWidth={14} strokeLinecap="round" />
          <path d={`M-100 -30 L${-100 + 230 * Math.min(1, Math.max(0, k * 2 - 0.5))} -54`} stroke={p.sello} strokeWidth={14} strokeLinecap="round" />
          <g opacity={Math.min(1, Math.max(0, k * 2 - 1))} transform="rotate(-6)">
            <text x={10} y={40} textAnchor="middle" fontFamily="Big Shoulders" fontWeight={900} fontSize={50} fill={p.papelLuz} stroke={ink} strokeWidth={8} paintOrder="stroke">UN SEÑOR</text>
            <text x={10} y={92} textAnchor="middle" fontFamily="Big Shoulders" fontWeight={900} fontSize={50} fill={p.papelLuz} stroke={ink} strokeWidth={8} paintOrder="stroke">CON GAFAS</text>
          </g>
        </>
      )}
    </g>
  );
};
Libro.kind = "objeto";
Libro.about = "El libro de Cervantes; tachado (0..1) lo convierte en «Un señor con gafas»";

/** A sparkly «fantasy» halo (used for Dulcinea): hearts and sparkles. */
export const Fantasia: Piece = ({ frame }: PieceProps) => (
  <g transform="translate(0 -300)">
    <Sparkles frame={frame} n={9} w={420} h={520} />
  </g>
);
Fantasia.kind = "objeto";
Fantasia.about = "Destellos de fantasía alrededor de algo";

