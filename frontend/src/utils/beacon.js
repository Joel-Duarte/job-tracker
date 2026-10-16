/**
 * Lightweight client beacon utility for GitHub Pages.
 * Persists campaign references across navigation and sends events
 * directly to the Cloudflare Worker D1 pipeline.
 */

function getStorageItem(key) {
  try {
    return localStorage.getItem(key) || sessionStorage.getItem(key) || ''
  } catch {
    return ''
  }
}

function setStorageItem(key, value) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // ignore storage error
  }
  try {
    sessionStorage.setItem(key, value)
  } catch {
    // ignore storage error
  }
}

function extractRefFromUrlString(urlStr) {
  if (!urlStr) return ''
  try {
    const qIndex = urlStr.indexOf('?')
    if (qIndex === -1) return ''
    const params = new URLSearchParams(urlStr.slice(qIndex))
    return (
      params.get('ref') ||
      params.get('utm_source') ||
      params.get('source') ||
      ''
    )
  } catch {
    return ''
  }
}

export function recordPageView(path) {
  if (typeof window === 'undefined') return
  try {
    // Prevent automated headless scrapers from triggering pageviews
    if (navigator.webdriver || window.callPhantom || window._phantom) return

    const endpoint = 'https://floral-pine-7c5e.joel-t-f82.workers.dev/api/ping'
    const currentPath = path || (location.pathname + location.search) || '/'
    const rawReferrer = document.referrer || ''

    // Detect campaign parameter across current URL, supplied path, or incoming referrer
    const queryRef =
      extractRefFromUrlString(window.location.search) ||
      extractRefFromUrlString(currentPath) ||
      extractRefFromUrlString(rawReferrer)

    let refTag = ''
    if (queryRef) {
      refTag = queryRef
      setStorageItem('jt_campaign_ref', queryRef)
    } else {
      refTag = getStorageItem('jt_campaign_ref')
    }

    // Suppress internal domain referrer to preserve external referrer integrity
    let externalReferrer = rawReferrer
    try {
      if (rawReferrer) {
        const refUrl = new URL(rawReferrer)
        if (refUrl.hostname === window.location.hostname) {
          externalReferrer = ''
        }
      }
    } catch {
      externalReferrer = ''
    }

    const payload = JSON.stringify({
      path: currentPath,
      referrer: externalReferrer,
      campaign: refTag,
      timestamp: new Date().toISOString(),
    })

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