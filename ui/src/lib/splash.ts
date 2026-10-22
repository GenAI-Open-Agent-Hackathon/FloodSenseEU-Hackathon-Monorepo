/** Status text and removal for the inline loading screen in index.html. */

const MAX_WAIT_MS = 6000;
let hidden = false;

export function setSplashStatus(text: string): void {
  const status = document.getElementById("splash-status");
  if (status) {
    status.textContent = text;
  }
}

/** Fades out and removes the loading screen. Safe to call more than once. */
export function hideSplash(): void {
  const splash = document.getElementById("splash");
  if (hidden || !splash) {
    return;
  }
  hidden = true;
  splash.classList.add("is-hidden");
  window.setTimeout(() => splash.remove(), 400);
}

/** Never keep the loading screen up for long, e.g. when map tiles are slow. */
export function hideSplashAfterTimeout(): void {
  window.setTimeout(hideSplash, MAX_WAIT_MS);
}
