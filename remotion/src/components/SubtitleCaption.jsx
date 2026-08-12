import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * Long-form-only: standard bottom-third subtitles over a semi-transparent
 * box, sentence-chunked (not word-by-word — kinetic pacing would fatigue
 * viewers over 10-13 minutes). Deliberately separate from KineticCaption.
 */
export const SubtitleCaption = ({ chunks }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const active = chunks.find((c) => t >= c.start && t < c.end);
  if (!active) return null;

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 90 }}>
      <div
        style={{
          background: "rgba(0,0,0,0.55)",
          borderRadius: 14,
          padding: "16px 32px",
          maxWidth: "80%",
        }}
      >
        <span
          style={{
            fontFamily: "Roboto, Arial, sans-serif",
            fontWeight: 500,
            fontSize: 40,
            color: "#FFFFFF",
            textAlign: "center",
          }}
        >
          {active.text}
        </span>
      </div>
    </AbsoluteFill>
  );
};
