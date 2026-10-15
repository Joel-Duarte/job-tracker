/**
 * Client beacon utility for tracking GitHub Pages demo visits.
 * Persists visitor ID and campaign tags across tabs using localStorage
 * with sessionStorage fallback.
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
    // ignore localStorage error
  }
  try {
    sessionStorage.setItem(key, value)
  } catch {
    // ignore sessionStorage error
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
    // Ignore automated headless webdriver flags
    if (navigator.webdriver || window.callPhantom || window._phantom) return

    const endpoint = 'https://floral-pine-7c5e.joel-t-f82.workers.dev/api/ping'
    const currentPath = path || (location.pathname + location.search) || '/'
    const rawReferrer = document.referrer || ''
    const title = document.title || ''
    const screenWidth = window.screen?.width || 0

    // 1. Get or create a cross-tab visitor ID
    let visitorId = getStorageItem('jt_visitor_id')
    if (!visitorId) {
      visitorId =
        Math.random().toString(36).substring(2, 10) +
        Date.now().toString(36)
      setStorageItem('jt_visitor_id', visitorId)
    }

    // 2. Extract campaign tag from current URL, passed path, referrer URL, or storage
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

    // Filter out internal same-site URLs from raw referrer so internal navigation
    // doesn't overwrite campaign/referrer tracking
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

    const effectiveReferrer = refTag || externalReferrer || ''

    const payload = JSON.stringify({
      path: currentPath,
      referrer: effectiveReferrer,
      ref: effectiveReferrer,
      campaign: refTag,
      title,
      width: screenWidth,
      visitorId,
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