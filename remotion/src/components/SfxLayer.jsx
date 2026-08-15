import React from "react";
import { Audio, Sequence, useVideoConfig } from "remotion";

export const SfxLayer = ({ sfxCues }) => {
  const { fps, durationInFrames } = useVideoConfig();
  if (!sfxCues || sfxCues.length === 0) return null;

  return (
    <>
      {sfxCues.map((cue, i) => {
        const from = Math.max(Math.round(cue.startTime * fps), 0);
        if (from >= durationInFrames) return null;
        return (
          <Sequence key={i} from={from} durationInFrames={Math.min(fps * 2, durationInFrames - from)}>
            <Audio src={cue.path} volume={0.7} />
          </Sequence>
        );
      })}
    </>
  );
};
