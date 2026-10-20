import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily } from "../fonts";

// A generic login on the novato's laptop in our own design. app_name may name a real service as plain text
// (a reference, like saying it in the dialogue), but never its logo, gradient or interface.
// Saturated colour on purpose (the opening shot is the first frame in the feed), but no white: the laptop
// screen is emissive and light UI burns out to a blank white card. Dark card, light text.
// state "error": the password is wrong (red, the card shakes once).
// state "typing": a new password is typed in plain text from type_start, then "saved" appears.
export type LoginScreenProps = {
  app_name: string;
  user: string;
  state: "error" | "typing";
  password: string;
  type_start?: number;
  type_speed?: number;
};

export const LoginScreen: React.FC<LoginScreenProps> = ({ app_name, user, state, password, type_start = 0.3, type_speed = 0.11 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const error = state === "error";
  const shake = error ? 14 * Math.sin(t * 55) * Math.exp(-t * 7) : 0;
  const typed = error ? password.length : Math.max(0, Math.min(password.length, Math.floor((t - type_start) / type_speed) + 1));
  const done = !error && t > type_start + password.length * type_speed + 0.25;
  const savedIn = interpolate(t, [type_start + password.length * type_speed + 0.25, type_start + password.length * type_speed + 0.45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const caret = !error && !done && Math.floor(t * 2.5) % 2 === 0;
  const field = (label: string, value: React.ReactNode, bad = false) => (
    <div style={{ marginTop: 22 }}>
      <div style={{ fontSize: 32, fontWeight: 700, color: "#9a9db0", marginBottom: 8 }}>{label}</div>
      <div
        style={{
          height: 96,
          borderRadius: 16,
          border: `4px solid ${bad ? "#ff5a5f" : "#3a3d4a"}`,
          background: bad ? "#3a1518" : "#14151b",
          display: "flex",
          alignItems: "center",
          padding: "0 24px",
          fontSize: 54,
          fontWeight: 700,
          color: "#f3f3f7",
          letterSpacing: 1,
        }}
      >
        {value}
      </div>
    </div>
  );
  return (
    <AbsoluteFill style={{ fontFamily, background: "linear-gradient(160deg,#1d3fc2,#0f9e9a)", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: 920, background: "#1d1e26", borderRadius: 40, padding: "44px 60px 48px", boxShadow: "0 18px 50px rgba(0,0,0,0.35)", transform: `translateX(${shake}px)` }}>
        <div style={{ fontSize: 60, fontWeight: 900, textAlign: "center", color: "#f3f3f7" }}>
          {app_name}
        </div>
        {field("Usuario", user)}
        {field(
          error ? "Contraseña" : "Nueva contraseña",
          error ? (
            "•".repeat(password.length)
          ) : (
            <span>
              {password.slice(0, typed)}
              <span style={{ opacity: caret ? 1 : 0, color: "#7b5cff" }}>|</span>
            </span>
          ),
          error,
        )}
        <div style={{ height: 64, marginTop: 20, fontSize: 46, fontWeight: 800, textAlign: "center" }}>
          {error && <span style={{ color: "#ff5a5f" }}>Contraseña incorrecta</span>}
          {!error && <span style={{ color: "#3ddc84", opacity: savedIn }}>Contraseña guardada</span>}
        </div>
      </div>
    </AbsoluteFill>
  );
};
