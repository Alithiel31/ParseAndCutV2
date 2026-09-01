// Notifications locales : déclenchées côté client une fois un traitement
// terminé, via le service worker déjà enregistré par vite-plugin-pwa.
// Pas de push serveur — ServiceWorkerRegistration.showNotification() est
// utilisé plutôt que `new Notification()`, qui lève une exception sur
// Android/Chrome pour une PWA installée.

export function isNotificationSupported(): boolean {
  return "Notification" in window && "serviceWorker" in navigator;
}

export function getPermission(): NotificationPermission {
  return isNotificationSupported() ? Notification.permission : "denied";
}

export async function requestPermission(): Promise<NotificationPermission> {
  return Notification.requestPermission();
}

export async function notifyResult(title: string, body: string): Promise<void> {
  const registration = await navigator.serviceWorker.ready;
  await registration.showNotification(title, {
    body,
    icon: "/apple-touch-icon.png",
    tag: "parseandcut-result",
  });
}
