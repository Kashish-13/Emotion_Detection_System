import type { NextConfig } from "next";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // The camera is used only by this site, for live emotion detection on the Detect page.
  { key: "Permissions-Policy", value: "camera=(self), microphone=(), geolocation=()" },
];

// Static inference assets: the model and OpenCV.js are large, so let browsers cache them.
const cacheDay = [{ key: "Cache-Control", value: "public, max-age=86400, stale-while-revalidate=604800" }];
const cacheYear = [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [
      { source: "/:path*", headers: securityHeaders },
      { source: "/models/:path*", headers: cacheDay },
      { source: "/vendor/tfjs-wasm/:path*", headers: cacheDay },
      { source: "/vendor/opencv-:version.js", headers: cacheYear }, // versioned file name
    ];
  },
};

export default nextConfig;
