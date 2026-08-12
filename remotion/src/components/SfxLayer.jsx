import React from "react";
import { Audio, Sequence, useVideoConfig } from "remotion";

/**
 * Places every sound-design cue (whoosh/impact/riser/click/pop — see
 * modules/sound_design.py) onto the timeline as its own Sequence+Audio.
 * This is the layer that makes cuts and chapter transitions actually
 * SOUND edited, instead of silent hard-cuts.
 */
export const SfxLayer = ({ cues }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {cues.map((cue, i) => (
        <Sequence key={i} from={Math.round(cue.time * fps)} durationInFrames={Math.round(1.2 * fps)}>
          <Audio src={cue.sfx} volume={cue.volume ?? 0.4} />
        </Sequence>
      ))}
    </>
  );
};
