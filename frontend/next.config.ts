import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The plan's URL is http://127.0.0.1:3000; Next dev blocks dev resources from
  // non-"localhost" origins unless listed here (page would never hydrate).
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
