/**
 * Client-Side Programmatic PII Scrubber
 * Redacts emails, phone numbers, social URLs, and street addresses before network transmission.
 */

const EMAIL_PATTERN = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g

const PHONE_PATTERN = /(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,9}\b/g

const URL_PATTERN = /https?:\/\/(?:www\.)?(?:linkedin\.com\/(?:in|pub)\/[a-zA-Z0-9_%-]+|github\.com\/[a-zA-Z0-9_%-]+|twitter\.com\/[a-zA-Z0-9_%-]+|x\.com\/[a-zA-Z0-9_%-]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\/[^\s]*)/g

const ADDRESS_PATTERN = /\b\d{1,5}\s+[A-Za-z0-9.\s]{2,30}\s+(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Way|Drive|Dr|Lane|Ln|Court|Ct|Circle|Cir|Terrace|Terr|Ter|Place|Pl|Square|Sq|Highway|Hwy|Parkway|Pkwy)\b(?:[,\s]+[A-Za-z\s]+[,\s]+[A-Z]{2}\s+\d{5}(?:-\d{4})?)?/gi

const ADDRESS_LINE_PREFIX_PATTERN = /^(?:Address|Location|Residential Address)\s*:\s*(.+)$/gim

export function scrubCVText(rawText) {
  if (!rawText || !rawText.trim()) {
    return {
      scrubbedText: '',
      stats: { emails: 0, phones: 0, urls: 0, addresses: 0, headerName: 0, total: 0 },
    }
  }

  const stats = { emails: 0, phones: 0, urls: 0, addresses: 0, headerName: 0, total: 0 }
  const lines = rawText.split('\n')

  const excludedHeadings = [
    'summary', 'profile', 'objective', 'experience', 'education',
    'skills', 'projects', 'work history', 'technical skills',
    'certifications', 'about me', 'curriculum vitae', 'resume',
  ]

  if (lines.length > 0) {
    let firstLineIdx = 0
    while (firstLineIdx < lines.length && !lines[firstLineIdx].trim()) {
      firstLineIdx++
    }

    if (firstLineIdx < lines.length) {
      const firstLine = lines[firstLineIdx].trim()
      const firstLineLower = firstLine.toLowerCase()
      if (
        firstLine.length <= 45 &&
        !excludedHeadings.includes(firstLineLower) &&
        !excludedHeadings.some((h) => firstLineLower.startsWith(h)) &&
        !/[:;{}#/]/.test(firstLine)
      ) {
        lines[firstLineIdx] = '[Candidate Name]'
        stats.headerName = 1
      }
    }
  }

  let text = lines.join('\n')

  // Address prefix lines
  text = text.replace(ADDRESS_LINE_PREFIX_PATTERN, () => {
    stats.addresses++
    return 'Address: [Address Redacted]'
  })

  // Emails
  const emailMatches = text.match(EMAIL_PATTERN) || []
  stats.emails = emailMatches.length
  text = text.replace(EMAIL_PATTERN, '[Email Redacted]')

  // URLs
  const urlMatches = text.match(URL_PATTERN) || []
  stats.urls = urlMatches.length
  text = text.replace(URL_PATTERN, '[Profile Link Redacted]')

  // Addresses
  const addressMatches = text.match(ADDRESS_PATTERN) || []
  stats.addresses += addressMatches.length
  text = text.replace(ADDRESS_PATTERN, '[Address Redacted]')

  // Phones
  text = text.replace(PHONE_PATTERN, (match) => {
    const digitCount = (match.match(/\d/g) || []).length
    if (digitCount >= 7 && digitCount <= 15) {
      stats.phones++
      return '[Phone Redacted]'
    }
    return match
  })

  stats.total = stats.emails + stats.phones + stats.urls + stats.addresses + stats.headerName

  return {
    scrubbedText: text,
    stats,
  }
}
