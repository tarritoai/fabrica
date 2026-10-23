// Remotion Studio entry (`npm run studio` in remotion/): the generic pieces and your characters. Renders use one
// entry per episode instead (src/generado/<slug>.ts, written by `uv run reels …`).
import { registerRoot } from "remotion";
import { makeRoot } from "./kit/root";

registerRoot(makeRoot());
