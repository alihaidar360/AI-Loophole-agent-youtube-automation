import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { KenBurnsClip } from "../components/KenBurnsClip";
import { SubtitleCaption } from "../components/SubtitleCaption";
import { SfxLayer } from "../components/SfxLayer";

export const LongformVideo = ({
  audioPath,
  visualPaths,
  chunks,
  sfxCues,
  accentHex,
  musicPath,
  durationInSeconds,
}) => {
  const durationInFrames = Math.round((durationInSeconds || 600) * 30);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      <KenBurnsClip visualPaths={visualPaths} durationInFrames={durationInFrames} />
      <SubtitleCaption chunks={chunks} />
      <SfxLayer sfxCues={sfxCues} />
      {audioPath ? <Audio src={staticFile(audioPath)} /> : null}
      {musicPath ? <Audio src={staticFile(musicPath)} volume={0.12} loop /> : null}
    </AbsoluteFill>
  );
};
