import type { NextConfig } from "next";

// standalone: the Docker image runs `node server.js` from .next/standalone (deployment-setup skill).
const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
};

export default config;
