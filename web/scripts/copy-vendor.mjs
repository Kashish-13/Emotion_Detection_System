// Copies prebuilt browser libraries from node_modules into public/vendor/ (git-ignored) so they are
// served as static files instead of being bundled. Runs automatically before `npm run dev` / `npm run build`.
//   - OpenCV.js (face detection + preprocessing)  -> public/vendor/opencv-<version>.js
//   - TensorFlow.js WASM binaries (WASM backend)  -> public/vendor/tfjs-wasm/
import { copyFileSync, mkdirSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const vendor = join(root, "public/vendor");
const pkgVersion = (name) => JSON.parse(readFileSync(join(root, "node_modules", name, "package.json"), "utf8")).version;

const opencv = pkgVersion("@techstark/opencv-js");
const version = opencv.split("-")[0]; // "4.12.0-release.1" -> "4.12.0" (must match OPENCV_VERSION in src/lib/emotion/core.ts)
mkdirSync(join(vendor, "tfjs-wasm"), { recursive: true });
copyFileSync(join(root, "node_modules/@techstark/opencv-js/dist/opencv.js"), join(vendor, `opencv-${version}.js`));
console.log(`copied OpenCV.js ${opencv} -> public/vendor/opencv-${version}.js`);

const wasmDir = join(root, "node_modules/@tensorflow/tfjs-backend-wasm/dist");
const wasm = readdirSync(wasmDir).filter((f) => f.endsWith(".wasm"));
for (const f of wasm) copyFileSync(join(wasmDir, f), join(vendor, "tfjs-wasm", f));
console.log(`copied ${wasm.length} TF.js WASM binaries -> public/vendor/tfjs-wasm/`);
