import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { KenBurnsClip } from "../components/KenBurnsClip";
import { KineticCaption } from "../components/KineticCaption";
import { SfxLayer } from "../components/SfxLayer";

export const ShortsVideo = ({
  audioPath,
  visualPaths,
  words,
  sfxCues,
  accentHex,
  musicPath,
  durationInSeconds,
}) => {
  const durationInFrames = Math.round((durationInSeconds || 30) * 30);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      <KenBurnsClip visualPaths={visualPaths} durationInFrames={durationInFrames} />
      <KineticCaption words={words} accentHex={accentHex} />
      <SfxLayer sfxCues={sfxCues} />
      {audioPath ? <Audio src={staticFile(audioPath)} /> : null}
      {musicPath ? <Audio src={staticFile(musicPath)} volume={0.12} loop /> : null}
    </AbsoluteFill>
  );
};
