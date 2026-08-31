import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// Concurrency left at Remotion's default (auto-detects available CPU
// cores). Forcing it to 1 made long-form renders (10-13 min, 1080p)
// far too slow and caused timeouts — GitHub Actions runners have 2+
// cores available, so let Remotion use them.
