import React from "react";
import { Sequence, useVideoConfig } from "remotion";

export const KineticCaption = ({ words, accentHex }) => {
  const { fps } = useVideoConfig();
  if (!words || words.length === 0) return null;

  return (
    <>
      {words.map((w, i) => {
        const startFrame = Math.round(w.start * fps);
        const endFrame = Math.round(w.end * fps);
        const duration = Math.max(endFrame - startFrame, 3);

        return (
          <Sequence key={i} from={startFrame} durationInFrames={duration}>
            <div
              style={{
                position: "absolute",
                top: "50%",
                left: 40,
                right: 40,
                transform: "translateY(-50%)",
                textAlign: "center",
                fontFamily: "Arial, Helvetica, sans-serif",
                fontWeight: 900,
                fontSize: 88,
                color: accentHex || "#00E5FF",
                WebkitTextStroke: "3px black",
                textShadow: "0 4px 14px rgba(0,0,0,0.65)",
              }}
            >
              {w.word}
            </div>
          </Sequence>
        );
      })}
    </>
  );
};
