import React from "react";
import { AbsoluteFill, Img, Video, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

const isVideoFile = (src) => /\.(mp4|mov|webm)$/i.test(src);

/**
 * Renders one b-roll clip with a slow Ken Burns zoom/pan — this is what
 * kills the "static crossfade" generic look the pipeline had before.
 * `intensity` ("high" for Shorts, "medium" for Longform) controls how
 * aggressive the zoom is, matching each format's pacing.
 */
export const KenBurnsClip = ({ src, durationInFrames, intensity = "medium", accentHex }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  const maxZoom = intensity === "high" ? 1.18 : 1.1;
  const scale = interpolate(frame, [0, durationInFrames], [1, maxZoom], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Alternate pan direction per clip so consecutive clips don't feel identical
  const panDirection = Math.floor(src.length) % 2 === 0 ? 1 : -1;
  const translateX = interpolate(frame, [0, durationInFrames], [0, 25 * panDirection], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const Media = isVideoFile(src) ? Video : Img;

  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#05060C" }}>
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `scale(${scale}) translateX(${translateX}px)`,
        }}
      >
        <Media
          src={src}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          muted
        />
      </div>
      {/* subtle accent-color vignette ties every clip back to the video's mood */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(to top, ${accentHex}22, transparent 40%)`,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
