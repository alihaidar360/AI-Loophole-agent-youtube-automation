import { Composition } from "remotion";
import { ShortsVideo } from "./compositions/ShortsVideo";
import { LongformVideo } from "./compositions/LongformVideo";

// Both formats are registered as fully independent Compositions — each
// with its own resolution, fps, and dynamic duration calculated from the
// actual voiceover length passed in via props (see calculateMetadata).
// Default props below are just placeholders for the Remotion Studio
// preview; the real pipeline always passes --props=<path-to-json>.

const emptyTimeline = { words: [], chunks: [], visuals: [], sfxCues: [], accentHex: "#00E5FF" };

export const Root = () => {
  return (
    <>
      <Composition
        id="ShortsVideo"
        component={ShortsVideo}
        durationInFrames={30 * 45}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          audioSrc: "",
          musicSrc: "",
          durationInSeconds: 45,
          timeline: emptyTimeline,
        }}
        calculateMetadata={({ props }) => ({
          durationInFrames: Math.ceil((props.durationInSeconds || 45) * 30),
        })}
      />
      <Composition
        id="LongformVideo"
        component={LongformVideo}
        durationInFrames={30 * 720}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          audioSrc: "",
          musicSrc: "",
          durationInSeconds: 720,
          timeline: emptyTimeline,
        }}
        calculateMetadata={({ props }) => ({
          durationInFrames: Math.ceil((props.durationInSeconds || 720) * 30),
        })}
      />
    </>
  );
};
