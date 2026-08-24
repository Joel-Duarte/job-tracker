/**
 * Fuzzy matching utility for application search, company matching, and text filtering.
 */

/**
 * Calculates Levenshtein edit distance between two strings.
 */
export function levenshteinDistance(s1, s2) {
  if (!s1) return s2 ? s2.length : 0
  if (!s2) return s1 ? s1.length : 0

  const m = s1.length
  const n = s2.length
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))

  for (let i = 0; i <= m; i++) dp[i][0] = i
  for (let j = 0; j <= n; j++) dp[0][j] = j

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (s1[i - 1] === s2[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1]
      } else {
        dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
      }
    }
  }
  return dp[m][n]
}

/**
 * Calculates normalized string similarity (0.0 to 1.0) using Levenshtein distance.
 */
export function stringSimilarity(s1, s2) {
  if (!s1 && !s2) return 1.0
  if (!s1 || !s2) return 0.0

  const str1 = s1.toLowerCase().trim()
  const str2 = s2.toLowerCase().trim()

  if (str1 === str2) return 1.0

  const longer = str1.length > str2.length ? str1 : str2
  const shorter = str1.length > str2.length ? str2 : str1
  if (longer.length === 0) return 1.0

  const distance = levenshteinDistance(str1, str2)
  return Math.max(0, (longer.length - distance) / longer.length)
}

/**
 * Calculates a fuzzy match score between a query string and a target string.
 * Returns a number between 0.0 (no match) and 1.0 (exact match).
 */
export function fuzzyScore(query, target) {
  if (!query || !target) return 0.0

  const q = query.toLowerCase().trim()
  const t = target.toLowerCase().trim()

  if (q === t) return 1.0

  // Exact substring match
  if (t.includes(q)) {
    const isPrefix = t.startsWith(q)
    return isPrefix ? 0.95 : 0.85
  }

  // Token-based matching (e.g. "Stripe Engineer" matching "Stripe" + "Software Engineer")
  const qTokens = q.split(/\s+/).filter(Boolean)
  const tTokens = t.split(/\s+/).filter(Boolean)

  if (qTokens.length > 1) {
    let tokenScoreSum = 0
    for (const qTok of qTokens) {
      if (t.includes(qTok)) {
        tokenScoreSum += 1.0
      } else {
        let bestTokScore = 0
        for (const tTok of tTokens) {
          const sim = stringSimilarity(qTok, tTok)
          if (sim > bestTokScore) bestTokScore = sim
        }
        if (bestTokScore >= 0.6) {
          tokenScoreSum += bestTokScore
        }
      }
    }
    const tokenScore = tokenScoreSum / qTokens.length
    if (tokenScore >= 0.4) {
      return 0.5 + tokenScore * 0.35
    }
  }

  // Subsequence / Acronym matching (e.g. "sre" in "Site Reliability Engineer")
  let qIdx = 0
  let consecutiveBonus = 0
  let prevMatchIdx = -1

  for (let i = 0; i < t.length && qIdx < q.length; i++) {
    if (t[i] === q[qIdx]) {
      if (prevMatchIdx === i - 1) consecutiveBonus++
      prevMatchIdx = i
      qIdx++
    }
  }

  if (qIdx === q.length) {
    const ratio = q.length / t.length
    const bonus = consecutiveBonus / (t.length || 1)
    const subseqScore = 0.45 + ratio * 0.25 + bonus * 0.2
    return Math.min(subseqScore, 0.8)
  }

  // Fallback to overall string edit distance similarity
  const sim = stringSimilarity(q, t)
  return sim >= 0.45 ? sim * 0.75 : 0.0
}

/**
 * Scores an application record against a search query across company name, position, and domain.
 */
export function scoreApplicationMatch(app, query) {
  if (!query || !query.trim()) return 1.0
  const q = query.trim()

  const companyName = app.company?.name || ''
  const companyDomain = app.company?.domain || ''
  const position = app.position || ''
  const combined = `${companyName} ${position} ${companyDomain}`

  const companyScore = fuzzyScore(q, companyName)
  const positionScore = fuzzyScore(q, position)
  const combinedScore = fuzzyScore(q, combined)

  return Math.max(companyScore * 1.15, positionScore * 1.05, combinedScore)
}

/**
 * Filters and ranks applications by fuzzy match score against query.
 */
export function fuzzyFilterApplications(apps, query, minScore = 0.25) {
  if (!apps || !apps.length) return []
  if (!query || !query.trim()) return apps

  const scored = apps.map((app) => ({
    app,
    score: scoreApplicationMatch(app, query),
  }))

  return scored
    .filter((item) => item.score >= minScore)
    .sort((a, b) => b.score - a.score)
    .map((item) => item.app)
}
