import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * Shorts-only: one-word-at-a-time kinetic captions, center-screen, active
 * word highlighted in the video's accent color. This is the Shorts-specific
 * caption treatment — Long-form uses SubtitleCaption.jsx instead, they are
 * deliberately NOT shared so each format gets pacing suited to it.
 */
export const KineticCaption = ({ words, accentHex }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const activeIndex = words.findIndex((w) => t >= w.start && t < w.end);
  if (activeIndex === -1) return null;

  const windowSize = 3;
  const start = Math.max(0, activeIndex - 1);
  const visible = words.slice(start, start + windowSize);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          display: "flex",
          gap: 18,
          padding: "0 60px",
          flexWrap: "wrap",
          justifyContent: "center",
        }}
      >
        {visible.map((w, i) => {
          const isActive = start + i === activeIndex;
          return (
            <span
              key={`${w.word}-${start + i}`}
              style={{
                fontFamily: "Montserrat, Arial, sans-serif",
                fontWeight: 800,
                fontSize: isActive ? 92 : 70,
                color: isActive ? accentHex : "rgba(255,255,255,0.55)",
                WebkitTextStroke: "3px rgba(0,0,0,0.7)",
                paintOrder: "stroke fill",
              }}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
