# EmotionSense — web app (Next.js on Vercel)

The Vercel version of EmotionSense. The Streamlit app in the repository root is unchanged and keeps working.

```
Browser ──► Next.js (this folder, Vercel)
              ├─ Firebase Auth + Firestore (JS SDK, user's own token, existing firestore.rules)
              └─ POST /api/predict ──► inference API (../inference_api, Docker on Hugging Face Spaces)
                                          └─ existing src/ pipeline + models/emotion_model.keras
```

- **Pages:** `/` landing · `/login` `/signup` `/reset-password` · `/dashboard` `/detect` `/history` `/about` (protected).
- **Prediction** runs on the inference API, because TensorFlow is far larger than Vercel's Python function limit.
- **History** is shared with the Streamlit app: `users/{uid}/checkins` with `kind: "detection"`, in the same
  format as `src/storage.py`. Images are never stored. If Firestore is unreachable, entries are kept in the
  browser (localStorage) and the cloud is retried after a minute.

## Environment variables

Copy `.env.example` to `.env.local` (git-ignored) for local development; set the same names in
**Vercel → Project → Settings → Environment Variables** for deployment.

| Variable | Required | Value |
|---|---|---|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | yes | Firebase Web API key (same project as the Streamlit app) |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | yes | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | no | defaults to `<project-id>.firebaseapp.com` |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | no | Firebase web app ID |
| `NEXT_PUBLIC_INFERENCE_API_URL` | yes | e.g. `https://<hf-user>-emotionsense-api.hf.space` (no trailing slash) |
| `NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_HOST` | no | local testing only, e.g. `127.0.0.1:9099` |

The Firebase web config is public by design (it ships to every browser); data access is enforced by Firebase
Auth and the Firestore security rules. No private credential is used anywhere in this app.

## Run locally

```bash
# 1) inference API (from the repository root, in the Python venv)
.venv\Scripts\activate
pip install -r inference_api/requirements.txt
set REQUIRE_AUTH=false                 # PowerShell: $env:REQUIRE_AUTH="false"
uvicorn inference_api.main:app --port 8000

# 2) web app (second terminal)
cd web
npm install
copy .env.example .env.local           # then fill in the values; INFERENCE_API_URL=http://localhost:8000
npm run dev                            # http://localhost:3000
```

Checks: `npm run lint`, `npx tsc --noEmit`, `npm run build`.

## Deploy to Vercel

1. Deploy the inference API first (see `../inference_api/README.md`) and note its URL.
2. In Vercel: **Add New → Project → Import** `Kashish-13/Emotion_Detection_System`.
3. **Root Directory:** `web` (Framework preset: Next.js is detected automatically).
4. Add the environment variables above, then **Deploy**.
5. Put the Vercel URL into the API's `ALLOWED_ORIGINS` on Hugging Face (and restart the Space).
6. Firebase console → **Authentication → Settings → Authorized domains** → add the Vercel domain.

CLI alternative: `npm i -g vercel`, then from `web/`: `vercel link`, `vercel env add …`, `vercel --prod`.
