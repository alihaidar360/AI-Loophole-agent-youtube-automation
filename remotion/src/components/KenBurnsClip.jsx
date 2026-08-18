import React from "react";
import { OffthreadVideo, Img, Sequence, staticFile, useCurrentFrame, interpolate } from "remotion";

const isImage = (path) => /\.(png|jpg|jpeg|webp)$/i.test(path || "");

const SingleClip = ({ path, durationInFrames }) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, durationInFrames], [1, 1.12], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  const style = { width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})` };

  if (!path) return null;
  const src = staticFile(path); // path is relative to assets/, served via --public-dir

  return isImage(path) ? <Img src={src} style={style} /> : <OffthreadVideo src={src} style={style} muted />;
};

// Splits the full video duration evenly across all provided visual clips,
// each with its own slow Ken Burns zoom.
export const KenBurnsClip = ({ visualPaths, durationInFrames }) => {
  const clips = visualPaths && visualPaths.length ? visualPaths : [];
  if (clips.length === 0) return null;

  const perClip = Math.max(Math.floor(durationInFrames / clips.length), 1);

  return (
    <>
      {clips.map((path, i) => (
        <Sequence key={`${path}-${i}`} from={i * perClip} durationInFrames={perClip}>
          <SingleClip path={path} durationInFrames={perClip} />
        </Sequence>
      ))}
    </>
  );
};
