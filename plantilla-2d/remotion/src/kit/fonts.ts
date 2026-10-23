// Las tipografías viajan con la fábrica (src/fonts, SIL OFL 1.1): el montaje funciona sin internet y nunca espera a
// Google. Big Shoulders (rótulos, condensada: cabe mucho y se lee en el teléfono), Big Shoulders Stencil (sellos
// grandes) y Archivo (bocadillos y texto).
import { cancelRender, continueRender, delayRender } from "remotion";
import bsLatin from "../fonts/BigShoulders-var-latin.woff2";
import bsLatinExt from "../fonts/BigShoulders-var-latin-ext.woff2";
import stLatin from "../fonts/BigShouldersStencil-var-latin.woff2";
import stLatinExt from "../fonts/BigShouldersStencil-var-latin-ext.woff2";
import arLatin from "../fonts/Archivo-var-latin.woff2";
import arLatinExt from "../fonts/Archivo-var-latin-ext.woff2";

const LATIN =
  "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD";
const LATIN_EXT =
  "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF";

export const DISPLAY = "Big Shoulders";
export const STENCIL = "Big Shoulders Stencil";
export const TEXT = "Archivo";

const faces = [
  new FontFace(DISPLAY, `url(${bsLatin}) format("woff2")`, { weight: "100 900", unicodeRange: LATIN }),
  new FontFace(DISPLAY, `url(${bsLatinExt}) format("woff2")`, { weight: "100 900", unicodeRange: LATIN_EXT }),
  new FontFace(STENCIL, `url(${stLatin}) format("woff2")`, { weight: "100 900", unicodeRange: LATIN }),
  new FontFace(STENCIL, `url(${stLatinExt}) format("woff2")`, { weight: "100 900", unicodeRange: LATIN_EXT }),
  new FontFace(TEXT, `url(${arLatin}) format("woff2")`, { weight: "100 900", stretch: "62% 125%", unicodeRange: LATIN }),
  new FontFace(TEXT, `url(${arLatinExt}) format("woff2")`, { weight: "100 900", stretch: "62% 125%", unicodeRange: LATIN_EXT }),
];

const handle = delayRender("Cargando las tipografías de la fábrica");
Promise.all(faces.map((face) => face.load().then((c) => document.fonts.add(c))))
  .then(() => continueRender(handle))
  .catch((err) => cancelRender(err));
