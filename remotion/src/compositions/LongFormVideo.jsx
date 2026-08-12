import React from "react";
import { AbsoluteFill, Audio, Sequence, useVideoConfig } from "remotion";
import { KenBurnsClip } from "../components/KenBurnsClip";
import { SubtitleCaption } from "../components/SubtitleCaption";
import { SfxLayer } from "../components/SfxLayer";

/**
 * Longform composition: slower documentary-style cuts, medium Ken Burns,
 * sparser SFX at chapter beats, standard bottom-third subtitles. A
 * dedicated component — not a scaled-up ShortsVideo — because a 12-minute
 * video needs different pacing rules than a 50-second one.
 */
export const LongformVideo = ({ audioSrc, musicSrc, timeline }) => {
  const { fps } = useVideoConfig();
  const { visuals = [], chunks = [], sfxCues = [], accentHex = "#00E5FF" } = timeline;

  return (
    <AbsoluteFill style={{ backgroundColor: "#05060C" }}>
      {visuals.map((clip, i) => (
        <Sequence key={i} from={Math.round(clip.start * fps)} durationInFrames={Math.round(clip.duration * fps)}>
          <KenBurnsClip src={clip.src} durationInFrames={Math.round(clip.duration * fps)}
                        intensity="medium" accentHex={accentHex} />
        </Sequence>
      ))}

      <SubtitleCaption chunks={chunks} />
      <SfxLayer cues={sfxCues} />

      {audioSrc && <Audio src={audioSrc} />}
      {musicSrc && <Audio src={musicSrc} volume={0.08} loop />}
    </AbsoluteFill>
  );
};
