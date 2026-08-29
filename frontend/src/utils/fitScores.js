/**
 * Helper to extract computed (programmatic) fit score and AI fit score from an application object, task, or result payload.
 *
 * @param {Object} obj Application object, intake evaluation task, or result JSON payload
 * @returns {{ computedScore: number|null, aiScore: number|null, computedText: string, aiText: string }}
 */
export function getFitScores(obj) {
  if (!obj) {
    return { computedScore: null, aiScore: null, computedText: '--%', aiText: '--%' }
  }

  // Extract payload if obj is an Application record, Task, or raw result payload
  const payload = obj.match_analysis_payload || obj.result_json || obj.raw_payload || obj

  // 1. Computed / Programmatic Overlap Score
  let computedVal = null
  if (obj.programmatic_match_score !== undefined && obj.programmatic_match_score !== null) {
    computedVal = Number(obj.programmatic_match_score)
  } else if (payload.programmatic_match_score !== undefined && payload.programmatic_match_score !== null) {
    computedVal = Number(payload.programmatic_match_score)
  } else if (payload.programmatic_score !== undefined && payload.programmatic_score !== null) {
    computedVal = Number(payload.programmatic_score)
  } else if (payload.programmatic_baseline !== undefined && payload.programmatic_baseline !== null) {
    computedVal = Number(payload.programmatic_baseline)
  }

  // 2. AI Qualitative Fit Score (fit_score / match_score)
  let aiVal = null
  if (obj.fit_score !== undefined && obj.fit_score !== null) {
    aiVal = Number(obj.fit_score)
  } else if (obj.match_score !== undefined && obj.match_score !== null) {
    aiVal = Number(obj.match_score)
  } else if (payload.fit_score !== undefined && payload.fit_score !== null) {
    aiVal = Number(payload.fit_score)
  } else if (payload.match_score !== undefined && payload.match_score !== null) {
    aiVal = Number(payload.match_score)
  } else if (payload.overall_fit_score !== undefined && payload.overall_fit_score !== null) {
    aiVal = Number(payload.overall_fit_score)
  }

  // 3. Matched and Total Skills Counts
  let matchedCount = null
  let totalCount = null

  if (obj.matched_skills_count !== undefined && obj.matched_skills_count !== null) {
    matchedCount = Number(obj.matched_skills_count)
  } else if (payload.matched_skills_count !== undefined && payload.matched_skills_count !== null) {
    matchedCount = Number(payload.matched_skills_count)
  } else if (Array.isArray(payload.matching_skills)) {
    matchedCount = payload.matching_skills.length
  }

  if (obj.total_required_skills_count !== undefined && obj.total_required_skills_count !== null) {
    totalCount = Number(obj.total_required_skills_count)
  } else if (payload.total_required_skills_count !== undefined && payload.total_required_skills_count !== null) {
    totalCount = Number(payload.total_required_skills_count)
  } else if (Array.isArray(payload.matching_skills) || Array.isArray(payload.missing_skills)) {
    const matchingLen = Array.isArray(payload.matching_skills) ? payload.matching_skills.length : 0
    const missingLen = Array.isArray(payload.missing_skills) ? payload.missing_skills.length : 0
    if (matchingLen + missingLen > 0) {
      totalCount = matchingLen + missingLen
    }
  }

  let ratioText = ''
  if (matchedCount !== null && totalCount !== null && totalCount > 0) {
    ratioText = `${matchedCount}/${totalCount} skills`
  } else if (totalCount === 0) {
    ratioText = '0 skills required'
  }

  return {
    computedScore: computedVal,
    aiScore: aiVal,
    matchedCount,
    totalCount,
    computedRatioText: ratioText,
    computedText: computedVal !== null ? `${computedVal}%` : '--%',
    aiText: aiVal !== null ? `${aiVal}%` : '--%',
  }
}
