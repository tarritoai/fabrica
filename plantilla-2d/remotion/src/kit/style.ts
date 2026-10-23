// El estilo de la casa: «papel recortado». Color plano, línea de tinta fina y una SOMBRA DURA (sin difuminar) bajo
// cada pieza, como recortes de papel pegados sobre una hoja. Todo SVG, todo por código.
// Las paletas son datos: el guion elige una ("palette") y cada pieza pide sus colores con usePalette().
import { createContext, useContext } from "react";

export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;
export const LINE = 6; // grosor de la línea de tinta a escala 1
export const SHADOW: [number, number] = [10, 10]; // desplazamiento de la sombra dura

export type Palette = {
  nombre: string;
  tinta: string; // línea y texto
  sombra: string; // color de la sombra dura (se pinta con opacidad)
  sombraOpacidad: number;
  papel: string; // rótulos y fondo de tarjetas
  papelLuz: string;
  kraft: string; // etiquetas
  kraftSombra: string;
  acento: string; // palabras destacadas, un solo acento
  sello: string; // tinta de los sellos
  cifra: string; // placa del contador
  cifraTexto: string;
  cielo: string;
  cieloTarde: string;
  cieloNoche: string;
  sol: string;
  loma: string;
  lomaCerca: string;
  suelo: string;
  sueloSombra: string;
  camino: string;
  hierba: string;
  pared: string;
  paredRaya: string;
  madera: string;
  maderaSombra: string;
  agua: string;
  aguaLuz: string;
  // ropa y objetos: una gama corta que combina
  rojo: string;
  naranja: string;
  ocre: string;
  verde: string;
  azul: string;
  turquesa: string;
  rosa: string;
  gris: string;
  blanco: string;
  negro: string;
  pieles: string[];
  mejilla: string;
  pelos: string[];
};

export const PALETTES: Record<string, Palette> = {
  // Barro, esmalte y papel: la de la casa.
  alfar: {
    nombre: "alfar",
    tinta: "#1E1712",
    sombra: "#1E1712",
    sombraOpacidad: 0.3,
    papel: "#F2E7D5",
    papelLuz: "#FBF4E8",
    kraft: "#D9C3A0",
    kraftSombra: "#B89C74",
    acento: "#E8572A",
    sello: "#C92A23",
    cifra: "#17213D",
    cifraTexto: "#F2E7D5",
    cielo: "#BFE0D6",
    cieloTarde: "#F4C9A0",
    cieloNoche: "#17213D",
    sol: "#F6C25B",
    loma: "#D9B57A",
    lomaCerca: "#C99A55",
    suelo: "#E8C98E",
    sueloSombra: "#D4AE6C",
    camino: "#F3DDB0",
    hierba: "#8FA65A",
    pared: "#E9D9BD",
    paredRaya: "#DCC7A3",
    madera: "#A86B3C",
    maderaSombra: "#7C4A26",
    agua: "#2F6F86",
    aguaLuz: "#5FA3B3",
    rojo: "#C8402A",
    naranja: "#E0743F",
    ocre: "#D9A441",
    verde: "#5E8F5A",
    azul: "#3C5F94",
    turquesa: "#1F9E9A",
    rosa: "#E59AA8",
    gris: "#9AA0A6",
    blanco: "#FBF4E8",
    negro: "#2B2420",
    pieles: ["#F5CFAE", "#EBB58C", "#C98B60", "#9A6440", "#6E452B"],
    mejilla: "#E9857A",
    pelos: ["#2B2420", "#5B3A26", "#9A6234", "#D9A441", "#E8E2D6", "#B8452C"],
  },
  // Más contraste y más frío: noche azul tinta, papel y un naranja de horno.
  tinta: {
    nombre: "tinta",
    tinta: "#141824",
    sombra: "#0B1224",
    sombraOpacidad: 0.35,
    papel: "#EFEBE3",
    papelLuz: "#FAF8F3",
    kraft: "#CDBB9B",
    kraftSombra: "#A99673",
    acento: "#FF8A3D",
    sello: "#D12F28",
    cifra: "#141824",
    cifraTexto: "#FF8A3D",
    cielo: "#A9C9DE",
    cieloTarde: "#E9B8A0",
    cieloNoche: "#0B1224",
    sol: "#FFD36B",
    loma: "#8FA3B8",
    lomaCerca: "#6F86A0",
    suelo: "#C9C2B2",
    sueloSombra: "#B0A893",
    camino: "#E1DACB",
    hierba: "#6E8F6A",
    pared: "#DCE3EA",
    paredRaya: "#C8D2DC",
    madera: "#8C5A3A",
    maderaSombra: "#633C24",
    agua: "#22406B",
    aguaLuz: "#4F79A6",
    rojo: "#D04A3A",
    naranja: "#FF8A3D",
    ocre: "#D9A441",
    verde: "#4F8A6E",
    azul: "#2F4F8C",
    turquesa: "#2A9D9A",
    rosa: "#E08FA0",
    gris: "#8E96A3",
    blanco: "#FAF8F3",
    negro: "#1D2230",
    pieles: ["#F3D2B6", "#E3B08C", "#C38A62", "#8F5E3E", "#5E3B26"],
    mejilla: "#E58A82",
    pelos: ["#1D2230", "#4E3426", "#8A5A34", "#D9A441", "#E6E6E6", "#A9452E"],
  },
};

export const PaletteContext = createContext<Palette>(PALETTES.alfar);
export const usePalette = () => useContext(PaletteContext);
export const palette = (name?: string): Palette => PALETTES[name ?? "alfar"] ?? PALETTES.alfar;

/** Un color del guion: un nombre de la paleta ("rojo", "pieles.2", "pelos.0") o un #hex tal cual. */
export const color = (p: Palette, value: string | undefined, fallback: string): string => {
  if (!value) return fallback;
  if (value.startsWith("#")) return value;
  const [k, i] = value.split(".");
  const v = (p as unknown as Record<string, unknown>)[k];
  if (Array.isArray(v)) return (v[Number(i) || 0] as string) ?? fallback;
  return typeof v === "string" ? v : fallback;
};

/** Mezcla dos colores #rrggbb (t = 0 → a, 1 → b). Para sombras y luces de un color sin inventar otro. */
export const mix = (a: string, b: string, t: number): string => {
  const pa = parseInt(a.slice(1, 7), 16);
  const pb = parseInt(b.slice(1, 7), 16);
  const ch = (x: number, s: number) => (x >> s) & 255;
  const m = (s: number) => Math.max(0, Math.min(255, Math.round(ch(pa, s) + (ch(pb, s) - ch(pa, s)) * t)));
  return "#" + [m(16), m(8), m(0)].map((v) => v.toString(16).padStart(2, "0")).join("");
};
export const darker = (c: string, t = 0.22) => mix(c, "#1E1712", t);
export const lighter = (c: string, t = 0.3) => mix(c, "#FFFFFF", t);
