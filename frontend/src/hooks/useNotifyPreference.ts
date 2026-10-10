import { useState } from "react";
import { getPermission, requestPermission } from "../notifications";

const NOTIFY_STORAGE_KEY = "pac_notify";

/**
 * Préférence « me notifier à la fin du traitement », gardée sur l'appareil.
 * `setNotify(true)` demande la permission au navigateur et renvoie false si
 * elle est refusée (la préférence reste alors désactivée).
 */
export function useNotifyPreference() {
  const [notifyEnabled, setNotifyEnabled] = useState(() => {
    try {
      return localStorage.getItem(NOTIFY_STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  });

  async function setNotify(checked: boolean): Promise<boolean> {
    if (checked) {
      const permission = getPermission() === "granted" ? "granted" : await requestPermission();
      if (permission !== "granted") return false;
    }
    setNotifyEnabled(checked);
    try {
      localStorage.setItem(NOTIFY_STORAGE_KEY, String(checked));
    } catch {
      // navigation privée / stockage désactivé : la préférence reste valide pour la session en cours
    }
    return true;
  }

  return { notifyEnabled, setNotify };
}
