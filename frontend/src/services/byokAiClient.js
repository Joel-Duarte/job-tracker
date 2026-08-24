import { db } from '../db/localDatabase'

export async function getActiveAIProvider() {
  const activeProviders = await db.ai_providers.where('is_active').equals(1).or('is_active').equals(true).toArray()
  if (activeProviders.length > 0) {
    return activeProviders[0]
  }
  const allProviders = await db.ai_providers.toArray()
  return allProviders[0] || null
}

export async function executeBYOKCompletion({ prompt, systemPrompt = '', jsonFormat = false }) {
  const provider = await getActiveAIProvider()
  if (!provider) {
    throw new Error('No active AI provider configured in local mode. Please configure an AI key or local runner endpoint in Settings.')
  }

  const { provider_type, base_url, api_key } = provider
  const cleanBaseUrl = (base_url || '').replace(/\/+$/, '')

  try {
    if (provider_type === 'openai' || provider_type === 'openrouter' || provider_type === 'lm_studio') {
      const url = `${cleanBaseUrl}/chat/completions`
      const headers = { 'Content-Type': 'application/json' }
      if (api_key) {
        headers['Authorization'] = `Bearer ${api_key}`
      }
      const body = {
        model: provider_type === 'openai' ? 'gpt-4o' : 'local-model',
        messages: [
          ...(systemPrompt ? [{ role: 'system', content: systemPrompt }] : []),
          { role: 'user', content: prompt }
        ],
        temperature: 0.7
      }
      if (jsonFormat) {
        body.response_format = { type: 'json_object' }
      }

      const res = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
      })

      if (!res.ok) {
        const errText = await res.text()
        throw new Error(`AI Provider API returned error (${res.status}): ${errText}`)
      }

      const data = await res.json()
      return data.choices?.[0]?.message?.content || ''
    } else if (provider_type === 'ollama') {
      const url = `${cleanBaseUrl}/api/generate`
      const body = {
        model: 'llama3',
        prompt: `${systemPrompt ? systemPrompt + '\n\n' : ''}${prompt}`,
        stream: false,
        json: jsonFormat
      }
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      if (!res.ok) {
        const errText = await res.text()
        throw new Error(`Ollama API error (${res.status}): ${errText}`)
      }
      const data = await res.json()
      return data.response || ''
    } else if (provider_type === 'anthropic') {
      const url = `${cleanBaseUrl || 'https://api.anthropic.com/v1'}/messages`
      const headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key || '',
        'anthropic-version': '2023-06-01',
        'dangerously-allow-browser': 'true'
      }
      const body = {
        model: 'claude-3-5-sonnet-20241022',
        max_tokens: 2048,
        system: systemPrompt,
        messages: [{ role: 'user', content: prompt }]
      }
      const res = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
      })
      if (!res.ok) {
        const errText = await res.text()
        throw new Error(`Anthropic API error (${res.status}): ${errText}`)
      }
      const data = await res.json()
      return data.content?.[0]?.text || ''
    } else {
      throw new Error(`Unsupported AI provider type: ${provider_type}`)
    }
  } catch (err) {
    console.warn('[BYOK AI Fallback Execution]', err.message)
    throw err
  }
}

export async function parseJobDescriptionWithBYOK(rawText) {
  const systemPrompt = `You are a career recruitment extraction tool. Extract structured job details from raw job descriptions into pure JSON with keys: "company_name", "title", "location", "work_model" ("Remote", "Hybrid", "On-site", or "Unknown"), "salary_range", "description", "requirements" (array of strings), "skills" (array of strings).`
  try {
    const rawResult = await executeBYOKCompletion({
      prompt: `Extract structured details from this job description:\n\n${rawText}`,
      systemPrompt,
      jsonFormat: true
    })
    const jsonMatch = rawResult.match(/\{[\s\S]*\}/)
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0])
    }
    return JSON.parse(rawResult)
  } catch (err) {
    // Basic heuristic fallback if no AI key configured
    const lines = rawText.split('\n').map(l => l.trim()).filter(Boolean)
    return {
      company_name: lines[0] || 'Unknown Company',
      title: lines[1] || 'Job Position',
      location: 'Remote',
      work_model: 'Remote',
      salary_range: 'Competitive',
      description: rawText.slice(0, 500),
      requirements: [],
      skills: []
    }
  }
}

export async function generateCoverLetterWithBYOK(appData, candidateProfile, lengthOption = 'standard', customInstructions = '') {
  const systemPrompt = `You are an expert executive cover letter writer. Create a professional cover letter based on the target position and candidate CV.`
  const prompt = `Target Role: ${appData.title} at ${appData.company_name}
Target Description: ${appData.description || 'N/A'}

Candidate Profile:
${candidateProfile?.raw_text || candidateProfile?.full_name || 'Experienced Engineering Leader'}

Length requirement: ${lengthOption}
Custom Instructions: ${customInstructions || 'None'}

Please output only the text of the cover letter.`

  try {
    return await executeBYOKCompletion({ prompt, systemPrompt })
  } catch (err) {
    return `Dear Hiring Manager at ${appData.company_name},\n\nI am writing to express my strong interest in the ${appData.title} role. With my background and passion for building scalable software, I am confident in my ability to bring value to your engineering team.\n\nSincerely,\n${candidateProfile?.full_name || 'Alex Mercer'}`
  }
}

export async function generateInterviewGuideWithBYOK(appData, candidateProfile) {
  const systemPrompt = `You are a technical bar raiser and hiring manager creating an interview preparation guide.`
  const prompt = `Create an interview prep guide for ${appData.title} at ${appData.company_name}.\nCandidate context: ${candidateProfile?.raw_text || 'Senior Engineer'}`

  try {
    return await executeBYOKCompletion({ prompt, systemPrompt })
  } catch (err) {
    return `# Interview Preparation Guide for ${appData.title} at ${appData.company_name}

## 1. Executive Summary & Company Context
- **Company**: ${appData.company_name}
- **Role**: ${appData.title}

## 2. Key Technical Focus Areas
- System Architecture & Scalability
- Core Problem Solving & Code Craft

## 3. High-Yield Behavioral Prep (STAR Method)
- Structure examples focusing on leadership, trade-offs, and measurable business impact.`
  }
}
