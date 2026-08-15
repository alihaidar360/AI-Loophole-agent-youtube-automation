import React from "react";
import { Composition, registerRoot } from "remotion";
import { ShortsVideo } from "./compositions/ShortsVideo";
import { LongformVideo } from "./compositions/LongformVideo";

const FPS = 30;

const defaultProps = {
  audioPath: "",
  visualPaths: [],
  words: [],
  chunks: [],
  sfxCues: [],
  accentHex: "#00E5FF",
  musicPath: null,
  durationInSeconds: 30,
};

// Video length varies per job (depends on voiceover length), so duration
// is calculated at render time from the durationInSeconds prop.
const calculateMetadata = ({ props }) => {
  const duration = props.durationInSeconds || 30;
  return {
    durationInFrames: Math.max(Math.round(duration * FPS), FPS),
  };
};

const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="ShortsVideo"
        component={ShortsVideo}
        durationInFrames={900}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
        calculateMetadata={calculateMetadata}
      />
      <Composition
        id="LongformVideo"
        component={LongformVideo}
        durationInFrames={18000}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={defaultProps}
        calculateMetadata={calculateMetadata}
      />
    </>
  );
};

registerRoot(RemotionRoot);
