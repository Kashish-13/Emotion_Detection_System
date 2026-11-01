"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "./auth";
import { listHistory, type HistoryEntry } from "./history";

/** The signed-in user's history (newest first), with a reload function. */
export function useHistory() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<HistoryEntry[] | null>(null);

  const reload = useCallback(async () => {
    if (!user) return;
    setEntries(await listHistory(user.uid));
  }, [user]);

  useEffect(() => { reload(); }, [reload]);
  return { entries, reload, uid: user?.uid };
}
