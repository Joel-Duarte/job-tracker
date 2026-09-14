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
export function formatSalaryRange(min, max, currency = 'USD', period = null) {
  const numMin = min !== null && min !== undefined ? Number(min) : null
  const numMax = max !== null && max !== undefined ? Number(max) : null

  const sym = getCurrencySymbol(currency)

  let suffix = ''
  if (period === 'YEARLY') suffix = ' / yr'
  else if (period === 'MONTHLY') suffix = ' / mo'
  else if (period === 'HOURLY') suffix = ' / hr'

  if (numMin && numMax) {
    if (numMax < 1000) {
      return `${sym}${numMin}–${sym}${numMax}${suffix}`
    }
    const minK = Math.round(numMin / 1000)
    const maxK = Math.round(numMax / 1000)
    return `${sym}${minK}k–${sym}${maxK}k${suffix}`
  }
  if (numMin) {
    if (numMin < 1000) {
      return `From ${sym}${numMin}${suffix}`
    }
    return `From ${sym}${Math.round(numMin / 1000)}k${suffix}`
  }
  if (numMax) {
    if (numMax < 1000) {
      return `Up to ${sym}${numMax}${suffix}`
    }
    return `Up to ${sym}${Math.round(numMax / 1000)}k${suffix}`
  }
  return null
}

const MONTH_SHORT = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

/**
 * Extracts floating wall-clock datetime string (YYYY-MM-DDTHH:mm or YYYY-MM-DD)
 * without applying timezone conversion or offset shifting.
 */
export function toLocalDatetimeString(dateStr) {
  if (!dateStr) return ''
  const str = String(dateStr).trim()
  const m = str.match(/^(\d{4}-\d{2}-\d{2})(?:[T\s](\d{2}:\d{2}))?/)
  if (m) {
    return m[2] ? `${m[1]}T${m[2]}` : m[1]
  }
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return ''
    const y = d.getFullYear()
    const mo = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    return `${y}-${mo}-${day}T${hh}:${mm}`
  } catch {
    return ''
  }
}

/**
 * Formats a date string in clean 24h format:
 * - With time: "17 Sep, 11:00" or "14 Sep, 16:30"
 * - Date-only (or midnight without explicit time): "17 Sep"
 */
export function formatDate24h(dateStr) {
  if (!dateStr) return ''
  const str = String(dateStr).trim()
  const m = str.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2}))?/)
  const currentYear = new Date().getFullYear()

  if (m) {
    const year = parseInt(m[1], 10)
    const month = MONTH_SHORT[parseInt(m[2], 10) - 1] || m[2]
    const day = parseInt(m[3], 10)
    const yearPart = year !== currentYear ? ` ${year}` : ''

    const isDateOnly =
      !m[4] ||
      (m[4] === '00' && m[5] === '00' && (str.endsWith('00:00:00') || str.endsWith('00:00:00Z') || str.endsWith('00:00:00+00:00')))

    if (isDateOnly) {
      return `${day} ${month}${yearPart}`
    }
    return `${day} ${month}${yearPart}, ${m[4]}:${m[5]}`
  }

  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return String(dateStr)
    const day = d.getDate()
    const month = MONTH_SHORT[d.getMonth()]
    const yearPart = d.getFullYear() !== currentYear ? ` ${d.getFullYear()}` : ''
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    return `${day} ${month}${yearPart}, ${hh}:${mm}`
  } catch {
    return String(dateStr)
  }
}

/**
 * Friendly relative date formatting with 24-hour time:
 * - "Today, 16:15"
 * - "Tomorrow, 14:00"
 * - "Yesterday, 10:30"
 * - "In 2 days, 11:00"
 * - "Overdue by 1 day"
 * - "14 May, 16:30" / "14 May"
 */
export function formatRelativeDate(dateStr, includeTime = false) {
  if (!dateStr) return ''
  try {
    const rawStr = typeof dateStr === 'string' ? dateStr.trim() : ''
    const m = rawStr.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2}))?/)

    const target = new Date(dateStr)
    if (isNaN(target.getTime())) return String(dateStr)

    const now = new Date()
    const targetMidnight = new Date(target.getFullYear(), target.getMonth(), target.getDate())
    const nowMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate())

    const diffDays = Math.round((targetMidnight - nowMidnight) / (1000 * 60 * 60 * 24))

    const isDateOnly =
      /^\d{4}-\d{2}-\d{2}$/.test(rawStr) ||
      !m?.[4] ||
      (m?.[4] === '00' && m?.[5] === '00' && (rawStr.endsWith('00:00:00') || rawStr.endsWith('00:00:00Z') || rawStr.endsWith('00:00:00+00:00')))

    const shouldShowTime = includeTime && !isDateOnly
    const timeStr = m?.[4] && m?.[5] ? `${m[4]}:${m[5]}` : target.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })

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

    const day = target.getDate()
    const month = MONTH_SHORT[target.getMonth()]
    const yearPart = target.getFullYear() !== now.getFullYear() ? ` ${target.getFullYear()}` : ''
    const dateFormatted = `${day} ${month}${yearPart}`

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

