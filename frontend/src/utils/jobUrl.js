export function isLinkedInUrl(value) {
  try {
    const url = new URL(value.trim())
    const host = url.hostname.toLowerCase().replace(/\.$/, '')
    return ['http:', 'https:'].includes(url.protocol) && (host === 'linkedin.com' || host.endsWith('.linkedin.com'))
  } catch {
    return false
  }
}
