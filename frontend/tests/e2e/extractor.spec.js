import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const EXTRACTOR_PATH = path.resolve(__dirname, '../../../extension/content/extractor.js')
const EXTRACTOR_SCRIPT = fs.readFileSync(EXTRACTOR_PATH, 'utf8')

/**
 * Serves a sanitized HTML fixture at the given URL (without hitting external networks)
 * and executes the extension's DOM extractor directly in Chromium.
 */
async function runExtractor(page, targetUrl, html) {
  await page.route('**/*', (route) => {
    if (route.request().url() === targetUrl) {
      return route.fulfill({
        status: 200,
        contentType: 'text/html; charset=utf-8',
        body: html,
      })
    }
    return route.abort()
  })

  await page.goto(targetUrl, { waitUntil: 'domcontentloaded' })
  return page.evaluate((script) => {
    // eslint-disable-next-line no-eval
    return eval(script)
  }, EXTRACTOR_SCRIPT)
}

test.describe('Extension DOM Extractor (extractor.js)', () => {
  test('Tier 1: LinkedIn extracts title, company, location, canonical URL, and JD', async ({ page }) => {
    const url = 'https://www.linkedin.com/jobs/view/9876543210/?trk=public_jobs'
    const html = `<!DOCTYPE html>
      <html>
        <head><title>(3) Staff Backend Engineer | LinkedIn</title></head>
        <body>
          <div class="job-view-layout">
            <div class="job-details-jobs-unified-top-card__job-title">
              <h1>(3) Staff Backend Engineer</h1>
            </div>
            <div class="job-details-jobs-unified-top-card__company-name">
              <a href="/company/acme/">Acme Cloud</a>
            </div>
            <div class="job-details-jobs-unified-top-card__primary-description-container">
              <span class="tvm__text">Lisbon, Portugal</span>
              <span class="job-details-jobs-unified-top-card__workplace-type">Hybrid</span>
            </div>
            <div id="job-details" class="jobs-description__content">
              <p>About the role: Design distributed systems in Python and PostgreSQL.</p>
              <ul>
                <li>5+ years backend engineering</li>
                <li>Strong experience with FastAPI and async architectures</li>
              </ul>
            </div>
          </div>
        </body>
      </html>`

    const res = await runExtractor(page, url, html)
    expect(res.site_type).toBe('LINKEDIN')
    expect(res.url).toBe('https://www.linkedin.com/jobs/view/9876543210/')
    expect(res.title).toBe('Staff Backend Engineer')
    expect(res.company).toBe('Acme Cloud')
    expect(res.location).toContain('Lisbon, Portugal')
    expect(res.location).toContain('Hybrid')
    expect(res.work_model).toBe('Hybrid')
    expect(res.description_text).toContain('Design distributed systems in Python and PostgreSQL')
    expect(res.description_text).toContain('Strong experience with FastAPI')
  })

  test('Tier 1: Glassdoor strips star ratings from company name and extracts scoped JD', async ({ page }) => {
    const url = 'https://www.glassdoor.com/job-listing/staff-ai-engineer-JV_KO0,17.htm?jl=4455667788'
    const html = `<!DOCTYPE html>
      <html>
        <head><title>Staff AI Engineer - NovaTech | Glassdoor</title></head>
        <body>
          <div data-test="job-details">
            <header>
              <div data-test="employer-name">NovaTech <span class="rating">4.4 ★</span></div>
              <h1 data-test="job-title">Staff AI Engineer</h1>
              <div data-test="location">Remote</div>
              <div data-test="detailSalary">$180,000 - $220,000</div>
            </header>
            <div id="JobDescriptionContainer">
              <p>Build production LLM agents and retrieval pipelines.</p>
              <p>Requirements: Python, PyTorch, pgvector, and Kubernetes.</p>
            </div>
          </div>
        </body>
      </html>`

    const res = await runExtractor(page, url, html)
    expect(res.site_type).toBe('GLASSDOOR')
    expect(res.url).toBe('https://www.glassdoor.com/job-listing/?jl=4455667788')
    expect(res.company).toBe('NovaTech')
    expect(res.title).toBe('Staff AI Engineer')
    expect(res.location).toBe('Remote')
    expect(res.salary).toBe('$180,000 - $220,000')
    expect(res.description_text).toContain('Build production LLM agents')
  })

  test('Tier 1: Indeed extracts scoped job pane and canonical viewjob URL', async ({ page }) => {
    const url = 'https://www.indeed.com/jobs?q=python&vjk=abc123def'
    const html = `<!DOCTYPE html>
      <html>
        <body>
          <div id="jobsearch-ViewjobPaneWrapper">
            <h1 data-testid="jobsearch-JobInfoHeader-title">Platform Engineer</h1>
            <div data-testid="inlineHeader-companyName">DataScale</div>
            <div data-testid="inlineHeader-companyLocation">Porto, Portugal</div>
            <div id="salaryInfoAndJobType">€70,000 - €90,000</div>
            <div id="jobDescriptionText">
              <p>Own cloud infrastructure, Terraform modules, and observability.</p>
              <p>Requirements: AWS, Kubernetes, Go, and Python.</p>
            </div>
          </div>
        </body>
      </html>`

    const res = await runExtractor(page, url, html)
    expect(res.site_type).toBe('INDEED')
    expect(res.url).toBe('https://www.indeed.com/viewjob?jk=abc123def')
    expect(res.title).toBe('Platform Engineer')
    expect(res.company).toBe('DataScale')
    expect(res.location).toBe('Porto, Portugal')
    expect(res.description_text).toContain('Own cloud infrastructure')
  })

  test('Tier 1: Greenhouse and Workday extract ATS-specific fields', async ({ page }) => {
    const ghUrl = 'https://boards.greenhouse.io/examplecorp/jobs/123456?utm_source=linkedin'
    const ghHtml = `<!DOCTYPE html>
      <html>
        <body>
          <div id="header">
            <h1 class="app-title">Senior Data Engineer</h1>
            <span class="company-name">ExampleCorp</span>
            <div class="location">Berlin, Germany</div>
          </div>
          <div id="content">
            <p>We are hiring a Senior Data Engineer to build streaming pipelines with Kafka and Spark.</p>
          </div>
        </body>
      </html>`

    const ghRes = await runExtractor(page, ghUrl, ghHtml)
    expect(ghRes.site_type).toBe('GREENHOUSE')
    expect(ghRes.url).toBe('https://boards.greenhouse.io/examplecorp/jobs/123456')
    expect(ghRes.title).toBe('Senior Data Engineer')
    expect(ghRes.company).toBe('ExampleCorp')
    expect(ghRes.location).toBe('Berlin, Germany')
    expect(ghRes.description_text).toContain('streaming pipelines with Kafka and Spark')

    const wdUrl = 'https://example.wd5.myworkdayjobs.com/en-US/Careers/job/Lisbon/AI-Lead_JR100'
    const wdHtml = `<!DOCTYPE html>
      <html>
        <head><title>AI Lead - ExampleGlobal</title></head>
        <body>
          <h2 data-automation-id="jobPostingHeader">AI Lead</h2>
          <div data-automation-id="companyName">ExampleGlobal</div>
          <div data-automation-id="locations">Lisbon</div>
          <div data-automation-id="jobPostingDescription">
            <p>Lead enterprise AI transformation initiatives across Europe.</p>
            <p>Requirements: LLMs, Python, MLOps, and stakeholder management.</p>
          </div>
        </body>
      </html>`

    const wdRes = await runExtractor(page, wdUrl, wdHtml)
    expect(wdRes.site_type).toBe('WORKDAY')
    expect(wdRes.title).toBe('AI Lead')
    expect(wdRes.company).toBe('ExampleGlobal')
    expect(wdRes.location).toBe('Lisbon')
    expect(wdRes.description_text).toContain('Lead enterprise AI transformation initiatives')
  })

  test('Tier 2 (GENERIC): skips tiny promo <article> before <main> and extracts full .description (BNP Paribas pattern)', async ({ page }) => {
    const url = 'https://group.bnpparibas/en/careers/job-offer/primary-markets-full-stack-ai-transformation-engineer?src=JB-10800'
    const fullJdParagraph =
      'Primary Markets AI Transformation Engineer: design and ship full-stack GenAI and Python applications for capital markets teams. '
    const html = `<!DOCTYPE html>
      <html>
        <head>
          <title>Job offer Primary Markets - Full Stack AI Transformation Engineer - BNP Paribas</title>
        </head>
        <body>
          <article class="faq-promo">
            <p>Check out our FAQ page</p>
            <p>See the page</p>
          </article>
          <main id="main">
            <h1 class="title-1">Primary Markets - Full Stack AI Transformation Engineer</h1>
            <div class="ct-text">
              <div class="description">
                <h2>About the Job</h2>
                <p>${fullJdParagraph.repeat(6)}</p>
                <ul>
                  <li>Python, FastAPI, Vue 3 / TypeScript</li>
                  <li>Hybrid working model in Lisbon</li>
                </ul>
              </div>
            </div>
          </main>
          <article class="card-custom card-offer">
            <h3>Similar Job</h3>
            <p>Apply now</p>
          </article>
        </body>
      </html>`

    const res = await runExtractor(page, url, html)
    expect(res.site_type).toBe('GENERIC')
    expect(res.title).toBe('Primary Markets - Full Stack AI Transformation Engineer')
    expect(res.company).toBe('BNP Paribas')
    expect(res.description_text.length).toBeGreaterThan(500)
    expect(res.description_text).toContain('design and ship full-stack GenAI and Python applications')
    expect(res.description_text).not.toBe('Check out our FAQ page\nSee the page')
  })

  test('Tier 2 (GENERIC): skips metadata-only first <article> and cookie modal <h1> (Siemens pattern)', async ({ page }) => {
    const url = 'https://jobs.siemens.com/pt_PT/externaljobs/JobDetail/528770'
    const fullJdParagraph =
      'At Siemens, we build technology solutions to shape the world we live in. Responsibilities include architecting AI agents, Python services, and cloud deployments. '
    const html = `<!DOCTYPE html>
      <html>
        <head>
          <title>Senior AI Forward Deployed Engineer (FDE) (m/f/d) - Job Detail | Careers Marketplace - Siemens</title>
        </head>
        <body>
          <div role="dialog" aria-modal="true" id="onetrust-consent-sdk">
            <h1>We value your privacy</h1>
            <p>Accept cookies to continue.</p>
          </div>
          <main id="main">
            <h3>Senior AI Forward Deployed Engineer (FDE) (m/f/d)</h3>
            <article class="article article--details regular-fields--cols-2Z">
              <p>ID da vaga 528770</p>
              <p>Publicado desde 13-Nov-2026</p>
              <p>Empresa Siemens S.A.</p>
              <p>Modo de trabalho Híbrido (remoto/escritório)</p>
              <p>Localização Amadora - Lisboa - Portugal</p>
            </article>
            <article class="article article--details">
              <div id="section1__content" class="article__content">
                <p>${fullJdParagraph.repeat(6)}</p>
              </div>
            </article>
          </main>
        </body>
      </html>`

    const res = await runExtractor(page, url, html)
    expect(res.site_type).toBe('GENERIC')
    expect(res.title).toContain('Senior AI Forward Deployed Engineer (FDE) (m/f/d)')
    expect(res.title).not.toBe('We value your privacy')
    expect(res.company).toContain('Siemens')
    expect(res.description_text).toContain('ID da vaga 528770')
    expect(res.description_text.length).toBeGreaterThan(800)
    expect(res.description_text).toContain('architecting AI agents, Python services')
    expect(res.description_text).not.toContain('We value your privacy')
  })

  test('Tier 2 (GENERIC): falls back to document.body while stripping nav, footer, and dock host', async ({ page }) => {
    const url = 'https://careers.customstartup.io/roles/ml-engineer'
    const html = `<!DOCTYPE html>
      <html>
        <head><title>ML Engineer - CustomStartup</title></head>
        <body>
          <nav>Home | Careers | Blog</nav>
          <div class="custom-layout">
            <h1>ML Engineer</h1>
            <p>${'Build scalable ML inference pipelines in Python and Rust. '.repeat(8)}</p>
          </div>
          <footer>Copyright CustomStartup</footer>
          <div id="job-tracker-dock-host">Dock Overlay Text</div>
        </body>
      </html>`

    const res = await runExtractor(page, url, html)
    expect(res.site_type).toBe('GENERIC')
    expect(res.title).toBe('ML Engineer')
    expect(res.company).toBe('CustomStartup')
    expect(res.description_text).toContain('Build scalable ML inference pipelines')
    expect(res.description_text).not.toContain('Copyright CustomStartup')
    expect(res.description_text).not.toContain('Dock Overlay Text')
  })

  test('Tier 2 (GENERIC): returns short description_text on non-JD page so backend guardrail triggers', async ({ page }) => {
    const url = 'https://example.com/faq'
    const html = `<!DOCTYPE html>
      <html>
        <head><title>FAQ - Example</title></head>
        <body>
          <article>
            <p>Check out our FAQ page</p>
            <p>See the page</p>
          </article>
        </body>
      </html>`

    const res = await runExtractor(page, url, html)
    expect(res.site_type).toBe('GENERIC')
    expect(res.description_text.length).toBeLessThan(100)
  })
})
