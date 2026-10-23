"""The contract of the 2D factory: episodes/<slug>/script.json.

A reel is a list of beats (one line each, said by one voice). A beat may start a new SHOT (a background + actors);
EVENTS hang from the words of its line ("the stamp lands on «molino»"), so everything moves with the voice. Times are
never written by hand: they come out of the voice (reels/timeline.py). Closed vocabularies (event types, pieces,
expressions) are checked here and by `reels lint`; the pieces themselves live in remotion/src/ (docs/piezas.md).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_WORDS_PER_LINE = 22
EVENT_TYPES = ("act", "cue", "reveal", "enter", "exit", "move", "stamp", "count", "count_break", "label", "shake",
               "flash", "sfx", "question", "sparkle")
ANCHOR = re.compile(r"^(inicio|fin|[^\s#]+(#\d+)?)$")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Voice(Strict):
    voice_id: str = Field(description="ElevenLabs voice id.")
    name: str = Field("", description="Its name in the library (only to recognise it).")
    stability: float = Field(0.5, ge=0, le=1, description="0 = creative (strong emotions), 0.5 = natural, 1 = robust.")
    similarity_boost: float = Field(0.75, ge=0, le=1)
    style: float = Field(0.2, ge=0, le=1)


class Pace(Strict):
    max_pause: float = Field(0.18, ge=0.05, le=1.0, description="Pauses inside a take longer than this are shortened to it.")
    tempo: float = Field(1.1, ge=1.0, le=1.3, description="Speed-up without changing the pitch (the «¿Y si…?» rhythm).")
    gap: float = Field(0.28, ge=0.0, le=1.5, description="Silence between two voices.")
    lead: float = Field(0.15, ge=0.0, le=1.0, description="Seconds before the first word.")
    hook_alone: bool = Field(True, description="The hook (beat 1) is its own take: a B hook or another reading of it "
                                               "never pays the rest of the narrator again.")


class Counter(Strict):
    label: str = Field(description="What is counted, in capitals, short: «LOCURAS EVITADAS».")
    kind: Literal["rodillo", "barra"] = "rodillo"
    start: int = 0
    max: int = Field(6, ge=1, le=12, description="barra: number of squares.")
    from_beat: int = Field(2, description="It appears when this beat starts.")
    suffix: str = ""


class TitleCard(Strict):
    lines: list[str] = Field(description="1–3 short lines, the question of the reel.")
    highlight: list[str] = Field(default_factory=list)
    until: str = Field("fin", description="Word of beat 1 where the card leaves (or «fin»).")


class Music(Strict):
    track: str = Field(description="A file of assets/music/music.json (e.g. clips/quijote-guitarra.mp3).")
    volume: float = Field(0.18, ge=0, le=1)
    loop: bool = Field(True, description="If the reel is longer than the track, it starts again (never silence).")


class Camera(Strict):
    zoom: float = Field(0.04, ge=-0.3, le=0.6, description="Slow push-in over the shot (0.04 = 4 %).")
    focus: tuple[float, float] = (540, 1000)
    punch: bool = Field(True, description="A small punch-in on the cut.")
    pan: tuple[float, float] = (0, 0)


class Actor(Strict):
    id: str = Field(description="Name of this actor inside the shot (events refer to it).")
    piece: str = Field(description="Piece that draws it: Persona, Cosa, Objeto or a piece of yours (docs/piezas.md).")
    x: float = 540
    y: float = 1420
    scale: float = Field(1.0, gt=0, le=6)
    rot: float = Field(0.0, ge=-180, le=180, description="Tilt in degrees (e.g. 12 when charging).")
    props: dict = Field(default_factory=dict, description="The piece's own props (expresion, pose, ropa…).")
    voice: str | None = Field(None, description="Key of `voices` whose words move its mouth.")
    z: int = 0
    flip: bool = False
    hidden: bool = Field(False, description="Starts hidden: an «enter» event brings it in.")
    shadow: bool = True


class Shot(Strict):
    scene: str = Field(description="Background piece: Campo, Interior, Ciudad, Mar, Trama, Papel, Noche or yours.")
    options: dict = Field(default_factory=dict)
    camera: Camera = Field(default_factory=Camera)
    actors: list[Actor] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> "Shot":
        ids = [a.id for a in self.actors]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"actores repetidos en el plano: {', '.join(sorted(dup))}")
        return self


class Event(Strict):
    type: Literal[EVENT_TYPES]  # type: ignore[valid-type]
    at: str = Field("inicio", description="Word of the beat's line where it happens («molino», «molino#2»), «inicio» or «fin».")
    delay: float = Field(0.0, ge=-2, le=5, description="Seconds after the word (negative = before).")
    actor: str | None = None
    props: dict | None = None
    name: str | None = Field(None, description="cue: the name of the moment.")
    piece: str | None = Field(None, description="reveal: the piece it turns into.")
    scale: float | None = None
    from_: Literal["left", "right", "top", "bottom", "pop"] | None = Field(None, alias="from")
    to: str | None = Field(None, description="exit: left | right | top | bottom | pop.")
    x: float | None = None
    y: float | None = None
    seconds: float | None = Field(None, description="move: how long it takes.")
    text: str | None = None
    rot: float | None = None
    size: float | None = None
    color: str | None = None
    until: str | None = Field(None, description="stamp/label: «plano» (default), «beat», «final» or a word of this beat.")
    value: int | None = None
    strength: float | None = None
    sound: str | None = Field(None, description="sfx: a file of assets/sfx without .wav.")
    volume: float | None = None

    @field_validator("at")
    @classmethod
    def _anchor(cls, v: str) -> str:
        if not ANCHOR.match(v.strip()):
            raise ValueError(f"«{v}» no es un ancla: una palabra de la frase («molino», «molino#2»), «inicio» o «fin»")
        return v.strip()

    @model_validator(mode="after")
    def _needs(self) -> "Event":
        need = {"act": ["actor", "props"], "cue": ["actor", "name"], "reveal": ["actor", "piece"], "enter": ["actor"],
                "exit": ["actor"], "move": ["actor"], "stamp": ["text"], "count": ["value"], "label": ["text"],
                "question": ["text"], "sfx": ["sound"]}.get(self.type, [])
        missing = [k for k in need if getattr(self, k) in (None, "")]
        if missing:
            raise ValueError(f"el evento «{self.type}» necesita: {', '.join(missing)}")
        return self


class Bubble(Strict):
    actor: str | None = Field(None, description="Who says it: the bubble points at its head.")
    x: float | None = None
    y: float | None = None
    shout: bool = Field(False, description="A shout: big capitals on the accent colour.")
    width: int = Field(560, ge=240, le=960)


class Beat(Strict):
    id: int
    voice: str = Field(description="Key of `voices`.")
    line: str = Field(description="What is said and shown (numbers in digits are spelled out for the voice).")
    tags: list[str] = Field(default_factory=list, description="ElevenLabs v4 tags for this line ([rushed], [whispers]…).")
    highlight: list[str] = Field(default_factory=list, description="Words shown in the accent colour.")
    shot: Shot | None = Field(None, description="A new shot starts with this beat (null = the previous one goes on).")
    events: list[Event] = Field(default_factory=list)
    bubble: Bubble | None = Field(None, description="Said in a speech bubble instead of captions.")
    captions: bool = True
    take: int = Field(1, ge=1, le=9, description="Another take of the voice (seed) for this line's take.")
    pause_before: float | None = Field(None, ge=0, le=2, description="Silence before this line if it is a new take.")
    performance: str | None = Field(None, description="Your own acting in the character's voice (reels voice-act): used instead of reading the line.")

    @field_validator("line")
    @classmethod
    def _line(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("la frase está vacía")
        if len(v.split()) > MAX_WORDS_PER_LINE:
            raise ValueError(f"frase de {len(v.split())} palabras: parte el beat (máximo {MAX_WORDS_PER_LINE})")
        return v


class Ending(Strict):
    seconds: float = Field(1.6, ge=0.4, le=6, description="Silent tail after the last word (the button).")
    shot: Shot | None = None
    events: list[Event] = Field(default_factory=list, description="«at» is ignored: «delay» counts from the start of the ending.")
    question: str | None = Field(None, description="The closing question, as a tag at the top (e.g. «¿TÚ SE LAS HABRÍAS QUITADO?»).")
    question_delay: float = 0.6


class Episode(Strict):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,60}$")
    title: str
    premise: str = ""
    tone: str = "comedia"
    tests: list[str] = Field(default_factory=list, description="Hypotheses of docs/hipotesis.md it puts to the test.")
    series: str | None = Field("¿Y SI…?", description="Series tag (top left).")
    work: str | None = Field(None, description="Second tag: the story or subject (DON QUIJOTE).")
    palette: str = "alfar"
    voices: dict[str, Voice | str] = Field(description="Voice key → voice, or the id of a character in personajes/.")
    pace: Pace = Field(default_factory=Pace)
    counter: Counter | None = None
    title_card: TitleCard | None = None
    tags_from_beat: int | None = Field(2, description="Beat from which the series tags stay on screen (null = never).")
    music: Music | None = None
    auto_sfx: bool = Field(True, description="Sounds for cuts, stamps, counts and reveals without asking.")
    captions_y: int = Field(1390, ge=900, le=1500)
    captions_size: int = Field(104, ge=70, le=140)
    beats: list[Beat]
    ending: Ending = Field(default_factory=Ending)
    post: str = Field("", description="Text of the post: one sentence that opens the story + a request about the viewer.")

    @model_validator(mode="after")
    def _coherent(self) -> "Episode":
        if not self.beats:
            raise ValueError("el guion no tiene beats")
        if self.beats[0].shot is None:
            raise ValueError("el beat 1 tiene que abrir un plano (shot)")
        ids = [b.id for b in self.beats]
        if len(set(ids)) != len(ids):
            raise ValueError("hay ids de beat repetidos")
        unknown = sorted({b.voice for b in self.beats} - set(self.voices))
        if unknown:
            raise ValueError(f"voces sin definir en «voices»: {', '.join(unknown)}")
        return self
