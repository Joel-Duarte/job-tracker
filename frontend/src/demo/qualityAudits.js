export function createDemoQualityAudits() {
  const samples = [
    ['COVER_LETTER', true, [], 'Rewritten letter is grounded in the verified CV. Removed the unsupported AWS certification.', true],
    ['COVER_LETTER', false, ['AWS certification is not present in the candidate CV.'], 'Flagged an invented credential; queued an automatic rewrite.', false],
    ['APPLICATION_QA', true, [], 'Answers cite the verified Rust/Kafka pipeline and 38% infrastructure cost reduction.', false],
    ['INTERVIEW_GUIDE', true, [], 'Separates verified experience from practice topics and skill gaps.', false],
  ]
  return samples.map(([task_type, passed, unverified_claims, critique, rewritten], index) => ({
    run_id: `demo_judge_${index + 1}`,
    task_type, passed, unverified_claims, critique, rewritten,
    timestamp: new Date(Date.now() - (index + 1) * 3600000).toISOString(),
  }))
}

export function getDemoQualityStats(audits) {
  const passed = audits.filter(a => a.passed).length
  return {
    total_audits: audits.length,
    passed_audits: passed,
    flagged_audits: audits.length - passed,
    grounding_rate_pct: audits.length ? Math.round(passed / audits.length * 1000) / 10 : 100,
    total_hallucinations_detected: audits.reduce((sum, a) => sum + a.unverified_claims.length, 0),
    auto_rewrites_triggered: audits.filter(a => a.rewritten).length,
    recent_audits: [...audits].sort((a, b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 50),
  }
}
