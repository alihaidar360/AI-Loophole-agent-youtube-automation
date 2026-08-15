import React from "react";
import { Sequence, useVideoConfig } from "remotion";

export const SubtitleCaption = ({ chunks }) => {
  const { fps } = useVideoConfig();
  if (!chunks || chunks.length === 0) return null;

  return (
    <>
      {chunks.map((c, i) => {
        const startFrame = Math.round(c.start * fps);
        const endFrame = Math.round(c.end * fps);
        const duration = Math.max(endFrame - startFrame, 3);

        return (
          <Sequence key={i} from={startFrame} durationInFrames={duration}>
            <div style={{ position: "absolute", bottom: 90, left: 100, right: 100, textAlign: "center" }}>
              <span
                style={{
                  background: "rgba(0,0,0,0.55)",
                  color: "#FFFFFF",
                  fontFamily: "Arial, Helvetica, sans-serif",
                  fontSize: 38,
                  fontWeight: 500,
                  padding: "12px 28px",
                  borderRadius: 14,
                  display: "inline-block",
                  lineHeight: 1.3,
                }}
              >
                {c.text}
              </span>
            </div>
          </Sequence>
        );
      })}
    </>
  );
};
