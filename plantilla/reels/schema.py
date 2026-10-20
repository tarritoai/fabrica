"""Pydantic models for script.json, the contract every pipeline stage reads.

Enums are closed on purpose: they mirror what exists in the assets (rigs,
camera presets, Remotion components). The writer cannot invent values.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from reels import cast as cast_mod
from reels.assets import ROOT, character_file, known_characters

MAX_WORDS_PER_LINE = 8


# Characters the template ships with (assets/characters/). Everything in personajes/<id>/ is added at import time,
# so a new character is a folder with a personaje.json, not a code change.
_TEMPLATE_CHARACTERS = [
    "novato",  # slot of the role "humano" (reels/cast.py): whoever plays the human lead
    "claude",  # slot of the role "cosa": whoever plays the thing
    "hugo",  # the lead's flatmate
    "chica",  # miniseries: the girl behind the lonely light, in her room (same voice as voz_sola)
    # Off-screen voice heard through the phone (no 3D model).
    "mama",
    # Giant robot of the future: a silhouette with red eyes built by the set, not a rig.
    "robot",
    # People heard as their lights in the miniseries world (voice only, each with their own accent).
    "voz_mx", "voz_es", "voz_ar", "voz_co",
    "voz_sola",  # the lonely light nobody answers
]
Character = Enum("Character", {c: c for c in dict.fromkeys(
    [*_TEMPLATE_CHARACTERS, *sorted(known_characters() - set(_TEMPLATE_CHARACTERS) - set(cast_mod.ROLE_SLOTS))])}, type=str)
Character.__doc__ = "Character ids: the template's plus every folder in personajes/ (see reels/cast.py for roles)."


PEOPLE = {Character.voz_mx, Character.voz_es, Character.voz_ar, Character.voz_co, Character.voz_sola}
OFFSCREEN = {Character.mama, Character.robot} | PEOPLE | {
    Character(c) for c in known_characters() - set(_TEMPLATE_CHARACTERS) if character_file(c).get("offscreen")}


class Emotion(str, Enum):
    neutral = "neutral"
    orgulloso = "orgulloso"
    confuso = "confuso"
    alarma = "alarma"
    juzgando = "juzgando"
    hundido = "hundido"
    panico = "panico"
    aliviado = "aliviado"


class Action(str, Enum):
    idle = "idle"
    talk_gesture = "talk_gesture"
    present_gesture = "present_gesture"
    shrug = "shrug"
    facepalm = "facepalm"
    lean_in = "lean_in"
    look_phone = "look_phone"
    phone_ear = "phone_ear"  # talking on the phone (phone at the ear)
    recoil = "recoil"
    slump = "slump"
    turn_away = "turn_away"  # offended: turns half its back on the other one, chin up; turns back next beat
    close_laptop = "close_laptop"  # the novato shuts the laptop lid (lands at light_at, or as his line ends); stays shut
    phone_down = "phone_down"  # the novato puts his phone face down on the desk; stays there
    phone_lower = "phone_lower"  # the novato lowers the phone he is reading to his belly, still holding it (face free)
    stretch = "stretch"  # stretches with both arms up (a lamp stretches its arm); characters list it in "actions"


class Camera(str, Enum):
    two_shot = "two_shot"
    band = "band"  # musical episodes (score): low and square on to the row of jars on the floor, the desk behind
    band_side = "band_side"  # musical: three-quarters from the left, above the V of jars (it travels)
    medium_novato_low = "medium_novato_low"
    closeup_novato = "closeup_novato"
    closeup_ai = "closeup_ai"
    phone_closeup = "phone_closeup"
    phone_screen = "phone_screen"  # pushed in on the phone's screen: the notifications read (hooks)
    establishing = "establishing"  # arrives from the galaxy to the floating room (opening shot)
    wide_space = "wide_space"  # the island alone in the galaxy, drifting away (silences, endings)
    robot_reveal = "robot_reveal"  # the future: from behind the novato, up at the giant robot
    robot_pov = "robot_pov"  # the future: the robot's view down onto the tiny room
    wide_epic = "wide_epic"  # the future's last shot: the island and the giant robot together, from afar
    standoff = "standoff"  # the future: low behind the AI standing in front of the novato, up at the robot
    closeup_other = "closeup_other"  # the other human in the scene (the flatmate), close
    medium_other = "medium_other"  # the other human, medium shot (e.g. on the sofa)
    over_shoulder = "over_shoulder"  # behind the novato: his laptop screen and the AI beside it
    screen_closeup = "screen_closeup"  # the novato's point of view on the laptop screen (readable text)
    # Set `mundo` (miniseries): the room's portal and the world inside.
    portal_open = "portal_open"  # the room: the portal opens on the floor by the desk
    cruce = "cruce"  # the crossing: swallowed by the portal, white flash, spat out onto the meadow (one silent beat, ~5 s)
    mundo_wide = "mundo_wide"  # behind them, the whole world; the first one after arriving is where the evening falls
    mundo_two_shot = "mundo_two_shot"  # the two of them on the meadow, from the side
    mundo_closeup_novato = "mundo_closeup_novato"
    mundo_closeup_ai = "mundo_closeup_ai"
    luces_cerca = "luces_cerca"  # a person's light close up, with its AI listening (for their voice)
    luces_cerca_b = "luces_cerca_b"  # another one
    luz_sola = "luz_sola"  # over their shoulders, down at the lonely islet; they turn to it on the beat before
    negro = "negro"  # hard cut to black (series cliffhanger)
    # Miniseries part 2 (tres-tokens): the lonely light up close, looking into it, and the girl's real room.
    luz_sola_cerca = "luz_sola_cerca"  # the lonely jar of light on its islet, close
    luz_sola_llegada = "luz_sola_llegada"  # opening: wide of the whole world at dusk, swooping down to the lonely jar
    claude_islote = "claude_islote"  # Claude beside the lonely light, where her AI should be
    asomarse = "asomarse"  # The lead leans into the light and the camera goes in with his gaze (transition, silent)
    cuarto_chica = "cuarto_chica"  # her dark room, the phone lighting her face (medium)
    cuarto_chica_cerca = "cuarto_chica_cerca"  # her face, close (the smile, the whisper)
    humano_asomado = "humano_asomado"  # reverse shot: the lead looking into the light, lit by it
    # Copies of the AI (beat.ai_copies / ai_mini, regenerar-coro).
    wide_room = "wide_room"  # the whole room from the front: desk, bookcase and floor (where the copies are)
    closeup_mini = "closeup_mini"  # the tiny copy behind the mug, close (needs ai_mini)


_SETS = {
    # The default: a bedroom-office (desk, laptop, window onto a city by night or by day), dressed by set_options.
    "habitacion": "habitacion",
    "escritorio_noche": "escritorio_noche",  # older scripts: the same room at night
    # Generic sets for any niche (blender/sets_generic.py), dressed by Episode.set_options:
    "estudio": "estudio",  # plain-colour studio with an infinite backdrop and a plinth (explainers, products)
    "mostrador": "mostrador",  # a shop counter by day: café or bakery ("variant"), human behind, thing on the counter
    "exterior": "exterior",  # a park by day (running, walks, outdoors)
}
# A brand pack copied over the template (blender/sets_marca.py + mundo.py) adds the original series' world.
if (ROOT / "blender" / "mundo.py").exists():
    _SETS["mundo"] = "mundo"
Set = Enum("Set", _SETS, type=str)
Set.__doc__ = "Sets (blender/sets.py): habitacion (default), the generic ones, and any a brand pack adds."


class SetCast(BaseModel):
    """What a set can stage: who must be there (its cameras are built around them) and how many fit on screen."""

    requires: list[str] = Field(default_factory=list)
    max_on_screen: int = 3


# The cast rule lives per set, not globally: today's sets frame everything around the novato (cameras.py,
# build_scene.py, mundo.py), so they keep requiring him; a new set registers its own rule here when it is built.
SET_CAST: dict[str, SetCast] = {
    "habitacion": SetCast(requires=[cast_mod.HUMAN]),
    "escritorio_noche": SetCast(requires=[cast_mod.HUMAN]),
    "mundo": SetCast(requires=[cast_mod.HUMAN]),
    # The generic sets frame whoever is there: the human, the thing, or both.
    "estudio": SetCast(),
    "mostrador": SetCast(),
    "exterior": SetCast(),
}


class Memento(str, Enum):
    """Small glowing objects that float up around the novato while he remembers something."""

    cv = "cv"  # a fanned stack of printed CVs
    caja = "caja"  # a moving box
    reloj = "reloj"  # a digital clock at 04:00
    taza = "taza"  # a coffee mug


class Light(str, Enum):
    """Room light mood from this beat on (default noche: cold, late at night)."""

    noche = "noche"
    madrugada = "madrugada"  # 3 a.m.: the room sunk in shadow, the lamp low; the screen and the AI's glow carry the light
    tibio = "tibio"  # a little warmth back
    calido = "calido"  # warm, intimate (lamp up, fairy lights glowing, moon down)
    amanecer = "amanecer"  # dawn after the threat: golden light, the fairy lights come back
    apagon = "apagon"  # power cut: lamp and fairy lights dead, the laptop screen is the only light
    oscuro = "oscuro"  # the laptop dies too: only the cold light from space
    ruinas = "ruinas"  # the future: the room's lights dead, only cold space light (a red siren comes from the set)


class Nonverbal(str, Enum):
    """A wordless vocal sound in the character's own voice (reactor of a silent beat, or the speaker)."""

    risa = "risa"  # a small laugh through the nose
    suspiro = "suspiro"


class Sfx(str, Enum):
    ding = "ding"
    ding_alarm = "ding_alarm"
    whoosh = "whoosh"
    error = "error"
    portal_rumble = "portal_rumble"  # miniseries: the portal opening, a low rumble and wind rising
    tunnel_whoosh = "tunnel_whoosh"  # rushing down the tunnel of lights
    sky_burst = "sky_burst"  # bursting out into the open sky of the world
    typing_tiny = "typing_tiny"  # a few soft keystrokes (someone typing a short password)
    tension = "tension"  # a low dark swell (3 s): the moment it hurts (a reveal, before a silence)
    click = "click"  # a trackpad click (pressing regenerate); one per press, timed with sfx_at
    toc = "toc"  # a soft clay knock: a copy of the jar is suddenly there (at the cut)
    cadena = "cadena"  # a toilet flushing in the next room (portatil-al-bano)
    grifo = "grifo"  # a bathroom tap running in the next room (portatil-al-bano)


class AudioTag(str, Enum):
    """ElevenLabs v4 audio tags (written in English inside the TTS text). Freer ones go in delivery.spoken."""

    whispers = "whispers"
    sighs = "sighs"
    sarcastic = "sarcastic"
    curious = "curious"
    laughs = "laughs"
    excited = "excited"
    crying = "crying"
    terrified = "terrified"
    nervous = "nervous"
    chuckles = "chuckles"
    softly = "softly"
    emotional = "emotional"
    concerned = "concerned"


INCOMPATIBLE_TAGS = [
    {AudioTag.whispers, AudioTag.excited},
    {AudioTag.whispers, AudioTag.laughs},
    {AudioTag.crying, AudioTag.laughs},
    {AudioTag.crying, AudioTag.excited},
    {AudioTag.terrified, AudioTag.laughs},
    {AudioTag.terrified, AudioTag.chuckles},
]


class Delivery(BaseModel):
    """Voice direction for a spoken beat (PLAN.md §5a)."""

    tags: list[AudioTag] = Field(default_factory=list, description="0 to 2 compatible audio tags.")
    pace: Literal["lento", "normal", "rapido"] = Field("normal", description="Sent to the voice as a tag ([rushed] / "
        "[slowly]) unless `spoken` is set (then write the pace into it). There is no speed setting: never speed up in post.")
    pause_before: float = Field(0.0, description="Seconds of silence before the line (0 to 2). Kept in the edit.")
    intensity: Literal["baja", "media", "alta"] = "media"
    spoken: str | None = Field(
        None, description="Exact text sent to the voice (eleven_v4) when the subtitle must stay clean; replaces tags + line "
        "for TTS only. Free tags that describe the voice work best ('[flat, bored voice]', '[trembling] O-oye...'); "
        "pauses with '...', '[short pause]' or '[long pause]'; ONE word in capitals for emphasis ('Que NO.'); commas "
        "where the line runs on and full stops only where it should breathe (v4 pauses at every full stop); a line cut "
        "off ends in '-'; '[jumping in]' / '[interrupting]' for a reply that cuts in."
    )
    creative: bool = Field(False, description="Creative stability (0.0): the only mode where strong emotions really land.")
    seed: int | None = Field(None, description="A solo take picked by ear (reels voice --pick): always used for this line.")
    max_gap: float | None = Field(None, description="Shorten pauses inside the take to at most this many seconds (keeps the acting).")
    chorus: int = Field(1, ge=1, le=6, description="AI lines only: stack this many takes of the voice (slightly offset and "
                        "detuned) so it sounds like a crowd; every visible copy of the AI (beat.ai_copies) mouths it.")
    mini: bool = Field(False, description="AI lines only: said by the tiny copy (beat.ai_mini) instead of the AI: same voice "
                       "pitched up, and only the tiny one's mouth moves.")

    @field_validator("tags")
    @classmethod
    def compatible_tags(cls, v: list[AudioTag]) -> list[AudioTag]:
        if len(v) > 2:
            raise ValueError("at most 2 audio tags per line")
        if any(pair <= set(v) for pair in INCOMPATIBLE_TAGS):
            raise ValueError(f"incompatible audio tags: {[t.value for t in v]}")
        return v


class PhoneMessage(BaseModel):
    app: str = Field(description='App or source shown on the card, e.g. "Noticias".')
    text: str = Field(description="The notification text, one short sentence.")


class PhoneNotificationsProps(BaseModel):
    time: str = Field(description='Lock-screen clock, e.g. "01:07".')
    date: str = Field("", description='Lock-screen date above the clock, e.g. "jueves, 23 de octubre" (empty = none). '
                      "Keep it consistent with the story (the night before a Thursday exam is Thursday at 3:31).")
    app_name: str = Field("", description="Invented brand name of the billing app, never a real company.")
    items: list[float] = Field(default_factory=list, description="Escalating charge amounts, 3 to 6 values.")
    messages: list[PhoneMessage] = Field(
        default_factory=list, description="Text notifications instead of charges (they escalate the same way, 3 to 6)."
    )
    currency: Literal["$", "€"] = "$"
    stagger: float = Field(0.45, description="Seconds between notifications.")


class PhoneNotificationsEvent(BaseModel):
    type: Literal["screen"] = "screen"
    component: Literal["PhoneNotifications"] = "PhoneNotifications"
    props: PhoneNotificationsProps

    def duration(self) -> float:
        return len(self.props.items or self.props.messages) * self.props.stagger + 1.2


class PhoneCallProps(BaseModel):
    contact: str = Field(description='Contact name as saved in the phone, e.g. "Mamá".')
    connect_after: float | None = Field(
        1.6, description="Seconds ringing before the call connects (and the timer starts). null = nobody answers."
    )


class PhoneCallEvent(BaseModel):
    type: Literal["screen"] = "screen"
    component: Literal["PhoneCall"] = "PhoneCall"
    props: PhoneCallProps

    def duration(self) -> float:
        # The other side speaks as soon as it connects.
        return (self.props.connect_after or 2.5) + 0.3


class CounterRevealProps(BaseModel):
    value: int = Field(description="Final number the counter lands on.")
    label: str = Field(description="What is being counted, short, in Spanish (shown under the number).")
    footnote: str | None = Field(None, description="Small text at the bottom (source or context).")


class CounterRevealEvent(BaseModel):
    """Full-screen data card over the darkened shot (the visual climax)."""

    type: Literal["overlay"] = "overlay"
    component: Literal["CounterReveal"] = "CounterReveal"
    props: CounterRevealProps

    def duration(self) -> float:
        return 3.2


class MemorySaveProps(BaseModel):
    title: str = Field("Guardando en memoria…", description="Header shown while the AI saves.")
    lines: list[str] = Field(default_factory=list, description="Memory lines, in Spanish, short.")
    from_char: int = Field(0, description="Characters (across all lines, joined) already written when the beat starts.")
    to_char: int | None = Field(None, description="Typing stops here (null = the end): one sentence can span several shots.")

    def typed_count(self) -> int:
        total = sum(len(line) for line in self.lines)
        return max(0, min(total, self.to_char if self.to_char is not None else total) - self.from_char)


class ChatMessage(BaseModel):
    from_user: bool
    text: str


class PhoneChatProps(BaseModel):
    owner: Character = Field(Character.novato, description="Whose phone shows it (the flatmate can have his own).")
    app_name: str = Field("Asistente", description="Generic chat app title: never a real brand UI.")
    messages: list[ChatMessage]
    last_at: float | None = Field(None, description="Seconds into the beat when the last message appears (null = all there).")


class PhoneChatEvent(BaseModel):
    """A chat with an assistant on someone's phone, shown while they talk (adds no time)."""

    type: Literal["screen"] = "screen"
    component: Literal["PhoneChat"] = "PhoneChat"
    props: PhoneChatProps

    def duration(self) -> float:
        return 0.0


TYPE_SPEED = 0.055  # s per character on the laptop screen


class MemorySaveEvent(BaseModel):
    """The AI writing to its memory file, on the novato's laptop screen."""

    type: Literal["screen"] = "screen"
    component: Literal["MemorySave"] = "MemorySave"
    props: MemorySaveProps

    def duration(self) -> float:
        n = self.props.typed_count()
        return 1.4 if not n else 0.3 + n * TYPE_SPEED + 0.4


class DateGlitchProps(BaseModel):
    date: str = Field(description='Big date on a broken screen, e.g. "2049".')
    time: str = Field("", description="Small line under it.")
    broken: bool = Field(True, description="Cracked and flickering (the future) or intact and calm (back to today).")


class DateGlitchEvent(BaseModel):
    """The laptop screen, cracked and flickering, stuck on a date (a jump in time, shown in-world)."""

    type: Literal["screen"] = "screen"
    component: Literal["DateGlitch"] = "DateGlitch"
    props: DateGlitchProps

    def duration(self) -> float:
        return 0.0


class SystemNoticeProps(BaseModel):
    title: str = Field(description='Small header, e.g. "Aviso" or "Retirada en".')
    text: str = Field("", description="The message (one or two short sentences).")
    countdown_from: int | None = Field(None, description="Show a countdown instead of text: seconds left when the beat starts.")
    battery: int | None = Field(None, description="Show a battery at this percentage instead of text (it drains beat by beat; 0 = dead screen).")


class SystemNoticeEvent(BaseModel):
    """A calm system message on the laptop: a notice, or a countdown that ticks down in real time."""

    type: Literal["screen"] = "screen"
    component: Literal["SystemNotice"] = "SystemNotice"
    props: SystemNoticeProps

    def duration(self) -> float:
        return 0.0


class LaptopChatProps(BaseModel):
    app_name: str = Field("Asistente", description="Generic chat app title: never a real brand UI.")
    messages: list[ChatMessage]
    code: str | None = Field(None, description="Optional code snippet under the assistant's last reply (small detail).")
    last_at: float | None = Field(None, description="Seconds into the beat when the last message appears (null = all there).")
    variant: int | None = Field(None, ge=1, description="Show the regenerate button (↻) and the answer counter 'n/n' "
                                "starting at this number (null = no button).")
    regen_at: list[float] = Field(default_factory=list, description="Seconds into the beat where ↻ is pressed: each press "
                                  "bumps the counter by one and the last reply pops in again (pair it with sfx click).")
    theme: Literal["neutral", "tarro", "tarro_noche"] = Field("neutral", description="neutral: a generic dark chat; tarro "
                                                             "(cream) / tarro_noche (warm dark): our jar's clay and glaze, "
                                                             "with the jar as the icon, so it reads as Claude's own chat.")
    text_scale: float = Field(1.0, ge=0.8, le=1.6, description="Bubble text size (1 = default). ~1.4 for a short chat that "
                              "has to read on a phone in the first second; long messages or code need 1.")


class LaptopChatEvent(BaseModel):
    """A chat with a generic AI open on the novato's laptop (readable in screen_closeup / over_shoulder)."""

    type: Literal["screen"] = "screen"
    component: Literal["LaptopChat"] = "LaptopChat"
    props: LaptopChatProps

    def duration(self) -> float:
        return 0.0


class StreamProfileItem(BaseModel):
    name: str
    color: str = Field("#3a6df0", description="Tile colour (hex).")
    is_new: bool = Field(False, description="Flagged 'Nuevo' and outlined; pops in at new_at.")


class StreamProfilesProps(BaseModel):
    app_name: str = Field("CINEO", description="Invented streaming brand: never a real one.")
    title: str = "¿Quién está viendo?"
    profiles: list[StreamProfileItem]
    new_at: float | None = Field(None, description="Seconds into the beat when the is_new profile pops in (null = already there).")


class StreamProfilesEvent(BaseModel):
    """A generic streaming app's profile picker on the novato's laptop (who uses the account; read in screen_closeup)."""

    type: Literal["screen"] = "screen"
    component: Literal["StreamProfiles"] = "StreamProfiles"
    props: StreamProfilesProps

    def duration(self) -> float:
        return 0.0


class LoginScreenProps(BaseModel):
    app_name: str = Field("Fotogram", description="Plain-text name (may name the real service, as the dialogue does); never its logo or look.")
    user: str = "alex_"
    state: Literal["error", "typing"] = Field("error", description="error: wrong password (red, shakes); typing: a new one is typed, then 'saved'.")
    password: str = Field(description="error: shown as dots (its length); typing: the text typed in plain.")
    type_start: float = Field(0.3, description="typing: seconds into the beat when the first character appears.")
    type_speed: float = Field(0.11, description="typing: seconds per character.")


class LoginScreenEvent(BaseModel):
    """A generic login on the novato's laptop (bright, readable in screen_closeup): a strong opening hook."""

    type: Literal["screen"] = "screen"
    component: Literal["LoginScreen"] = "LoginScreen"
    props: LoginScreenProps

    def duration(self) -> float:
        return 0.0


# Plain union (no discriminator): structured outputs get a simple anyOf; the Literal `component` disambiguates.
Event = (
    PhoneNotificationsEvent | PhoneCallEvent | CounterRevealEvent | MemorySaveEvent | PhoneChatEvent | DateGlitchEvent
    | SystemNoticeEvent | LaptopChatEvent | StreamProfilesEvent | LoginScreenEvent
)
PHONE_COMPONENTS = {"PhoneNotifications", "PhoneCall", "PhoneChat"}
LAPTOP_COMPONENTS = {"MemorySave", "DateGlitch", "SystemNotice", "LaptopChat", "StreamProfiles", "LoginScreen"}


class Beat(BaseModel):
    id: int
    speaker: Character | None = Field(description="null for silent beats (screen events or mute reactions).")
    line: str | None = Field(description=f"Spoken line, {MAX_WORDS_PER_LINE} words or fewer. null for silent beats.")
    delivery: Delivery | None = Field(None, description="Voice direction. Required when there is a line.")
    reactor: Character | None = Field(None, description="Silent beats only: whose face reacts (default novato).")
    emotion: Emotion = Field(description="Speaker emotion (reactor's for silent beats).")
    listener_emotion: Emotion = Field(description="Emotion of the other character(s) during this beat.")
    action: Action
    camera: Camera
    cut_camera: Camera | None = Field(None, description="A second shot inside this beat, from cut_at on (e.g. cut to the "
                                      "screen to see the counter race at the end of a burst of clicks).")
    cut_at: float | None = Field(None, description="Seconds into the beat where it cuts to cut_camera.")
    event: Event | None = None
    sfx: list[Sfx] = Field(default_factory=list)
    sfx_at: list[float] = Field(default_factory=list, description="Seconds into the beat for each sfx (same order); missing = at the cut.")
    hold: float = Field(0.3, description="Extra seconds of silence after the line.")
    memento: Memento | None = Field(None, description="A memory object that floats up around the novato at this beat.")
    mementos: Literal["away", "keep"] | None = Field(
        None, description="away: the floating memories dim and drift into the galaxy; keep: one comes back into the AI."
    )
    light: Light | None = Field(None, description="Change the room light from this beat on (null = keep the current one).")
    light_snap: bool = Field(False, description="Change the light instantly (a hard cut) instead of a slow fade.")
    light_at: float | None = Field(None, description="Seconds into the beat where the light change starts (null = at the "
                                   "beat's start). With close_laptop, the lid lands right then.")
    ambience: Literal["noche", "ruinas", "calma", "luces"] | None = Field(
        None, description="Background sound from this beat on: noche (room hum, default), ruinas (far siren + machine drone), "
        "calma (nothing: only the music) or luces (miniseries world: a soft murmur of many far voices, words never readable)."
    )
    nonverbal: Nonverbal | None = Field(None, description="Silent beats: a wordless sound (laugh, sigh) from the reactor.")
    nonverbal_at: float = Field(0.4, description="Seconds into the beat where the nonverbal sound starts.")
    ai_move: Literal["laptop", "front", "back"] | None = Field(
        None, description="The AI goes to the laptop (to type), to the front of the desk (to shield the novato) or back."
    )
    tears: Literal["wet", "tear"] | None = Field(
        None, description="The novato's eyes: wet (glossy, holding it in) or tear (also one drop rolls down his cheek at tear_at)."
    )
    tear_at: float = Field(0.8, description="Seconds into the beat where the tear wells up.")
    ai_power: Literal["off", "on"] | None = Field(
        None, description="The AI shuts down (eyes close, its light dies, it sags) or boots up again (light flickers on, eyes open)."
    )
    ai_power_at: float = Field(0.0, description="Seconds into the beat where it shuts down / boots up.")
    ai_move_instant: bool = Field(False, description="Jump there on the cut instead of walking (it was already there).")
    ai_move_at: float = Field(0.0, description="Seconds into the beat where the AI sets off.")
    gaze: str | None = Field(None, description="Where the actor looks this beat: a character id, or a set point such as "
                             "'_light' (the lonely light in the world).")
    ai_copies: int | None = Field(None, ge=1, le=12, description="From this beat on, how many copies of the AI stand in "
                                  "the room (1 = only the AI). They appear on the cut, as if they were always there.")
    ai_mini: bool | None = Field(None, description="From this beat on, show (true) or hide (false) a tiny copy of the AI "
                                 "behind the mug (it speaks with delivery.mini; camera closeup_mini).")
    novato_away: bool | None = Field(None, description="From this beat on, the novato has left the room with his laptop "
                                     "(true: empty chair, his lines echo from the bathroom and the others look at the door) "
                                     "or is back (false). portatil-al-bano.")
    ai_flourish: Literal["hop", "giggle"] | None = Field(
        None, description="A cute AI beat right after its line: hop = a little smug jump; giggle = laughing inside (lid rattles, eyes squint).")
    bars: float | None = Field(None, gt=0, description="Musical episodes (episode.score): how many bars this shot lasts "
                               "(halves and quarters allowed). The beats' bars add up to the score's.")

    @field_validator("line")
    @classmethod
    def short_line(cls, v: str | None) -> str | None:
        if v is not None and len(v.split()) > MAX_WORDS_PER_LINE:
            raise ValueError(f"line has more than {MAX_WORDS_PER_LINE} words: {v!r}")
        return v

    @model_validator(mode="after")
    def speaker_line_consistent(self) -> Beat:
        if (self.speaker is None) != (self.line is None):
            raise ValueError("speaker and line must both be set or both be null")
        if self.speaker is not None and self.delivery is None:
            self.delivery = Delivery()
        if self.speaker is None and self.event is None and self.hold < 0.8 and self.bars is None:
            raise ValueError("a mute reaction beat needs hold >= 0.8 s")
        return self


class Source(BaseModel):
    type: Literal["evergreen", "news"] = "evergreen"
    links: list[str] = Field(default_factory=list)


class Series(BaseModel):
    name: str
    part: int
    of: int | None = Field(None, description="Total parts: the last beat, if it is the `negro` camera, shows a small 'part/of'.")


class Music(BaseModel):
    mood: Literal["agridulce", "chill", "tension", "comedia", "epica"]
    track: str | None = Field(None, description="A specific clip from assets/music/music.json (its file), instead of picking by mood.")
    start_at_beat: int | None = Field(None, description="Beat id where the music comes in (null = from the start).")
    swell_level: float = Field(0.6, description="Music level at the swell (0.6 gentle; up to 1.0 for an all-out climax).")
    align_end: bool = Field(False, description="Play the clip so that its own ending lands on the video's last frame (a built-in climax).")
    swell_at_beat: int | None = Field(None, description="Beat id where the music rises (usually the final silence).")
    fade_in: float = Field(1.5, description="Seconds the entrance (start_at_beat) and the comeback (resume_at_beat) take to fade in.")
    cut_at_beat: int | None = Field(
        None, description="Beat id where the music stops dead (a twist at the emotional peak)."
    )
    resume_at_beat: int | None = Field(
        None, description="After a cut: beat id where the music comes back (fading in, as if it never stopped playing)."
    )
    start_delay: float = Field(0.0, description="Seconds after start_at_beat begins where the music comes in (e.g. mid-beat).")
    restart: bool = Field(False, description="The music starts from its own beginning at its entrance (a hit), instead of "
                          "fading in mid-song.")
    duck: list[int] | None = Field(None, description="[first, last] beat ids where the music sits lower (e.g. under the "
                                   "most intimate voices), easing in and out over a second.")
    duck_db: float = Field(-3.0, description="How much lower during `duck`, in dB.")
    cut_fade: float | None = Field(None, description="Seconds the music takes to melt away at cut_at_beat (null = a dead stop).")


STEPS_PER_BAR = 16  # score patterns are written in sixteenths


class ScoreTrack(str, Enum):
    tarro = "tarro"  # the melody, played on the jars: each pitch class is one jar (score.jars)
    bajo = "bajo"
    pad = "pad"  # sustained chords ("D3+F3+A3")
    bombo = "bombo"
    caja = "caja"
    hats = "hats"


class ScoreSection(BaseModel):
    name: str
    bars: int = Field(ge=1)
    palette: Literal["ambar", "neon", "frio", "arcoiris", "negro"] = Field(
        "ambar", description="Colours of the room washes in this section (negro: the room goes dark, only the jars glow).")
    energy: float = Field(0.6, ge=0, le=1, description="How hard the room lights pump on the kick (0 still … 1 a party).")
    riser: bool = Field(False, description="A noise swell builds across the section into the next one.")
    wobble: int = Field(0, ge=0, le=16, description="The bass growls open and shut this many times per bar (4 quarters, "
                        "8 eighths; 0 = a plain sub). A light on the floor breathes with it.")
    impact: bool = Field(False, description="The section opens with a hit (sub boom + flash): the drop.")
    blackout_tail: int = Field(0, ge=0, description="Last sixteenths of the section with every room light dead (the gap "
                               "before the drop; leave the patterns silent there too).")
    tracks: dict[ScoreTrack, str] = Field(
        default_factory=dict, description="One pattern per track, one token per sixteenth ('|' between bars is decoration). "
        "Tokens: '.' rest, '-' hold the previous note, a note ('E5', 'F#4') or chord ('D3+F3+A3'); drums 'x' hit, 'X' accent, "
        "'o' ghost (hats: 'O' open). A '!' after a tarro note ('D6!') is an accent: louder, and the jar spins. "
        "A pattern shorter than the section loops.")


class Score(BaseModel):
    """Musical episodes: the music is written here and both the audio and the animation come from it (reels/score.py)."""

    bpm: float = Field(112.5, description="Pick one where a sixteenth lands on whole frames at 30 fps: 75, 90, 112.5 or 150.")
    jars: list[str] = Field(description="Pitch classes of the tarro track, one per jar: the first is the AI itself, then "
                            "its copies in order (beat.ai_copies must put them in the room).")
    sections: list[ScoreSection]

    @model_validator(mode="after")
    def check(self) -> Score:
        step = 60 / self.bpm / 4 * 30
        if abs(step - round(step)) > 1e-6:
            raise ValueError(f"bpm {self.bpm}: a sixteenth is {step:.2f} frames at 30 fps (use 75, 90, 112.5 or 150)")
        return self

    def bars(self) -> int:
        return sum(s.bars for s in self.sections)


class Episode(BaseModel):
    slug: str = Field(description="kebab-case, ascii, short.")
    title: str
    premise: str
    tone: Literal["comedia", "agridulce", "serie"] = "comedia"
    series: Series | None = None
    music: Music | None = None
    score: Score | None = Field(None, description="Musical episode: the music is composed here instead of a library clip; "
                                "the shots last beat.bars and every note moves and lights the jars.")
    characters: list[Character]
    reparto: dict[str, str] = Field(default_factory=dict, description="Who plays each role in this episode: "
                                    '{"humano": "<character id>", "cosa": "<character id>"}. Filled in when loaded '
                                    "(reparto.json, or inferred from `characters`); write it only to force a choice.")
    source: Source = Field(default_factory=Source)
    set: Set = Set.habitacion
    set_options: dict[str, str | bool | float] = Field(default_factory=dict, description=(
        "Colours and switches of the set, e.g. {\"window\": \"dia\", \"wall\": \"#6f8a74\"} (habitacion), {\"background\": \"#e8dcc8\"} (estudio), "
        "{\"variant\": \"obrador\", \"accent\": \"#2f6b5a\"} (mostrador), {\"grass\": \"#86b35c\"} (exterior)."))
    loop_hint: str
    alt_hooks: list[str] = Field(description="Two alternative first lines (hook candidates).")
    hook: str | None = Field(None, description="Short hook text shown at the top for the first ~2.5 s (what the reel is about, 3-7 words).")
    tests: list[str] = Field(default_factory=list, description="Hypothesis ids from docs/hipotesis.md this reel tests (e.g. H3).")
    beats: list[Beat]

    @model_validator(mode="before")
    @classmethod
    def resolve_cast_names(cls, data):
        """Scripts may use the student's own names for each role (reparto.json): translate them to internal ids."""
        return cast_mod.resolve_script(data) if isinstance(data, dict) else data

    def players(self) -> dict[str, str]:
        """slot -> character id that plays it in this episode (reels/cast.py)."""
        return {cast_mod.ROLE_SLOTS[role]: who for role, who in self.reparto.items()}

    @model_validator(mode="after")
    def check_cast(self) -> Episode:
        for role, who in self.reparto.items():
            if role not in cast_mod.ROLE_SLOTS:
                raise ValueError(f'reparto: role "{role}" does not exist (humano, cosa)')
            if cast_mod.kind_of(who) != role:
                raise ValueError(f'reparto: "{who}" cannot play the role {role}')
        cast_mod.activate(self.players())
        rule = SET_CAST.get(self.set.value, SetCast())
        on_screen = [c for c in self.characters if c not in OFFSCREEN]
        voices = [c for c in self.characters if c in OFFSCREEN and c not in PEOPLE]
        if not 1 <= len(on_screen) <= rule.max_on_screen or len(voices) > 1:
            raise ValueError(f"set {self.set.value}: 1 to {rule.max_on_screen} on-screen characters "
                             "(plus one off-screen voice and any PEOPLE voices)")
        cast = set(self.characters)
        missing = [c for c in rule.requires if Character(c) not in cast]
        if missing:
            raise ValueError(f"set {self.set.value} is built around {', '.join(cast_mod.script_name(c) for c in missing)} "
                             "(role humano): they must be in the cast "
                             "(a set without them needs its own SET_CAST rule and cameras)")
        for b in self.beats:
            if b.speaker is not None and b.speaker not in cast:
                raise ValueError(f"beat {b.id}: speaker {cast_mod.script_name(b.speaker.value)} not in characters")
            if b.reactor in OFFSCREEN:
                raise ValueError(f"beat {b.id}: {b.reactor.value} is off-screen and cannot react on camera")
        if self.beats and self.beats[-1].speaker is not None:
            raise ValueError("the episode must end with a mute reaction beat (speaker and line null)")
        ids = [b.id for b in self.beats]
        if len(set(ids)) != len(ids):
            raise ValueError("beat ids must be unique")
        if self.score:
            if any(b.bars is None for b in self.beats):
                raise ValueError("musical episode: every beat needs `bars`")
            if abs(sum(b.bars for b in self.beats) - self.score.bars()) > 1e-6:
                raise ValueError(f"the beats last {sum(b.bars for b in self.beats)} bars, the score {self.score.bars()}")
            if self.music:
                raise ValueError("a musical episode brings its own music: drop `music`")
        return self
