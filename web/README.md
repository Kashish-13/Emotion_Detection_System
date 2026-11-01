# EmotionSense — web app (Next.js on Vercel)

The Vercel version of EmotionSense. The Streamlit app in the repository root is unchanged and keeps working.

```
Browser ──► Next.js (this folder, static pages on Vercel)
              ├─ Emotion detection, entirely in the browser:
              │     OpenCV.js 4.12 (Haar face detection + preprocessing)
              │     TensorFlow.js 4.22 (the trained CNN, converted from models/emotion_model.keras)
              └─ Firebase Auth + Firestore (JS SDK, user's own token, existing firestore.rules)
```

No Python server, Docker image, inference API or paid service is needed. Images and webcam frames are analysed
on the user's device and are never uploaded.

- **Pages:** `/` landing · `/login` `/signup` `/reset-password` · `/dashboard` `/detect` `/history` `/about` (protected).
- **Detect:** upload a photo, or use the webcam (live predictions about 6–7 times a second, plus "Analyze this
  frame" for a full result with Grad-CAM).
- **History** is shared with the Streamlit app: `users/{uid}/checkins` with `kind: "detection"`, in the same format
  as `src/storage.py`. Images are never stored. If Firestore is unreachable, entries are kept in the browser.

## How inference matches the Python app

`src/lib/emotion/` reproduces the Python pipeline step by step (the Python code is the source of truth):

| Step | Python | Browser |
|---|---|---|
| Face detection | `cv2` Haar cascade, `equalizeHist`, `detectMultiScale(1.1, 5, minSize 30)` | OpenCV.js, same cascade XML (byte-identical) and parameters |
| Crop | `crop_face`: 10 % padding, clipped | `cropRect` (same integer maths) |
| Preprocess | gray → 48×48 `INTER_AREA` → /255 | identical OpenCV.js calls |
| Model | `models/emotion_model.keras` | `public/models/emotion/` (same weights, TF.js format) |
| Grad-CAM | `src/gradcam.py` (`block4_2_relu`) | `gradcamRaw` + `gradCam` (same maths) |

Measured against Python on 44 real faces and 2 whole-image inputs: model inputs identical; probabilities within
3.3 × 10⁻⁷ (WebGL, WASM and CPU backends); same predicted emotion 46/46; Grad-CAM heatmaps within 3 × 10⁻⁶ with the
same peak region 46/46.

Static assets:
- `public/models/emotion/model.json` + `weights.bin` (2.9 MB) and `public/models/haarcascade_frontalface_default.xml`
  are committed.
- `public/vendor/` (OpenCV.js 10.9 MB and the TF.js WASM binaries) is **generated** from `node_modules` by
  `scripts/copy-vendor.mjs`, which runs automatically before `npm run dev` and `npm run build`. It is git-ignored.

TF.js uses WebGL when the GPU supports full float32 precision, otherwise WASM, otherwise plain CPU.

## Environment variables

Copy `.env.example` to `.env.local` (git-ignored) for local development; set the same names in
**Vercel → Project → Settings → Environment Variables** for deployment.

| Variable | Required | Value |
|---|---|---|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | yes | Firebase Web API key (same project as the Streamlit app) |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | yes | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | no | defaults to `<project-id>.firebaseapp.com` |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | no | Firebase web app ID |
| `NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_HOST` | no | local testing only, e.g. `127.0.0.1:9099` |

The Firebase web config is public by design (it ships to every browser); data access is enforced by Firebase
Auth and the Firestore security rules. No private credential is used anywhere in this app.

## Run locally

```bash
cd web
npm install
copy .env.example .env.local           # then fill in the Firebase values
npm run dev                            # http://localhost:3000
```

Checks: `npm run lint`, `npx tsc --noEmit`, `npm test` (unit tests, incl. cross-checks against `src/config.py`
and the model files), `npm run build`.

## Deploy to Vercel

1. In Vercel: **Add New → Project → Import** `Kashish-13/Emotion_Detection_System`.
2. **Root Directory:** `web` (Framework preset: Next.js is detected automatically; the default build command
   `npm run build` also copies OpenCV.js into `public/vendor/`).
3. Add the environment variables above, then **Deploy**.
4. Firebase console → **Authentication → Settings → Authorized domains** → add the Vercel domain.

CLI alternative: `npm i -g vercel`, then from `web/`: `vercel link`, `vercel env add …`, `vercel --prod`.
