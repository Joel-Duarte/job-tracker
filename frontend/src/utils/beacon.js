/**
 * Client beacon utility for tracking GitHub Pages demo visits.
 * Uses CORS-free image pixel GET + silent no-cors fetch to ensure
 * zero console warnings or CORS preflight failures across all browsers.
 */

export function recordPageView(path) {
  if (typeof window === 'undefined') return
  try {
    // Ignore automated headless test runners
    if (navigator.webdriver || window.callPhantom || window._phantom) return

    const endpoint = 'https://floral-pine-7c5e.joel-t-f82.workers.dev/api/ping'
    const currentPath = path || (location.pathname + location.search) || '/'
    const referrer = document.referrer || ''
    const title = document.title || ''
    const screenWidth = window.screen?.width || 0

    // Extract ?ref=, ?utm_source=, or ?source= from URL search params
    let refTag = ''
    try {
      const urlParams = new URLSearchParams(window.location.search)
      refTag =
        urlParams.get('ref') ||
        urlParams.get('utm_source') ||
        urlParams.get('source') ||
        ''
    } catch {
      // fallback
    }

    const payload = JSON.stringify({
      path: currentPath,
      referrer,
      ref: refTag,
      title,
      width: screenWidth,
      timestamp: new Date().toISOString(),
    })

    // Dispatch POST request (works with 200 OK across all desktop & mobile browsers)
    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
      body: payload,
      mode: 'no-cors',
      keepalive: true,
    }).catch(() => {})
  } catch {
    // Silent error containment
  }
}



