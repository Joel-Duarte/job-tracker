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

  return {
    computedScore: computedVal,
    aiScore: aiVal,
    computedText: computedVal !== null ? `${computedVal}%` : '--%',
    aiText: aiVal !== null ? `${aiVal}%` : '--%',
  }
}
