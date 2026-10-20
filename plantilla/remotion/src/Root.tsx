import React from "react";
import { Composition } from "remotion";
import { Cover, CoverProps } from "./compose/Cover";
import { Final } from "./compose/Final";
import { FinalProps } from "./compose/types";
import { DateGlitch, DateGlitchProps } from "./screens/DateGlitch";
import { SystemNotice, SystemNoticeProps } from "./screens/SystemNotice";
import { LAPTOP_HEIGHT, LAPTOP_WIDTH, MemorySave, MemorySaveProps } from "./screens/MemorySave";
import { PhoneCall, PhoneCallProps } from "./screens/PhoneCall";
import { PhoneChat, PhoneChatProps } from "./screens/PhoneChat";
import { LaptopChat, LaptopChatProps } from "./screens/LaptopChat";
import { StreamProfiles, StreamProfilesProps } from "./screens/StreamProfiles";
import { LoginScreen, LoginScreenProps } from "./screens/LoginScreen";
import { PHONE_HEIGHT, PHONE_WIDTH, PhoneNotifications, PhoneNotificationsProps } from "./screens/PhoneNotifications";
import { style } from "./style";

type PhoneCompProps = PhoneNotificationsProps & { duration: number };

const phoneDefaults: PhoneCompProps = {
  time: "01:07",
  app_name: "NubePay",
  items: [12.4, 86.2, 186.7, 642.9, 1024.8],
  currency: "$",
  stagger: 0.45,
  duration: 4,
};

export const Root: React.FC = () => (
  <>
    <Composition
      id="PhoneNotifications"
      component={PhoneNotifications as unknown as React.FC<PhoneCompProps>}
      width={PHONE_WIDTH}
      height={PHONE_HEIGHT}
      fps={style.fps}
      durationInFrames={120}
      defaultProps={phoneDefaults}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.round(props.duration * style.fps)) })}
    />
    <Composition
      id="PhoneCall"
      component={PhoneCall as unknown as React.FC<PhoneCallProps & { duration: number }>}
      width={PHONE_WIDTH}
      height={PHONE_HEIGHT}
      fps={style.fps}
      durationInFrames={120}
      defaultProps={{ contact: "Mamá", connect_after: 2, duration: 5 }}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.round(props.duration * style.fps)) })}
    />
    <Composition
      id="PhoneChat"
      component={PhoneChat as unknown as React.FC<PhoneChatProps & { duration: number }>}
      width={PHONE_WIDTH}
      height={PHONE_HEIGHT}
      fps={style.fps}
      durationInFrames={60}
      defaultProps={{ app_name: "Asistente", messages: [{ from_user: true, text: "eres un inútil" }, { from_user: false, text: "¡Gracias por tu comentario! 😊" }], last_at: null, duration: 2 }}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.round(props.duration * style.fps)) })}
    />
    <Composition
      id="DateGlitch"
      component={DateGlitch as unknown as React.FC<DateGlitchProps & { duration: number }>}
      width={LAPTOP_WIDTH}
      height={LAPTOP_HEIGHT}
      fps={style.fps}
      durationInFrames={60}
      defaultProps={{ date: "2049", time: "14/10 · 03:12", duration: 2 }}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.round(props.duration * style.fps)) })}
    />
    <Composition
      id="LaptopChat"
      component={LaptopChat as unknown as React.FC<LaptopChatProps & { duration: number }>}
      width={LAPTOP_WIDTH}
      height={LAPTOP_HEIGHT}
      fps={style.fps}
      durationInFrames={60}
      defaultProps={{
        app_name: "Asistente",
        messages: [{ from_user: true, text: "esa función no existe" }, { from_user: false, text: "¡Tienes toda la razón! 😊 Aquí tienes la versión corregida:" }],
        code: "const datos = await api.obtenerTodoRapido();",
        last_at: null,
        duration: 2,
      }}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.round(props.duration * style.fps)) })}
    />
    <Composition
      id="StreamProfiles"
      component={StreamProfiles as unknown as React.FC<StreamProfilesProps & { duration: number }>}
      width={LAPTOP_WIDTH}
      height={LAPTOP_HEIGHT}
      fps={style.fps}
      durationInFrames={60}
      defaultProps={{
        app_name: "CINEO",
        title: "¿Quién está viendo?",
        profiles: [{ name: "Alex", color: "#3a6df0" }, { name: "Lucía", color: "#d9668f" }, { name: "Marcos", color: "#2f9e74", is_new: true }],
        new_at: null,
        duration: 2,
      }}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.round(props.duration * style.fps)) })}
    />
    <Composition
      id="LoginScreen"
      component={LoginScreen as unknown as React.FC<LoginScreenProps & { duration: number }>}
      width={LAPTOP_WIDTH}
      height={LAPTOP_HEIGHT}
      fps={style.fps}
      durationInFrames={60}
      defaultProps={{ app_name: "Fotogram", user: "alex_", state: "error", password: "Alex12345", type_start: 0.3, type_speed: 0.11, duration: 2 }}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.round(props.duration * style.fps)) })}
    />
    <Composition
      id="SystemNotice"
      component={SystemNotice as unknown as React.FC<SystemNoticeProps & { duration: number }>}
      width={LAPTOP_WIDTH}
      height={LAPTOP_HEIGHT}
      fps={style.fps}
      durationInFrames={60}
      defaultProps={{ title: "Aviso", text: "Esta versión de Claude dejará de estar disponible el 31 de octubre.", countdown_from: null, duration: 2 }}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.round(props.duration * style.fps)) })}
    />
    <Composition
      id="MemorySave"
      component={MemorySave as unknown as React.FC<MemorySaveProps & { duration: number }>}
      width={LAPTOP_WIDTH}
      height={LAPTOP_HEIGHT}
      fps={style.fps}
      durationInFrames={120}
      defaultProps={{ title: "Guardando en memoria…", lines: ["A the lead le gusta que le escuchen.", "Y subió el .env a GitHub."], from_char: 0, to_char: null, duration: 5 }}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.round(props.duration * style.fps)) })}
    />
    <Composition
      id="Cover"
      component={Cover as unknown as React.FC<CoverProps>}
      width={style.width}
      height={style.height}
      fps={style.fps}
      durationInFrames={1}
      defaultProps={{ image: "cover_still.png", title: "Título", mark: null } as CoverProps}
    />
    <Composition
      id="Final"
      component={Final as unknown as React.FC<FinalProps>}
      width={style.width}
      height={style.height}
      fps={style.fps}
      durationInFrames={1}
      defaultProps={{ timeline: { slug: "", title: "", fps: 30, width: 1080, height: 1920, total_frames: 1, beats: [] }, video: "renders/scene.mp4" } as FinalProps}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, props.timeline.total_frames) })}
    />
  </>
);
