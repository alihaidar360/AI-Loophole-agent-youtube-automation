import React from "react";
import { AbsoluteFill, Audio, Sequence, useVideoConfig } from "remotion";
import { KenBurnsClip } from "../components/KenBurnsClip";
import { KineticCaption } from "../components/KineticCaption";
import { SfxLayer } from "../components/SfxLayer";

/**
 * Shorts composition: fast cuts, high-intensity Ken Burns, dense SFX,
 * kinetic word-by-word captions. Built as its own component (not a prop
 * variant of LongformVideo) so Shorts pacing gets dedicated attention.
 */
export const ShortsVideo = ({ audioSrc, musicSrc, timeline }) => {
  const { fps } = useVideoConfig();
  const { visuals = [], words = [], sfxCues = [], accentHex = "#00E5FF" } = timeline;

  return (
    <AbsoluteFill style={{ backgroundColor: "#05060C" }}>
      {visuals.map((clip, i) => (
        <Sequence key={i} from={Math.round(clip.start * fps)} durationInFrames={Math.round(clip.duration * fps)}>
          <KenBurnsClip src={clip.src} durationInFrames={Math.round(clip.duration * fps)}
                        intensity="high" accentHex={accentHex} />
        </Sequence>
      ))}

      <KineticCaption words={words} accentHex={accentHex} />
      <SfxLayer cues={sfxCues} />

      {audioSrc && <Audio src={audioSrc} />}
      {musicSrc && <Audio src={musicSrc} volume={0.12} loop />}
    </AbsoluteFill>
  );
};
