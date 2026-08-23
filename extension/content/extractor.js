/**
 * Job Tracker Companion Extension - Smart Hybrid DOM Extractor
 * Unified single source of truth extraction engine for popup.js and dock.js.
 */

(function initExtractorEngine() {
  function extractJobData() {
    const url = window.location.href;
    const host = window.location.hostname.toLowerCase();

    function queryFirst(selectors) {
      for (const sel of selectors) {
        try {
          const el = document.querySelector(sel);
          if (el && el.textContent && el.textContent.trim()) {
            return el;
          }
        } catch (e) {}
      }
      return null;
    }

    function queryFirstIn(parent, selectors) {
      if (!parent) return null;
      for (const sel of selectors) {
        try {
          const el = parent.querySelector(sel);
          if (el && el.textContent && el.textContent.trim()) {
            return el;
          }
        } catch (e) {}
      }
      return null;
    }

    function getText(selectors) {
      const el = queryFirst(selectors);
      return el ? el.textContent.trim() : '';
    }

    function getTextIn(parent, selectors) {
      const el = queryFirstIn(parent, selectors);
      return el ? el.textContent.trim() : '';
    }

    function extractSalaryFromText(text) {
      if (!text) return '';
      const salaryRegex = /(?:[\$€£]\s?\d{2,3}(?:,\d{3})*(?:\s?-\s?[\$€£]?\s?\d{2,3}(?:,\d{3})*)?|\b\d{2,3}k\s?-\s?\b\d{2,3}k\b)(?:\s?\/(?:yr|year|hr|hour|mo|month))?/i;
      const match = text.match(salaryRegex);
      return match ? match[0].trim() : '';
    }

    function detectWorkModel(text) {
      if (!text) return 'Unknown';
      const low = text.toLowerCase();
      if (low.includes('hybrid')) return 'Hybrid';
      if (low.includes('remote') || low.includes('work from home') || low.includes('telecommute')) return 'Remote';
      if (low.includes('on-site') || low.includes('onsite') || low.includes('in-office') || low.includes('in office')) return 'On-site';
      return 'Unknown';
    }

    function convertNodeToText(node) {
      if (!node) return '';

      const clone = node.cloneNode(true);
      const dropTags = ['script', 'style', 'noscript', 'nav', 'header', 'footer', 'svg', 'form', 'button', 'iframe'];
      dropTags.forEach((tag) => {
        clone.querySelectorAll(tag).forEach((el) => el.remove());
      });

      clone.querySelectorAll('li').forEach((li) => {
        li.textContent = `• ${li.textContent.trim()}\n`;
      });

      clone.querySelectorAll('h1, h2, h3, h4, h5, h6, p, div, br').forEach((block) => {
        block.after(document.createTextNode('\n'));
      });

      const lines = clone.textContent
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0);

      return lines.join('\n');
    }

    function deriveCompanyFromTitle() {
      const docTitle = document.title || '';
      const ogTitle = document.querySelector('meta[property="og:title"]')?.content || '';
      const ogSite = document.querySelector('meta[property="og:site_name"]')?.content || '';

      if (ogSite) return ogSite.trim();

      const titleStr = ogTitle || docTitle;
      const separators = [' at ', ' | ', ' - ', ' — ', ' • '];
      for (const sep of separators) {
        if (titleStr.includes(sep)) {
          const parts = titleStr.split(sep);
          if (parts.length >= 2) {
            return parts[parts.length - 1].replace(/careers|jobs|hiring/gi, '').trim();
          }
        }
      }
      return '';
    }

    function deriveTitleFromDoc() {
      const ogTitle = document.querySelector('meta[property="og:title"]')?.content || '';
      const docTitle = document.title || '';
      const raw = ogTitle || docTitle;

      const separators = [' at ', ' | ', ' - ', ' — ', ' • '];
      for (const sep of separators) {
        if (raw.includes(sep)) {
          return raw.split(sep)[0].trim();
        }
      }
      return raw.replace(/careers|jobs|hiring/gi, '').trim();
    }

    let site_type = 'GENERIC';
    let title = '';
    let company = '';
    let location = '';
    let salary = '';
    let description_text = '';
    let raw_html_snippet = '';

    // --- Tier 1: Site-Specific High Precision Extraction Rules ---

    // 1. Glassdoor
    if (host.includes('glassdoor.com') || host.includes('glassdoor.co.uk')) {
      site_type = 'GLASSDOOR';
      title = getText(['[data-test="job-title"]', 'h1.JobDetails_jobTitle__', '.job-title', 'h1']);
      company = getText(['[data-test="employer-name"]', '.JobDetails_employerName__', '.employer-name']);
      location = getText(['[data-test="location"]', '.JobDetails_location__', '.location']);
      salary = getText(['[data-test="detailSalary"]', '[data-test="salaries"]']);

      const descEl = queryFirst(['#JobDescriptionContainer', '.JobDetails_jobDescription__', '[data-test="jobDescription"]']);
      if (descEl) {
        description_text = convertNodeToText(descEl);
        raw_html_snippet = descEl.innerHTML;
      }
    }

    // 2. Indeed (Scoped strictly inside view pane)
    else if (host.includes('indeed.com')) {
      site_type = 'INDEED';
      const pane = queryFirst(['#jobsearch-ViewjobPaneWrapper', '#jobsearch-JobComponent']) || document;
      title = getTextIn(pane, ['h1.jobsearch-JobInfoHeader-title', '[data-testid="simpler-jobTitle"]', '[data-testid="jobsearch-JobInfoHeader-title"]', 'h1']);
      company = getTextIn(pane, ['[data-testid="inlineHeader-companyName"]', '.jobsearch-CompanyReview-companyHeader']);
      location = getTextIn(pane, ['[data-testid="inlineHeader-companyLocation"]', '[data-testid="job-location"]']);
      salary = getTextIn(pane, ['#salaryInfoAndJobType', '[data-testid="jobsearch-OtherJobDetailsContainer"]']);

      const descEl = queryFirstIn(pane, ['#jobDescriptionText']);
      if (descEl) {
        description_text = convertNodeToText(descEl);
        raw_html_snippet = descEl.innerHTML;
      }
    }

    // 3. LinkedIn (Scoped strictly inside job details pane)
    else if (host.includes('linkedin.com')) {
      site_type = 'LINKEDIN';
      const pane = queryFirst(['.jobs-search__job-details', '#job-details', '.job-view-layout']) || document;
      title = getTextIn(pane, ['.job-details-jobs-unified-top-card__job-title', '.top-card-layout__title', 'h1.t-24', 'h1']);
      company = getTextIn(pane, ['.job-details-jobs-unified-top-card__company-name', '.topcard__org-name-link', '.job-details-jobs-unified-top-card__primary-description a']);
      location = getTextIn(pane, [
        '.job-details-jobs-unified-top-card__primary-description-container span.tvm__text',
        '.job-details-jobs-unified-top-card__bullet',
        '.jobs-unified-top-card__bullet',
        '.topcard__flavor--bullet'
      ]);

      if (!location) {
        const primaryDesc = getTextIn(pane, ['.job-details-jobs-unified-top-card__primary-description', '.job-details-jobs-unified-top-card__primary-description-container']);
        if (primaryDesc) {
          const parts = primaryDesc.split('·').map((p) => p.trim());
          if (parts.length >= 2) {
            location = parts[1];
          }
        }
      }

      const descEl = queryFirstIn(pane, ['#job-details', '.jobs-description__content']);
      if (descEl) {
        description_text = convertNodeToText(descEl);
        raw_html_snippet = descEl.innerHTML;
      }
    }

    // 4. Greenhouse
    else if (host.includes('greenhouse.io') || host.includes('boards.greenhouse.io')) {
      site_type = 'GREENHOUSE';
      title = getText(['.app-title', '#header .title', 'h1.heading', 'h1']);
      company = getText(['.company-name', '#header .company-name']);
      location = getText(['.location']);

      const descEl = queryFirst(['#content', '#main-content', '#app-body', '.job-post']);
      if (descEl) {
        description_text = convertNodeToText(descEl);
        raw_html_snippet = descEl.innerHTML;
      }
    }

    // 5. Lever
    else if (host.includes('lever.co') || host.includes('jobs.lever.co')) {
      site_type = 'LEVER';
      title = getText(['.posting-headline h2', '.posting-header h2', 'h2']);
      company = document.querySelector('.main-header-logo img')?.getAttribute('alt') || deriveCompanyFromTitle();
      location = getText(['.posting-categories .location', '.sort-by-location', '.location']);

      const descEl = queryFirst(['.section-page', '.content', '[data-qa="job-description"]']);
      if (descEl) {
        description_text = convertNodeToText(descEl);
        raw_html_snippet = descEl.innerHTML;
      }
    }

    // 6. Workday
    else if (host.includes('myworkdayjobs.com') || host.includes('workday.com')) {
      site_type = 'WORKDAY';
      title = getText(['[data-automation-id="jobPostingHeader"]', 'h2[data-automation-id="jobTitle"]', 'h1']);
      company = getText(['[data-automation-id="companyName"]']) || deriveCompanyFromTitle();
      location = getText(['[data-automation-id="locations"]', '[data-automation-id="jobPostingLocation"]']);

      const descEl = queryFirst(['[data-automation-id="jobPostingDescription"]']);
      if (descEl) {
        description_text = convertNodeToText(descEl);
        raw_html_snippet = descEl.innerHTML;
      }
    }

    // 7. Ashby
    else if (host.includes('ashbyhq.com') || host.includes('jobs.ashbyhq.com')) {
      site_type = 'ASHBY';
      title = getText(['h1', '[class*="heading"]']);
      company = getText(['[class*="company"]']) || deriveCompanyFromTitle();

      const descEl = queryFirst(['[class*="description"]', '[class*="job-posting"]']);
      if (descEl) {
        description_text = convertNodeToText(descEl);
        raw_html_snippet = descEl.innerHTML;
      }
    }

    // --- Tier 2: Universal Fallback Parser ---
    if (!description_text || description_text.length < 50) {
      if (site_type === 'GENERIC') {
        site_type = 'GENERIC';
      }

      if (!title) {
        title = getText(['h1', 'h2']) || deriveTitleFromDoc();
      }
      if (!company) {
        company = deriveCompanyFromTitle();
      }

      const container = queryFirst([
        'article',
        'main',
        '[role="main"]',
        '#job-description',
        '#description',
        '.job-description',
        '.description',
        '.content',
        'body'
      ]) || document.body;

      description_text = convertNodeToText(container);
      raw_html_snippet = container.innerHTML;
    }

    if (!title) {
      title = deriveTitleFromDoc() || 'Unknown Role';
    }
    if (!company) {
      company = deriveCompanyFromTitle() || 'Unknown Company';
    }

    if (!salary) {
      salary = extractSalaryFromText(description_text);
    }

    const work_model = detectWorkModel(`${location} ${description_text}`);

    return {
      url,
      title,
      company,
      location,
      salary,
      work_model,
      description_text: description_text.substring(0, 30000),
      raw_html_snippet: raw_html_snippet ? raw_html_snippet.substring(0, 15000) : '',
      site_type,
      extracted_at: new Date().toISOString()
    };
  }

  // Assign globally as window.__JOB_TRACKER_EXTRACT__
  window.__JOB_TRACKER_EXTRACT__ = extractJobData;

  // Immediately execute and return when injected directly
  return extractJobData();
})();
