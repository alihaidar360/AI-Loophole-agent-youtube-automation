import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// CI runners are CPU-only — keep concurrency modest so renders don't
// starve the GitHub Actions runner of memory.
Config.setConcurrency(2);
