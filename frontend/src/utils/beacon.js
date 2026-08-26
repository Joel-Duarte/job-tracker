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

    // 1. Image Pixel Ping (100% CORS-exempt, works universally across all browsers)
    try {
      const img = new Image()
      const query = new URLSearchParams({
        path: currentPath,
        r: referrer,
        t: title,
        w: String(screenWidth),
        _t: String(Date.now()),
      })
      img.src = `${endpoint}?${query.toString()}`
    } catch {
      // Ignore image pixel error
    }

    // 2. Fetch with mode 'no-cors' to prevent CORS policy blocks on POST
    try {
      const payload = JSON.stringify({
        path: currentPath,
        referrer,
        title,
        width: screenWidth,
      })
      fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: payload,
        mode: 'no-cors',
        keepalive: true,
      }).catch(() => {})
    } catch {
      // Ignore fetch error
    }
  } catch {
    // Silent error containment
  }
}


