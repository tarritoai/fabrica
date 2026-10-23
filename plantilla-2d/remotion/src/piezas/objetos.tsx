// Things that are not people: a cottage seen from outside and a giant phone with screens (maps, chats,
// notifications, calls): modern «¿Y si…?» stories ask for them all the time. Origin = the bottom centre.
import React from "react";
import { transition } from "../kit/draw";
import { DISPLAY, TEXT } from "../kit/fonts";
import { color, darker, LINE, lighter, usePalette } from "../kit/style";
import type { Piece, PieceProps } from "../kit/types";
import { bool, num, str } from "../kit/types";

/** A cottage from outside: walls, roof, door, two windows, chimney with smoke. ~560 px tall. */
export const Casa: Piece = ({ frame, props }: PieceProps) => {
  const p = usePalette();
  const ink = p.tinta;
  const st = { stroke: ink, strokeWidth: LINE, strokeLinejoin: "round" as const };
  const pared = color(p, props.pared as string, p.blanco);
  const tejado = color(p, props.tejado as string, p.rojo);
  const night = bool(props.luz, false);
  const win = night ? p.sol : lighter(p.azul, 0.45);
  return (
    <g>
      <rect x={70} y={-520} width={60} height={140} fill={darker(pared, 0.15)} {...st} />
      {bool(props.humo, true) && [0, 1, 2].map((i) => {
        const k = (frame * 1.2 + i * 30) % 90;
        return <circle key={i} cx={100 + Math.sin((frame + i * 20) / 10) * 12} cy={-540 - k * 2.2} r={18 + k * 0.25} fill={p.papelLuz} stroke={ink} strokeWidth={3} opacity={1 - k / 90} />;
      })}
      <rect x={-240} y={-300} width={480} height={300} fill={pared} {...st} />
      <path d="M-280 -290 L0 -500 L280 -290 Z" fill={tejado} {...st} />
      {[-180, -90, 0, 90, 180].map((x) => <path key={x} d={`M${x * 0.9} ${-480 + Math.abs(x) * 0.7} L${x * 1.25} -296`} stroke={darker(tejado, 0.25)} strokeWidth={4} />)}
      <rect x={-50} y={-170} width={100} height={170} rx={4} fill={p.madera} {...st} />
      <circle cx={30} cy={-80} r={8} fill={p.ocre} stroke={ink} strokeWidth={3} />
      {[-160, 110].map((x) => (
        <g key={x}>
          <rect x={x} y={-230} width={70} height={70} fill={win} {...st} />
          <path d={`M${x + 35} -230 L${x + 35} -160 M${x} -195 L${x + 70} -195`} stroke={ink} strokeWidth={4} />
        </g>
      ))}
      {str(props.cartel, "") && (
        <g transform="translate(0 -320)">
          <rect x={-110} y={-28} width={220} height={56} rx={3} fill={p.kraft} {...st} />
          <text x={0} y={14} textAnchor="middle" fontFamily={DISPLAY} fontWeight={900} fontSize={38} fill={ink}>{str(props.cartel, "")}</text>
        </g>
      )}
    </g>
  );
};
Casa.kind = "objeto";
Casa.about = "Casita vista desde fuera, con chimenea que echa humo. props: pared, tejado, luz (ventanas encendidas), humo, cartel (texto)";

type Msg = { de?: string; texto: string };

/** A giant phone (~780 px tall) with a screen: map with a route that draws itself (and pins), chat, notification,
 *  incoming call or big text. Every «act» that changes «pantalla» or «ruta» restarts its animation. */
export const Telefono: Piece = ({ frame, props, prev, since }: PieceProps) => {
  const p = usePalette();
  const ink = p.tinta;
  const W = 400;
  const H = 780;
  const sw = W - 50;
  const sh = H - 120;
  const pantalla = str(props.pantalla, "mapa");
  const titulo = str(props.titulo, "");
  const k = Math.min(1, since / 24);
  const ruta = transition(num(prev.ruta, num(props.ruta, 1)), num(props.ruta, 1), since, 24, 0);
  const screen = () => {
    switch (pantalla) {
      case "chat": {
        const msgs = (Array.isArray(props.mensajes) ? props.mensajes : []) as Msg[];
        const shown = Math.max(1, Math.min(msgs.length, Math.floor(since / 12) + 1));
        return (
          <g>
            <rect width={sw} height={70} fill={p.turquesa} />
            <text x={20} y={46} fontFamily={DISPLAY} fontWeight={900} fontSize={34} fill={p.papelLuz}>{titulo || "CHAT"}</text>
            {msgs.slice(0, shown).map((m, i) => {
              const mine = m.de === "yo";
              const lines = wrapWords(m.texto, 17).slice(0, 3);
              const bw = 250;
              const x = mine ? sw - bw - 16 : 16;
              const y = 100 + msgs.slice(0, i).reduce((a, mm) => a + 50 + wrapWords(mm.texto, 17).slice(0, 3).length * 34, 0);
              return (
                <g key={i}>
                  <rect x={x} y={y} width={bw} height={30 + lines.length * 34} rx={14} fill={mine ? lighter(p.turquesa, 0.5) : p.papelLuz} stroke={ink} strokeWidth={3} />
                  {lines.map((l, j) => <text key={j} x={x + 16} y={y + 40 + j * 34} fontFamily={TEXT} fontWeight={700} fontSize={26} fill={ink}>{l}</text>)}
                </g>
              );
            })}
          </g>
        );
      }
      case "notificacion":
        return (
          <g>
            <rect width={sw} height={sh} fill={darker(p.azul, 0.3)} />
            <text x={sw / 2} y={150} textAnchor="middle" fontFamily={DISPLAY} fontWeight={800} fontSize={110} fill={p.papelLuz}>{str(props.hora, "03:12")}</text>
            <g transform={`translate(20 ${260 - (1 - k) * 40})`} opacity={k}>
              <rect width={sw - 40} height={150} rx={18} fill={p.papelLuz} stroke={ink} strokeWidth={3} />
              <text x={20} y={46} fontFamily={DISPLAY} fontWeight={900} fontSize={30} fill={ink}>{titulo || "AVISO"}</text>
              {wrapWords(str(props.texto, ""), 20).slice(0, 2).map((l, j) => (
                <text key={j} x={20} y={90 + j * 34} fontFamily={TEXT} fontWeight={600} fontSize={26} fill={ink}>{l}</text>
              ))}
            </g>
          </g>
        );
      case "llamada": {
        const pulse = 1 + Math.abs(Math.sin(frame / 6)) * 0.08;
        return (
          <g>
            <rect width={sw} height={sh} fill={darker(p.verde, 0.35)} />
            <circle cx={sw / 2} cy={220} r={80} fill={p.kraft} stroke={ink} strokeWidth={4} />
            <text x={sw / 2} y={250} textAnchor="middle" fontFamily={DISPLAY} fontWeight={900} fontSize={80} fill={ink}>{str(props.contacto, "?").slice(0, 1).toUpperCase()}</text>
            <text x={sw / 2} y={360} textAnchor="middle" fontFamily={DISPLAY} fontWeight={900} fontSize={48} fill={p.papelLuz}>{str(props.contacto, "LLAMADA").toUpperCase()}</text>
            <text x={sw / 2} y={404} textAnchor="middle" fontFamily={TEXT} fontWeight={600} fontSize={26} fill={p.papelLuz}>llamando…</text>
            <g transform={`translate(${sw / 2 - 90} 540) scale(${pulse})`}><circle r={44} fill={p.rojo} stroke={ink} strokeWidth={4} /></g>
            <g transform={`translate(${sw / 2 + 90} 540) scale(${pulse})`}><circle r={44} fill={p.verde} stroke={ink} strokeWidth={4} /></g>
          </g>
        );
      }
      case "texto":
        return (
          <g>
            <rect width={sw} height={sh} fill={color(p, props.fondo as string, p.papelLuz)} />
            {str(props.texto, "").split("\n").map((l, i) => (
              <text key={i} x={sw / 2} y={sh / 2 - 40 + i * 80} textAnchor="middle" fontFamily={DISPLAY} fontWeight={900} fontSize={70} fill={ink}>{l}</text>
            ))}
          </g>
        );
      default: {
        // the map: blocks of green, a road, a route that draws itself from A to B, pins
        const path = "M60 600 L60 470 L200 470 L200 300 L300 300 L300 140";
        const len = 130 + 140 + 170 + 100 + 160;
        return (
          <g>
            <rect width={sw} height={sh} fill="#E8EEDC" />
            {[[30, 40, 110, 80], [180, 60, 120, 70], [40, 200, 120, 120], [230, 380, 100, 60], [100, 540, 90, 70]].map(([x, y, w, h], i) => (
              <rect key={i} x={x} y={y} width={w} height={h} rx={10} fill="#BFD8A6" />
            ))}
            <path d="M0 470 L350 470 M200 0 L200 660 M0 300 L350 300" stroke={p.papelLuz} strokeWidth={26} />
            <path d={path} fill="none" stroke={p.azul} strokeWidth={14} strokeLinecap="round" strokeLinejoin="round"
              strokeDasharray={len} strokeDashoffset={len * (1 - ruta)} />
            <Pin x={60} y={600} c={p.azul} />
            <Pin x={300} y={140} c={p.rojo} />
            {titulo && (
              <g>
                <rect x={0} y={0} width={sw} height={64} fill={p.rojo} />
                <text x={sw / 2} y={44} textAnchor="middle" fontFamily={DISPLAY} fontWeight={900} fontSize={34} fill={p.papelLuz}>{titulo}</text>
              </g>
            )}
            {str(props.minutos, "") && (
              <g transform={`translate(${sw - 130} ${sh - 70})`}>
                <rect width={110} height={50} rx={25} fill={p.papelLuz} stroke={ink} strokeWidth={3} />
                <text x={55} y={35} textAnchor="middle" fontFamily={DISPLAY} fontWeight={900} fontSize={28} fill={ink}>{str(props.minutos, "")}</text>
              </g>
            )}
          </g>
        );
      }
    }
  };
  return (
    <g transform={`translate(${-W / 2} ${-H})`}>
      <rect width={W} height={H} rx={48} fill={p.negro} stroke={ink} strokeWidth={LINE + 1} />
      <rect x={W / 2 - 50} y={22} width={100} height={20} rx={10} fill={darker(p.negro, 0.4)} />
      <svg x={25} y={60} width={sw} height={sh} viewBox={`0 0 ${sw} ${sh}`} overflow="hidden">
        {screen()}
      </svg>
      <rect x={25} y={60} width={sw} height={sh} rx={6} fill="none" stroke={ink} strokeWidth={4} />
    </g>
  );
};
Telefono.kind = "objeto";
Telefono.about = "Teléfono gigante (~780 px) con pantalla: pantalla (mapa|chat|notificacion|llamada|texto), titulo; mapa: ruta (0..1, se dibuja al cambiar), minutos; chat: mensajes [{de: yo|otro, texto}] (van saliendo); notificacion: hora, texto; llamada: contacto; texto: texto (\\n para otra línea), fondo";
Telefono.head = () => [0, -800];
Telefono.sheet = [
  { label: "mapa", props: { pantalla: "mapa", titulo: "RECALCULANDO…", minutos: "12 MIN" } },
  { label: "chat", props: { pantalla: "chat", titulo: "ABUELA", mensajes: [{ de: "otro", texto: "¿Vienes?" }, { de: "yo", texto: "En 12 minutos, abuela" }] } },
  { label: "notificacion", props: { pantalla: "notificacion", titulo: "LOBO", texto: "¿Me pasas tu ubicación?" } },
  { label: "llamada", props: { pantalla: "llamada", contacto: "Mamá" } },
  { label: "texto", props: { pantalla: "texto", texto: "SIN\nCOBERTURA" } },
];

const Pin: React.FC<{ x: number; y: number; c: string }> = ({ x, y, c }) => {
  const p = usePalette();
  return (
    <g transform={`translate(${x} ${y})`}>
      <path d="M0 0 C-30 -30 -30 -70 0 -70 C30 -70 30 -30 0 0 Z" fill={c} stroke={p.tinta} strokeWidth={4} />
      <circle cx={0} cy={-46} r={10} fill={p.papelLuz} />
    </g>
  );
};

/** Words into lines of at most `n` characters (a word longer than that gets its own line). */
const wrapWords = (text: string, n: number): string[] => {
  const out: string[] = [];
  let cur = "";
  for (const w of text.split(/\s+/).filter(Boolean)) {
    if (cur && (cur + " " + w).length > n) {
      out.push(cur);
      cur = w;
    } else cur = cur ? `${cur} ${w}` : w;
  }
  if (cur) out.push(cur);
  return out;
};
