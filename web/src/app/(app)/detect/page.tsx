"use client";

// The Detect page runs TensorFlow.js and OpenCV.js, which only work in the browser. Loading it with
// ssr: false keeps those libraries out of the server build entirely (the page is behind sign-in, so
// there is nothing to pre-render anyway).
import dynamic from "next/dynamic";

const DetectView = dynamic(() => import("./DetectView"), {
  ssr: false,
  loading: () => <div className="center"><span className="spinner muted" aria-label="Loading" /></div>,
});

export default function DetectPage() {
  return <DetectView />;
}
