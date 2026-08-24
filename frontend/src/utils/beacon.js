/**
 * Lightweight client beacon utility bundled directly into the application.
 * Dispatches navigation hits to the Cloudflare proxy in Demo Mode.
 */
export function recordPageView(path) {
  if (typeof window === 'undefined') return
  try {
    // Ignore automated headless test runners
    if (navigator.webdriver || window.callPhantom || window._phantom) return

    const endpoint = 'https://floral-pine-7c5e.joel-t-f82.workers.dev/count'
    const query = new URLSearchParams({
      p: path || (location.pathname + location.search) || '/',
      r: document.referrer || '',
      t: document.title || '',
      s: String(window.screen?.width || 0),
      rnd: Math.random().toString(36).substring(2, 7),
    })

    const targetUrl = `${endpoint}?${query.toString()}`

    if (!navigator.sendBeacon || !navigator.sendBeacon(targetUrl)) {
      fetch(targetUrl, { mode: 'no-cors', priority: 'low' }).catch(() => {})
    }
  } catch {
    // silent fallback
  }
}
