/**
 * Job Tracker Companion Extension - Smart Hybrid DOM Extractor
 * Unified single source of truth extraction engine for popup.js and dock.js.
 */

(function initExtractorEngine() {
  const BLACKLISTED_PORTALS = ['linkedin', 'glassdoor', 'indeed', 'job posting', 'careers'];

  function extractJobData() {
    const rawUrl = window.location.href;
    const host = window.location.hostname.toLowerCase();
    const url = resolveCanonicalJobUrl(host, rawUrl);

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
      const docTitle = (document.title || '').replace(/^\(\d+\)\s*/, '');
      const ogTitle = (document.querySelector('meta[property="og:title"]')?.content || '').replace(/^\(\d+\)\s*/, '');
      const ogSite = document.querySelector('meta[property="og:site_name"]')?.content || '';

      if (ogSite && !BLACKLISTED_PORTALS.includes(ogSite.toLowerCase().trim())) {
        return ogSite.trim();
      }

      const titleStr = ogTitle || docTitle;
      const separators = [' at ', ' | ', ' - ', ' — ', ' • '];
      for (const sep of separators) {
        if (titleStr.includes(sep)) {
          const parts = titleStr.split(sep);
          if (parts.length >= 2) {
            const candidate = parts[parts.length - 1].replace(/careers|jobs|hiring/gi, '').trim();
            if (candidate && !BLACKLISTED_PORTALS.includes(candidate.toLowerCase())) {
              return candidate;
            }
          }
        }
      }
      return '';
    }

    function deriveTitleFromDoc() {
      let raw = document.querySelector('meta[property="og:title"]')?.content || document.title || '';
      raw = raw.replace(/^\(\d+\)\s*/, '');
      raw = raw.replace(/\s*\|\s*LinkedIn.*$/i, '');
      raw = raw.replace(/\s*\|\s*Glassdoor.*$/i, '');
      raw = raw.replace(/\s*\|\s*Indeed.*$/i, '');
      for (const sep of [' at ', ' | ', ' - ', ' — ', ' • ']) {
        if (raw.includes(sep)) {
          return raw.split(sep)[0].trim();
        }
      }
      return raw.trim().replace(/careers|jobs|hiring/gi, '').trim();
    }

    let site_type = 'GENERIC';
    let title = '';
    let company = '';
    let location = '';
    let salary = '';
    let description_text = '';
    let raw_html_snippet = '';

    // --- Tier 1: Site-Specific High Precision Extraction Rules ---

    // 1. Glassdoor (Wildcard Header Scoping + Star Rating Cleanup)
    if (host.includes('glassdoor.com') || host.includes('glassdoor.co.uk')) {
      site_type = 'GLASSDOOR';
      const descContainer = document.querySelector('#JobDescriptionContainer');
      const detailPane = descContainer?.closest('[class*="JobDetails"], [data-test="job-details"], article, main') ||
                         document.querySelector('[data-test="job-details"], div[class*="JobDetails_jobDetailsContainer"], div[class*="JobDetails_jobDetails"]') ||
                         document;

      const header = queryFirstIn(detailPane, [
        '[class*="JobDetails_jobDetailsHeader"]',
        '[class*="StickyScrollSection_stickyHeader"]',
        '[class*="JobDetails_header"]',
        'header'
      ]) || detailPane;

      const employerEl = queryFirstIn(header, [
        '[data-test="employer-name"]',
        'a[href*="/Overview/"]',
        '[class*="employerName" i]',
        '[class*="EmployerName" i]',
        '[class*="JobDetails_employerName"]',
        'h4',
        'div:first-child p',
        'div:first-child a',
        'div:first-child'
      ]);

      if (employerEl) {
        const clone = employerEl.cloneNode(true);
        clone.querySelectorAll('[class*="rating" i], [data-test="rating"], [class*="star" i], [class*="review" i]').forEach((el) => el.remove());
        company = clone.textContent.trim();
      }

      company = company
        .replace(/\s*★.*$/, '')
        .replace(/\s+\d+(\.\d+)?(\s*★)?\s*$/, '')
        .replace(/\b\d\.\d\b/g, '')
        .replace(/[\r\n\t]+/g, ' ')
        .trim();

      title = getTextIn(header, [
        '[data-test="job-title"]',
        'h1[class*="JobDetails_jobTitle"]',
        'h1[class*="jobTitle" i]',
        'h1',
        'h2'
      ]);

      location = getTextIn(header, [
        '[data-test="location"]',
        '[class*="JobDetails_location"]',
        '[class*="location" i]',
        'div:nth-child(3)',
        'span[class*="location"]'
      ]);

      salary = getTextIn(header, [
        '[data-test="detailSalary"]',
        '[data-test="salaries"]'
      ]);

      const descEl = queryFirstIn(detailPane, ['#JobDescriptionContainer', '.JobDetails_jobDescription__', '[data-test="jobDescription"]']);
      if (descEl) {
        description_text = convertNodeToText(descEl);
        raw_html_snippet = descEl.innerHTML;
      }
    }

    // 2. Indeed (Scoped strictly inside view pane)
    else if (host.includes('indeed.com')) {
      site_type = 'INDEED';
      const pane = queryFirst(['#jobsearch-ViewjobPaneWrapper', '.jobsearch-JobComponent', 'main']) || document;
      title = getTextIn(pane, ['h1.jobsearch-JobInfoHeader-title', '[data-testid="simpler-jobTitle"]', '[data-testid="jobsearch-JobInfoHeader-title"]', 'h1']);
      company = getTextIn(pane, ['[data-testid="inlineHeader-companyName"]', '.jobsearch-CompanyReview-companyHeader']);
      location = getTextIn(pane, [
        '[data-testid="inlineHeader-companyLocation"]',
        'div[data-testid="job-location"]',
        '#jobLocationText',
        '.jobsearch-JobInfoHeader-companyLocation',
        '.jobsearch-CompanyInfoContainer div'
      ]);
      salary = getTextIn(pane, ['#salaryInfoAndJobType', '[data-testid="jobsearch-OtherJobDetailsContainer"]']);

      const descEl = queryFirstIn(pane, ['#jobDescriptionText', '.jobsearch-JobComponent-description']);
      if (descEl) {
        description_text = convertNodeToText(descEl);
        raw_html_snippet = descEl.innerHTML;
      }
    }

    // 3. LinkedIn (Topcard Heading Exclusion & Notification Filter)
    else if (host.includes('linkedin.com')) {
      site_type = 'LINKEDIN';
      const pane = queryFirst([
        '.job-view-layout',
        '.jobs-search__job-details',
        'main.scaffold-layout__main',
        '.scaffold-layout__detail',
        '.top-card-layout',
        '#job-details'
      ])?.closest('.job-view-layout, .jobs-search__job-details, main, body') || document;

      title = getTextIn(pane, [
        '.job-details-jobs-unified-top-card__job-title h1:not(.visually-hidden)',
        '.job-details-jobs-unified-top-card__job-title a:not(.visually-hidden)',
        '.job-details-jobs-unified-top-card__job-title:not(.visually-hidden)',
        '.jobs-unified-top-card__job-title h1:not(.visually-hidden)',
        'h1.top-card-layout__title:not(.visually-hidden)',
        'h1.topcard__title:not(.visually-hidden)',
        'h1.t-24.t-bold:not(.visually-hidden)',
        'h1.t-24:not(.visually-hidden)',
        'h1[class*="job-title" i]:not(.visually-hidden)',
        'h1[class*="title" i]:not(.visually-hidden)',
        '.job-view-layout h1:not(.visually-hidden)',
        'main.scaffold-layout__main h1:not(.visually-hidden)',
        'h1:not(.visually-hidden)'
      ]);

      title = title.replace(/^\(\d+\)\s*/, '').trim();

      const lowerTitle = title.toLowerCase();
      if (
        lowerTitle.includes('notification') ||
        lowerTitle.includes('notificações') ||
        lowerTitle.includes('messaging') ||
        lowerTitle.includes('my network') ||
        lowerTitle === 'linkedin'
      ) {
        title = '';
      }

      company = getTextIn(pane, [
        'a.topcard__org-name-link',
        '.top-card-layout__first-subline a',
        '.job-details-jobs-unified-top-card__company-name a',
        '.job-details-jobs-unified-top-card__company-name',
        'a[data-tracking-control-name*="company"]',
        'a[href*="/company/"]'
      ]);
      if (company.toLowerCase().trim() === 'linkedin') company = '';

      location = getTextIn(pane, [
        '.topcard__flavor--bullet',
        '.top-card-layout__first-subline .topcard__flavor:not(.topcard__flavor--link)',
        '.job-details-jobs-unified-top-card__primary-description-container span.tvm__text',
        '.job-details-jobs-unified-top-card__bullet',
        'span.topcard__flavor:nth-of-type(2)',
        'span.topcard__flavor'
      ]);

      const workplaceType = getTextIn(pane, [
        '.job-details-jobs-unified-top-card__workplace-type',
        '.ui-label--accent-3',
        '.jobs-unified-top-card__workplace-type'
      ]);
      if (workplaceType && !location.includes(workplaceType)) {
        location = location ? `${location} (${workplaceType})` : workplaceType;
      }

      if (!location) {
        const primaryDesc = getTextIn(pane, ['.job-details-jobs-unified-top-card__primary-description', '.job-details-jobs-unified-top-card__primary-description-container']);
        if (primaryDesc) {
          const parts = primaryDesc.split('·').map((p) => p.trim());
          if (parts.length >= 2) {
            location = parts[1];
          }
        }
      }

      const descEl = queryFirstIn(pane, [
        '.show-more-less-html__markup',
        '.description__text',
        '#job-details',
        '.jobs-description__content'
      ]);
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

    // --- Tier 2: Universal Fallback Parser & Pattern Scanner ---
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

    // Generic Location Scanner
    if (!location && site_type === 'GENERIC') {
      const metaLoc = document.querySelector('meta[name="job:location"], meta[property="og:locality"]')?.content;
      if (metaLoc) {
        location = metaLoc.trim();
      } else {
        location = getText(['[class*="location" i]', '[data-location]', '[data-testid*="location" i]']);
        if (!location) {
          const headerText = document.querySelector('header, .header, main, body')?.textContent || '';
          const locMatch = headerText.match(/(?:Location|Based in|Office):\s*([^\n·|•<]+)/i);
          if (locMatch && locMatch[1]) {
            location = locMatch[1].trim();
          }
        }
      }
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

  /**
   * Resolves direct canonical job URL across major job boards and career portals.
   */
  function resolveCanonicalJobUrl(host, rawUrl) {
    try {
      const urlObj = new URL(rawUrl);

      // 1. LinkedIn
      if (host.includes('linkedin.com')) {
        const jobIdQuery = urlObj.searchParams.get('currentJobId');
        if (jobIdQuery && /^\d+$/.test(jobIdQuery)) {
          return `https://www.linkedin.com/jobs/view/${jobIdQuery}/`;
        }
        const pathMatch = urlObj.pathname.match(/\/jobs\/view\/(\d+)/i);
        if (pathMatch && pathMatch[1]) {
          return `https://www.linkedin.com/jobs/view/${pathMatch[1]}/`;
        }
        const pane = document.querySelector('.jobs-search__job-details, #job-details, .job-view-layout, .top-card-layout, body');
        if (pane) {
          const activeLink = pane.querySelector('a[href*="/jobs/view/"]');
          if (activeLink && activeLink.href) {
            const linkMatch = activeLink.href.match(/\/jobs\/view\/(\d+)/i);
            if (linkMatch && linkMatch[1]) {
              return `https://www.linkedin.com/jobs/view/${linkMatch[1]}/`;
            }
          }
          const dataJobEl = pane.querySelector('[data-job-id]');
          if (dataJobEl) {
            const jid = dataJobEl.getAttribute('data-job-id');
            if (jid && /^\d+$/.test(jid)) {
              return `https://www.linkedin.com/jobs/view/${jid}/`;
            }
          }
        }
      }

      // 2. Indeed
      else if (host.includes('indeed.com')) {
        const vjk = urlObj.searchParams.get('vjk') || urlObj.searchParams.get('jk');
        if (vjk) {
          return `https://www.indeed.com/viewjob?jk=${encodeURIComponent(vjk)}`;
        }
        const pane = document.querySelector('#jobsearch-ViewjobPaneWrapper, .jobsearch-JobComponent, main, body');
        if (pane) {
          const link = pane.querySelector('a[href*="/viewjob"]');
          if (link && link.href) {
            const linkObj = new URL(link.href);
            const linkJk = linkObj.searchParams.get('jk') || linkObj.searchParams.get('vjk');
            if (linkJk) return `https://www.indeed.com/viewjob?jk=${encodeURIComponent(linkJk)}`;
          }
          const dataJkEl = pane.querySelector('[data-jk]');
          if (dataJkEl) {
            const jkVal = dataJkEl.getAttribute('data-jk');
            if (jkVal) return `https://www.indeed.com/viewjob?jk=${encodeURIComponent(jkVal)}`;
          }
        }
      }

      // 3. Glassdoor
      else if (host.includes('glassdoor.com') || host.includes('glassdoor.co.uk')) {
        const jl = urlObj.searchParams.get('jl') || urlObj.searchParams.get('jobListingId');
        if (jl && /^\d+$/.test(jl)) {
          return `https://www.glassdoor.com/job-listing/?jl=${jl}`;
        }
        const activeLink = document.querySelector('[data-test="job-link"], a[href*="jobListingId="], a[href*="jl="]');
        if (activeLink && activeLink.href) {
          const linkObj = new URL(activeLink.href);
          const linkJl = linkObj.searchParams.get('jl') || linkObj.searchParams.get('jobListingId');
          if (linkJl && /^\d+$/.test(linkJl)) {
            return `https://www.glassdoor.com/job-listing/?jl=${linkJl}`;
          }
        }
      }

      // 4. General ATS & Sites
      const canonicalTag = document.querySelector('link[rel="canonical"]')?.href;
      const targetUrl = canonicalTag ? new URL(canonicalTag, rawUrl).href : rawUrl;
      const cleanObj = new URL(targetUrl);

      const stripParams = [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'refId', 'trackingId', 'trk', 'ref', 'gclid', 'fbclid', '_hsenc', '_hsmi'
      ];
      stripParams.forEach((param) => cleanObj.searchParams.delete(param));

      return cleanObj.href;
    } catch (err) {
      return rawUrl;
    }
  }

  // Assign globally as window.__JOB_TRACKER_EXTRACT__
  window.__JOB_TRACKER_EXTRACT__ = extractJobData;

  // Immediately execute and return when injected directly
  return extractJobData();
})();
