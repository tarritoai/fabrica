// Backgrounds («fondos»): layers of cut paper, each one casting its hard shadow on the one behind. The frame is
// 1080×1920; the ground line is around y = 1180 so characters stand at y ≈ 1400–1450. Options come from the shot's
// "options" in script.json (colours are palette names or #hex).
import React from "react";
import { Halftone } from "../kit/effects";
import { color, darker, LINE, lighter, usePalette } from "../kit/style";
import type { Piece, PieceProps } from "../kit/types";
import { bool, num, str } from "../kit/types";

const sky = (p: ReturnType<typeof usePalette>, hora: string, override?: string) =>
  override ? override : hora === "tarde" ? p.cieloTarde : hora === "noche" ? p.cieloNoche : p.cielo;

const Cloud: React.FC<{ x: number; y: number; s: number }> = ({ x, y, s }) => {
  const p = usePalette();
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} filter="url(#sombra)">
      <path d="M0 40 Q-12 2 36 0 Q54 -38 104 -18 Q140 -42 172 -4 Q222 -6 214 40 Z" fill={p.papelLuz} stroke={p.tinta} strokeWidth={LINE - 1} strokeLinejoin="round" />
    </g>
  );
};

const Stars: React.FC<{ frame: number; n?: number; top?: number; bottom?: number }> = ({ frame, n = 26, top = 140, bottom = 900 }) => {
  const p = usePalette();
  return (
    <g>
      {Array.from({ length: n }, (_, i) => {
        const x = (i * 263) % 1080;
        const y = top + ((i * 397) % (bottom - top));
        const tw = 0.6 + 0.4 * Math.abs(Math.sin(frame / 11 + i));
        return <path key={i} transform={`translate(${x} ${y}) scale(${(0.5 + (i % 3) * 0.25) * tw})`} d="M0 -14 L3 -3 L14 0 L3 3 L0 14 L-3 3 L-14 0 L-3 -3 Z" fill={p.papelLuz} />;
      })}
    </g>
  );
};

/** Open country: sky, sun (or moon), clouds, two hills, ground and a path. */
export const Campo: Piece = ({ frame, props }: PieceProps) => {
  const p = usePalette();
  const hora = str(props.hora, "dia");
  const night = hora === "noche";
  const horizon = num(props.horizonte, 1000);
  const cielo = sky(p, hora, props.cielo as string | undefined);
  const loma = color(p, props.loma as string, night ? darker(p.lomaCerca, 0.55) : p.loma);
  const lomaCerca = color(p, props.loma_cerca as string, night ? darker(p.lomaCerca, 0.45) : p.lomaCerca);
  const suelo = color(p, props.suelo as string, night ? darker(p.suelo, 0.5) : p.suelo);
  const drift = (frame * 0.5) % 1400;
  return (
    <g>
      <rect width={1080} height={1920} fill={cielo} />
      {night ? <Stars frame={frame} /> : null}
      {bool(props.sol, true) && (
        <g filter="url(#sombra)">
          <circle cx={num(props.sol_x, 800)} cy={num(props.sol_y, 560)} r={night ? 80 : 118} fill={night ? p.papelLuz : color(p, props.color_sol as string, p.sol)} stroke={p.tinta} strokeWidth={LINE} />
        </g>
      )}
      {bool(props.nubes, !night) && [[-200 + drift, 420, 1], [520 + drift * 0.7, 300, 0.8], [-900 + drift, 640, 0.7]].map(([x, y, s], i) => (
        <Cloud key={i} x={((x as number) % 1500) - 200} y={y as number} s={s as number} />
      ))}
      <g filter="url(#sombra)">
        <path d={`M-20 ${horizon - 20} Q160 ${horizon - 140} 360 ${horizon - 70} Q560 ${horizon - 150} 760 ${horizon - 80} Q940 ${horizon - 140} 1100 ${horizon - 70} L1100 ${horizon + 300} L-20 ${horizon + 300} Z`}
          fill={loma} stroke={p.tinta} strokeWidth={LINE} strokeLinejoin="round" />
      </g>
      <g filter="url(#sombra)">
        <path d={`M-20 ${horizon + 80} Q280 ${horizon} 560 ${horizon + 60} Q820 ${horizon + 10} 1100 ${horizon + 70} L1100 ${horizon + 400} L-20 ${horizon + 400} Z`}
          fill={lomaCerca} stroke={p.tinta} strokeWidth={LINE} strokeLinejoin="round" />
      </g>
      <g filter="url(#sombra)">
        <rect x={-20} y={horizon + 170} width={1120} height={1920 - horizon} fill={suelo} stroke={p.tinta} strokeWidth={LINE} />
      </g>
      {bool(props.camino, true) && (
        <path d={`M400 ${horizon + 170} Q340 ${horizon + 470} 130 1940 L960 1940 Q720 ${horizon + 470} 610 ${horizon + 170} Z`} fill={lighter(suelo, 0.35)} />
      )}
      {[[90, horizon + 300], [990, horizon + 330], [240, horizon + 560], [880, horizon + 620], [60, horizon + 760]].map(([x, y], i) => (
        <path key={i} d={`M${x - 18} ${y} L${x - 8} ${y - 26} L${x} ${y} L${x + 8} ${y - 30} L${x + 18} ${y}`}
          stroke={p.tinta} strokeWidth={5} fill={night ? darker(p.hierba, 0.4) : p.hierba} strokeLinejoin="round" />
      ))}
    </g>
  );
};
Campo.kind = "fondo";
Campo.about = "Campo abierto: cielo, sol o luna, nubes, dos lomas, suelo y camino. opciones: hora (dia|tarde|noche), cielo, loma, loma_cerca, suelo, sol, nubes, camino, horizonte";

/** Indoors: a wall (plain, stripes, bricks or tiles), skirting, floor, optional window and door and a frame. */
export const Interior: Piece = ({ props }: PieceProps) => {
  const p = usePalette();
  const pared = color(p, props.pared as string, p.pared);
  const raya = color(p, props.raya as string, darker(pared, 0.08));
  const suelo = color(p, props.suelo as string, p.madera);
  const patron = str(props.patron, "rayas");
  const floorY = num(props.suelo_y, 1240);
  const vista = str(props.vista, "dia");
  return (
    <g>
      <rect width={1080} height={1920} fill={pared} />
      {patron === "rayas" && Array.from({ length: 14 }, (_, i) => <rect key={i} x={i * 80} y={0} width={40} height={floorY} fill={raya} />)}
      {patron === "ladrillo" && Array.from({ length: Math.ceil(floorY / 60) }, (_, r) =>
        Array.from({ length: 10 }, (_, c) => (
          <rect key={`${r}-${c}`} x={c * 120 - (r % 2 ? 60 : 0)} y={r * 60} width={114} height={54} rx={2} fill={raya} stroke={darker(pared, 0.25)} strokeWidth={2} />
        )))}
      {patron === "azulejo" && Array.from({ length: Math.ceil(floorY / 90) }, (_, r) =>
        Array.from({ length: 13 }, (_, c) => (
          <rect key={`${r}-${c}`} x={c * 90} y={r * 90} width={90} height={90} fill={(r + c) % 2 ? raya : pared} stroke={darker(pared, 0.12)} strokeWidth={2} />
        )))}
      {bool(props.ventana, true) && (
        <g transform={`translate(${num(props.ventana_x, 700)} 520)`}>
          <g filter="url(#sombra)">
            <rect x={-170} y={-200} width={340} height={400} fill={p.madera} stroke={p.tinta} strokeWidth={LINE} />
          </g>
          <rect x={-146} y={-176} width={292} height={352} fill={vista === "noche" ? p.cieloNoche : vista === "tarde" ? p.cieloTarde : p.cielo} stroke={p.tinta} strokeWidth={LINE - 2} />
          {vista === "noche" ? (
            <circle cx={60} cy={-90} r={36} fill={p.papelLuz} stroke={p.tinta} strokeWidth={4} />
          ) : (
            <circle cx={60} cy={-90} r={44} fill={p.sol} stroke={p.tinta} strokeWidth={4} />
          )}
          <path d="M-146 120 L-90 60 L-40 100 L20 30 L90 90 L146 50 L146 176 L-146 176 Z" fill={vista === "noche" ? darker(p.lomaCerca, 0.5) : p.lomaCerca} />
          <line x1={0} x2={0} y1={-176} y2={176} stroke={p.madera} strokeWidth={14} />
          <line x1={-146} x2={146} y1={0} y2={0} stroke={p.madera} strokeWidth={14} />
        </g>
      )}
      {bool(props.cuadro, false) && (
        <g transform="translate(250 560) rotate(-2)" filter="url(#sombra)">
          <rect x={-110} y={-140} width={220} height={280} fill={p.kraft} stroke={p.tinta} strokeWidth={LINE} />
          <rect x={-86} y={-116} width={172} height={232} fill={color(p, props.color_cuadro as string, p.turquesa)} stroke={p.tinta} strokeWidth={3} />
          <circle cx={0} cy={-20} r={44} fill={p.sol} stroke={p.tinta} strokeWidth={3} />
        </g>
      )}
      {bool(props.puerta, false) && (
        <g transform={`translate(${num(props.puerta_x, 220)} ${floorY})`} filter="url(#sombra)">
          <rect x={-120} y={-560} width={240} height={560} fill={p.madera} stroke={p.tinta} strokeWidth={LINE} />
          <rect x={-90} y={-520} width={180} height={220} fill={darker(p.madera, 0.12)} stroke={p.tinta} strokeWidth={3} />
          <rect x={-90} y={-270} width={180} height={220} fill={darker(p.madera, 0.12)} stroke={p.tinta} strokeWidth={3} />
          <circle cx={84} cy={-280} r={12} fill={p.ocre} stroke={p.tinta} strokeWidth={3} />
        </g>
      )}
      <g filter="url(#sombra)">
        <rect x={-20} y={floorY - 34} width={1120} height={40} fill={darker(pared, 0.25)} stroke={p.tinta} strokeWidth={LINE - 1} />
      </g>
      <rect x={-20} y={floorY} width={1120} height={1940 - floorY} fill={suelo} stroke={p.tinta} strokeWidth={LINE} />
      {Array.from({ length: 6 }, (_, i) => (
        <line key={i} x1={-20} x2={1100} y1={floorY + 60 + i * i * 22} y2={floorY + 60 + i * i * 22} stroke={darker(suelo, 0.18)} strokeWidth={4} />
      ))}
    </g>
  );
};
Interior.kind = "fondo";
Interior.about = "Habitación: pared (patron: rayas|liso|ladrillo|azulejo), zócalo y suelo; ventana (vista dia|tarde|noche), puerta y cuadro opcionales. opciones: pared, raya, suelo, patron, ventana, ventana_x, vista, puerta, puerta_x, cuadro, suelo_y";

/** A city street: skyline with lit windows (night) and a pavement. */
export const Ciudad: Piece = ({ frame, props }: PieceProps) => {
  const p = usePalette();
  const hora = str(props.hora, "dia");
  const night = hora === "noche";
  const cielo = sky(p, hora, props.cielo as string | undefined);
  const base = num(props.horizonte, 1180);
  const tones = night ? [darker(p.azul, 0.5), darker(p.azul, 0.35), darker(p.turquesa, 0.55)] : [p.kraft, lighter(p.naranja, 0.35), lighter(p.turquesa, 0.4), p.paredRaya];
  const blocks = [[-20, 360, 210], [170, 520, 170], [320, 300, 190], [490, 610, 160], [630, 420, 200], [810, 540, 150], [940, 330, 170]];
  return (
    <g>
      <rect width={1080} height={1920} fill={cielo} />
      {night && <Stars frame={frame} n={18} bottom={600} />}
      {night && <circle cx={820} cy={330} r={70} fill={p.papelLuz} stroke={p.tinta} strokeWidth={LINE} />}
      {blocks.map(([x, h, w], i) => (
        <g key={i} filter="url(#sombra)">
          <rect x={x} y={base - h} width={w} height={h + 40} fill={tones[i % tones.length]} stroke={p.tinta} strokeWidth={LINE} />
          {Array.from({ length: Math.floor((h - 60) / 70) }, (_, r) =>
            Array.from({ length: Math.floor((w - 30) / 50) }, (_, c) => {
              const lit = night ? (r * 7 + c * 3 + i) % 3 !== 0 : false;
              return <rect key={`${r}-${c}`} x={x + 22 + c * 50} y={base - h + 34 + r * 70} width={26} height={36}
                fill={lit ? p.sol : night ? darker(p.azul, 0.6) : lighter(p.azul, 0.55)} stroke={p.tinta} strokeWidth={2.5} />;
            }))}
        </g>
      ))}
      <g filter="url(#sombra)">
        <rect x={-20} y={base + 40} width={1120} height={70} fill={p.gris} stroke={p.tinta} strokeWidth={LINE} />
      </g>
      <rect x={-20} y={base + 110} width={1120} height={1920} fill={color(p, props.suelo as string, night ? darker(p.gris, 0.45) : darker(p.gris, 0.15))} stroke={p.tinta} strokeWidth={LINE} />
      {Array.from({ length: 5 }, (_, i) => <rect key={i} x={60 + i * 220} y={base + 420} width={120} height={22} fill={p.papelLuz} opacity={0.8} />)}
    </g>
  );
};
Ciudad.kind = "fondo";
Ciudad.about = "Calle de ciudad: edificios con ventanas (encendidas de noche), acera y asfalto. opciones: hora (dia|tarde|noche), cielo, suelo, horizonte";

/** The sea: sky, horizon and three bands of waves that move. */
export const Mar: Piece = ({ frame, props }: PieceProps) => {
  const p = usePalette();
  const hora = str(props.hora, "dia");
  const cielo = sky(p, hora, props.cielo as string | undefined);
  const horizon = num(props.horizonte, 900);
  const agua = color(p, props.agua as string, p.agua);
  const band = (y: number, c: string, amp: number, speed: number, k: number) => {
    const off = (frame * speed) % 180;
    let d = `M${-200 + off} ${y}`;
    for (let x = -200 + off; x < 1300; x += 90) d += ` q45 ${-amp} 90 0`;
    d += ` L1300 1940 L-200 1940 Z`;
    return <g key={k} filter="url(#sombra)"><path d={d} fill={c} stroke={p.tinta} strokeWidth={LINE - 1} strokeLinejoin="round" /></g>;
  };
  return (
    <g>
      <rect width={1080} height={1920} fill={cielo} />
      {hora === "noche" ? <Stars frame={frame} bottom={horizon - 80} /> : (
        <g filter="url(#sombra)"><circle cx={790} cy={horizon - 220} r={110} fill={p.sol} stroke={p.tinta} strokeWidth={LINE} /></g>
      )}
      {band(horizon, agua, 0, 0, 0)}
      {band(horizon + 260, lighter(agua, 0.12), 26, 1.2, 1)}
      {band(horizon + 560, darker(agua, 0.1), 34, 2, 2)}
      {band(horizon + 860, lighter(agua, 0.2), 30, 3, 3)}
    </g>
  );
};
Mar.kind = "fondo";
Mar.about = "Mar: cielo, sol o estrellas y bandas de olas que se mueven. opciones: hora, cielo, agua, horizonte";

/** Title / close-up background: a flat colour with halftone dots that are bigger towards the edges. */
export const Trama: Piece = ({ frame, props }: PieceProps) => {
  const p = usePalette();
  const fondo = color(p, props.color as string, p.acento);
  const puntos = color(p, props.puntos as string, darker(fondo, 0.18));
  return (
    <g>
      <rect width={1080} height={1920} fill={fondo} />
      <Halftone w={1080} h={1920} cx={num(props.cx, 540)} cy={num(props.cy, 980)} color={puntos} drift={(frame * 0.6) % 46} />
    </g>
  );
};
Trama.kind = "fondo";
Trama.about = "Fondo de título o primer plano: color plano con trama de puntos (más grandes en los bordes). opciones: color, puntos, cx, cy";

/** Just paper (or a flat colour): for objects alone, lists, close-ups of a thing. */
export const Papel: Piece = ({ props }: PieceProps) => {
  const p = usePalette();
  return <rect width={1080} height={1920} fill={color(p, props.color as string, p.papel)} />;
};
Papel.kind = "fondo";
Papel.about = "Papel liso (o un color): para objetos solos o primeros planos. opciones: color";

/** Night sky over a dark hill: stars and a moon. */
export const Noche: Piece = ({ frame, props }: PieceProps) => {
  const p = usePalette();
  return (
    <g>
      <rect width={1080} height={1920} fill={color(p, props.cielo as string, p.cieloNoche)} />
      <Stars frame={frame} n={40} bottom={1100} />
      <g filter="url(#sombra)"><circle cx={760} cy={480} r={96} fill={p.papelLuz} stroke={p.tinta} strokeWidth={LINE} /></g>
      <circle cx={730} cy={460} r={18} fill={p.papel} />
      <circle cx={790} cy={520} r={12} fill={p.papel} />
      <g filter="url(#sombra)">
        <path d="M-20 1180 Q300 1060 600 1150 Q860 1090 1100 1160 L1100 1940 L-20 1940 Z" fill={color(p, props.suelo as string, darker(p.lomaCerca, 0.55))} stroke={p.tinta} strokeWidth={LINE} />
      </g>
    </g>
  );
};
Noche.kind = "fondo";
Noche.about = "Noche: cielo oscuro con estrellas, luna y una loma. opciones: cielo, suelo";

const Pine: React.FC<{ x: number; y: number; s: number; c: string }> = ({ x, y, s, c }) => {
  const p = usePalette();
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} filter="url(#sombra)">
      <rect x={-12} y={-40} width={24} height={60} fill={p.maderaSombra} stroke={p.tinta} strokeWidth={LINE} />
      <path d="M0 -330 L-110 -40 L110 -40 Z M0 -250 L-90 -130 L90 -130 Z" fill={c} stroke={p.tinta} strokeWidth={LINE} strokeLinejoin="round" />
      <path d="M0 -330 L-110 -40 L110 -40 Z" fill={c} stroke={p.tinta} strokeWidth={LINE} strokeLinejoin="round" />
      <path d="M0 -330 L-80 -150 L80 -150 Z" fill={lighter(c, 0.12)} stroke={p.tinta} strokeWidth={LINE - 1} strokeLinejoin="round" />
    </g>
  );
};

/** A forest: the Campo, greener, with a row of pines far away and two big ones on the sides. */
export const Bosque: Piece = (pp: PieceProps) => {
  const p = usePalette();
  const night = str(pp.props.hora, "dia") === "noche";
  const pine = color(p, pp.props.pinos as string, night ? darker(p.verde, 0.45) : p.verde);
  const horizon = num(pp.props.horizonte, 1000);
  return (
    <g>
      <Campo {...pp} props={{ loma: night ? undefined : "#A9C285", loma_cerca: night ? undefined : "#8FAE6E", suelo: night ? undefined : "#C9D79A", sol: !night, ...pp.props }} />
      {[60, 190, 330, 760, 900, 1020].map((x, i) => <Pine key={x} x={x} y={horizon + 150 + (i % 2) * 20} s={0.55 + (i % 3) * 0.08} c={darker(pine, 0.08)} />)}
      {bool(pp.props.arboles, true) && (
        <>
          <Pine x={30} y={1720} s={1.5} c={pine} />
          <Pine x={1060} y={1760} s={1.6} c={pine} />
        </>
      )}
    </g>
  );
};
Bosque.kind = "fondo";
Bosque.about = "Bosque: el Campo más verde con pinos lejos y dos grandes a los lados. opciones: las del Campo + pinos (color), arboles (true|false)";
