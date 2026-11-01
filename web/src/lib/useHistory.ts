"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "./auth";
import { listHistory, type HistoryEntry } from "./history";

/** The signed-in user's history (newest first), with a reload function. */
export function useHistory() {
  const { user } = useAuth();
  const uid = user?.uid;
  // Entries are tagged with the account they belong to, so another account's are never shown.
  const [loaded, setLoaded] = useState<{ uid: string; entries: HistoryEntry[] } | null>(null);
  const current = useRef(uid);
  useEffect(() => { current.current = uid; }, [uid]);

  const reload = useCallback(async () => {
    if (!uid) return;
    const entries = await listHistory(uid);
    if (current.current === uid) setLoaded({ uid, entries }); // ignore a late reply for a previous account
  }, [uid]);

  useEffect(() => { reload(); }, [reload]);
  return { entries: loaded && loaded.uid === uid ? loaded.entries : null, reload, uid };
}
