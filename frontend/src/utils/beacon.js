/**
 * Stealth client beacon utility bundled directly into the application.
 * Dispatches standard JSON POST requests to Cloudflare proxy in Demo Mode.
 */
export function recordPageView(path) {
  if (typeof window === 'undefined') return
  try {
    // Ignore automated headless test runners
    if (navigator.webdriver || window.callPhantom || window._phantom) return

    const endpoint = 'https://floral-pine-7c5e.joel-t-f82.workers.dev/api/ping'
    const payload = JSON.stringify({
      path: path || (location.pathname + location.search) || '/',
      referrer: document.referrer || '',
      title: document.title || '',
      width: window.screen?.width || 0,
    })

    if (navigator.sendBeacon) {
      // Use text/plain to avoid CORS preflights in Firefox and strict privacy browsers
      const blob = new Blob([payload], { type: 'text/plain;charset=UTF-8' })
      navigator.sendBeacon(endpoint, blob)
    } else {
      fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: payload,
        mode: 'no-cors',
        keepalive: true,
      }).catch(() => {})
    }
  } catch {
    // silent fallback
  }
}
