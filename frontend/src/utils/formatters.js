/**
 * Utility formatters and normalizers for Job Tracker UI
 */

/**
 * Normalizes noisy work model strings like:
 * - "HYBRID/ON-SITE (IMPLIED BY 'DEVELOPMENT · LISBON')" -> "Hybrid"
 * - "REMOTE (GLOBAL)" -> "Remote"
 * - "ON-SITE / IN-OFFICE" -> "On-site"
 */
export function normalizeWorkModel(raw) {
  if (!raw) return null
  const text = String(raw).trim()
  if (!text) return null

  const lower = text.toLowerCase()

  if (lower.includes('hybrid')) return 'Hybrid'
  if (lower.includes('remote') || lower.includes('telecommute')) return 'Remote'
  if (lower.includes('on-site') || lower.includes('onsite') || lower.includes('in-office') || lower.includes('in office')) {
    return 'On-site'
  }

  // Clean parenthetical notes if any
  const cleaned = text.replace(/\s*\([^)]*\)/g, '').trim()
  if (cleaned.length > 0 && cleaned.length <= 20) {
    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1)
  }

  return 'On-site'
}

/**
 * Normalizes employment types like:
 * - "VAST (FULL-TIME)" -> "Full-Time"
 * - "PERMANENT / FULL TIME" -> "Full-Time"
 * - "CONTRACT / 6 MONTHS" -> "Contract"
 */
export function normalizeEmploymentType(raw) {
  if (!raw) return null
  const text = String(raw).trim()
  if (!text) return null

  const lower = text.toLowerCase()
  if (lower.includes('full-time') || lower.includes('full time') || lower.includes('permanent')) {
    return 'Full-Time'
  }
  if (lower.includes('part-time') || lower.includes('part time')) {
    return 'Part-Time'
  }
  if (lower.includes('contract') || lower.includes('contractor') || lower.includes('freelance')) {
    return 'Contract'
  }
  if (lower.includes('intern') || lower.includes('internship')) {
    return 'Internship'
  }

  return text.replace(/\s*\([^)]*\)/g, '').trim()
}

/**
 * Formats salary ranges cleanly into compact representation:
 * - (180000, 220000, 'USD') -> "$180k–$220k"
 * - (150000, null, 'USD') -> "From $150k"
/**
 * Returns canonical currency symbol for display (e.g., 'EUR' -> '€', 'GBP' -> '£', 'USD' -> '$')
 */
export function getCurrencySymbol(curr = 'USD') {
  switch (String(curr || '').toUpperCase()) {
    case 'EUR':
    case 'EURO':
    case 'EUROS':
    case '€':
      return '€'
    case 'GBP':
    case 'POUND':
    case 'POUNDS':
    case '£':
      return '£'
    case 'CAD':
    case 'CA$':
      return 'CA$'
    case 'AUD':
    case 'AU$':
      return 'AU$'
    case 'CHF':
      return 'CHF'
    case 'BRL':
    case 'R$':
      return 'R$'
    case 'JPY':
    case '¥':
      return '¥'
    case 'USD':
    case '$':
    default:
      return '$'
  }
}

/**
 * Formats salary ranges cleanly into compact representation:
 * - (180000, 220000, 'USD') -> "$180k–$220k"
 * - (150000, null, 'USD') -> "From $150k"
 * - (null, 200000, 'EUR') -> "Up to €200k"
 */
export function formatSalaryRange(min, max, currency = 'USD') {
  const numMin = min !== null && min !== undefined ? Number(min) : null
  const numMax = max !== null && max !== undefined ? Number(max) : null

  const sym = getCurrencySymbol(currency)

  if (numMin && numMax) {
    const minK = Math.round(numMin / 1000)
    const maxK = Math.round(numMax / 1000)
    return `${sym}${minK}k–${sym}${maxK}k`
  }
  if (numMin) {
    return `From ${sym}${Math.round(numMin / 1000)}k`
  }
  if (numMax) {
    return `Up to ${sym}${Math.round(numMax / 1000)}k`
  }
  return null
}

/**
 * Friendly relative date formatting:
 * - "Today, 4:15 PM"
 * - "Tomorrow, 2:00 PM"
 * - "Yesterday, 10:30 AM"
 * - "Due in 2 days"
 * - "Overdue by 1 day"
 * - "May 14, 2026"
 */
export function formatRelativeDate(dateStr, includeTime = false) {
  if (!dateStr) return ''
  try {
    const target = new Date(dateStr)
    if (isNaN(target.getTime())) return String(dateStr)

    const now = new Date()
    const targetMidnight = new Date(target.getFullYear(), target.getMonth(), target.getDate())
    const nowMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate())

    const diffDays = Math.round((targetMidnight - nowMidnight) / (1000 * 60 * 60 * 24))

    // Check if the input is a date-only string (e.g. "2026-09-14") or midnight UTC fallback
    const rawStr = typeof dateStr === 'string' ? dateStr.trim() : ''
    const isDateOnly =
      /^\d{4}-\d{2}-\d{2}$/.test(rawStr) ||
      (rawStr.includes('T00:00:00') &&
        !rawStr.includes('T00:00:00.') &&
        target.getUTCHours() === 0 &&
        target.getUTCMinutes() === 0 &&
        target.getUTCSeconds() === 0)

    const shouldShowTime = includeTime && !isDateOnly
    const timeStr = target.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    })

    if (diffDays === 0) {
      return shouldShowTime ? `Today, ${timeStr}` : 'Today'
    }
    if (diffDays === 1) {
      return shouldShowTime ? `Tomorrow, ${timeStr}` : 'Tomorrow'
    }
    if (diffDays === -1) {
      return shouldShowTime ? `Yesterday, ${timeStr}` : 'Yesterday'
    }
    if (diffDays > 1 && diffDays <= 7) {
      return shouldShowTime ? `In ${diffDays} days, ${timeStr}` : `In ${diffDays} days`
    }
    if (diffDays < -1 && diffDays >= -7) {
      return `${Math.abs(diffDays)} days ago`
    }

    const dateFormatted = target.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: target.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    })

    return shouldShowTime ? `${dateFormatted}, ${timeStr}` : dateFormatted
  } catch {
    return String(dateStr)
  }
}

const KNOWN_ATS_DOMAINS = new Set([
  'greenhouse.io',
  'lever.co',
  'ashbyhq.com',
  'workday.com',
  'myworkdayjobs.com',
  'smartrecruiters.com',
  'bamboohr.com',
  'jobvite.com',
  'icims.com',
  'rippling-ats.com',
  'recruitee.com',
  'applytojob.com',
  'workable.com',
  'breezy.hr',
  'jazzhr.com',
  'pinpointhq.com',
  'teamtailor.com',
  'polymer.co',
  'otta.com',
  'wellfound.com',
  'linkedin.com',
  'indeed.com',
  'glassdoor.com',
])

const ATS_VENDOR_ALIASES = {
  'ashbyhq.com': ['ashby', 'ashbyhq'],
  'greenhouse.io': ['greenhouse', 'greenhousesoftware'],
  'lever.co': ['lever'],
  'workday.com': ['workday'],
  'smartrecruiters.com': ['smartrecruiters'],
  'bamboohr.com': ['bamboohr'],
  'rippling.com': ['rippling'],
  'rippling-ats.com': ['rippling'],
  'jobvite.com': ['jobvite'],
  'icims.com': ['icims'],
  'workable.com': ['workable'],
  'breezy.hr': ['breezy', 'breezyhr'],
  'jazzhr.com': ['jazzhr'],
  'pinpointhq.com': ['pinpoint', 'pinpointhq'],
  'teamtailor.com': ['teamtailor'],
  'recruitee.com': ['recruitee'],
}

/**
 * Returns clean company domain from company object or company name
 */
export function getCompanyDomain(companyName, existingDomain = null) {
  const cleaned = companyName
    ? String(companyName)
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '')
    : ''

  if (existingDomain && String(existingDomain).includes('.')) {
    let clean = String(existingDomain)
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\//, '')
      .replace(/[?#].*$/, '')
      .replace(/\/.*$/, '')
      .replace(/^www\./, '')

    let isATS = Array.from(KNOWN_ATS_DOMAINS).some(
      (ats) => clean === ats || clean.endsWith(`.${ats}`)
    )

    if (isATS && cleaned) {
      for (const [atsDomain, aliases] of Object.entries(ATS_VENDOR_ALIASES)) {
        if (
          (clean === atsDomain || clean.endsWith(`.${atsDomain}`)) &&
          aliases.includes(cleaned)
        ) {
          isATS = false
          clean = atsDomain
          break
        }
      }
    }

    if (!isATS) {
      // Strip common recruitment / career subdomains so brand favicons resolve
      clean = clean.replace(/^(careers|jobs|apply|talent|work|join|recruiting|corp)\./, '')
      if (clean.length > 3 && clean.includes('.')) {
        return clean
      }
    }
  }
  if (!companyName) return null

  if (!cleaned) return null

  // Common known mappings
  const overrides = {
    stripe: 'stripe.com',
    linear: 'linear.app',
    figma: 'figma.com',
    datadog: 'datadoghq.com',
    airbnb: 'airbnb.com',
    google: 'google.com',
    apple: 'apple.com',
    microsoft: 'microsoft.com',
    amazon: 'amazon.com',
    meta: 'meta.com',
    netflix: 'netflix.com',
    uber: 'uber.com',
    spotify: 'spotify.com',
    notion: 'notion.so',
    slack: 'slack.com',
    github: 'github.com',
    gitlab: 'gitlab.com',
    vercel: 'vercel.com',
    supabase: 'supabase.com',
    postman: 'postman.com',
    openai: 'openai.com',
    anthropic: 'anthropic.com',
    canva: 'canva.com',
    snowflake: 'snowflake.com',
    cloudflare: 'cloudflare.com',
    discord: 'discord.com',
    zoom: 'zoom.us',
    atlassian: 'atlassian.com',
    ashby: 'ashbyhq.com',
    ashbyhq: 'ashbyhq.com',
    greenhouse: 'greenhouse.io',
    lever: 'lever.co',
    workday: 'workday.com',
    smartrecruiters: 'smartrecruiters.com',
    bamboohr: 'bamboohr.com',
    rippling: 'rippling.com',
    jobvite: 'jobvite.com',
    icims: 'icims.com',
    workable: 'workable.com',
    breezyhr: 'breezy.hr',
    jazzhr: 'jazzhr.com',
    pinpoint: 'pinpointhq.com',
    teamtailor: 'teamtailor.com',
    recruitee: 'recruitee.com',
  }

  if (overrides[cleaned]) {
    return overrides[cleaned]
  }

  return `${cleaned}.com`
}

/**
 * Returns Google Favicon service URL for a company domain
 */
export function getCompanyFaviconUrl(companyName, existingDomain = null, size = 64) {
  const domain = getCompanyDomain(companyName, existingDomain)
  if (!domain) return null
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=${size}`
}

/**
 * Formats ISO date string into human-readable format (e.g. Sep 1, 2026)
 */
export function formatDate(dateString) {
  if (!dateString) return ''
  try {
    const d = new Date(dateString)
    if (isNaN(d.getTime())) return String(dateString)
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return String(dateString)
  }
}

