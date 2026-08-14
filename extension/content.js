// Content script to scrape job metadata from active page DOM
function extractJobMetadata() {
  const url = window.location.href;
  let company = "";
  let position = "";
  let location = "";
  let description = "";

  // Strategy 1: OpenGraph and Meta tags
  const ogTitle = document.querySelector('meta[property="og:title"]')?.content || "";
  const ogSiteName = document.querySelector('meta[property="og:site_name"]')?.content || "";
  const docTitle = document.title || "";

  // Strategy 2: Common ATS / Job Portal Selectors
  // LinkedIn
  if (url.includes("linkedin.com")) {
    position = document.querySelector(".job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title")?.innerText?.trim() || "";
    company = document.querySelector(".job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name")?.innerText?.trim() || "";
    location = document.querySelector(".job-details-jobs-unified-top-card__bullet, .jobs-unified-top-card__bullet")?.innerText?.trim() || "";
    description = document.querySelector("#job-details, .jobs-description-content__text")?.innerText?.trim() || "";
  }
  // Greenhouse
  else if (url.includes("greenhouse.io") || document.querySelector("#app_body")) {
    position = document.querySelector(".app-title, h1.heading")?.innerText?.trim() || "";
    company = document.querySelector(".company-name")?.innerText?.trim() || ogSiteName;
    description = document.querySelector("#content, #job-description")?.innerText?.trim() || "";
  }
  // Lever
  else if (url.includes("lever.co")) {
    position = document.querySelector(".posting-headline h2")?.innerText?.trim() || "";
    company = document.querySelector(".main-header-logo img")?.alt || ogSiteName;
    description = document.querySelector(".section-wrapper")?.innerText?.trim() || "";
  }
  // Fallback heuristic: parse Title tag "Job Title at Company" or "Job Title - Company"
  if (!position || !company) {
    const rawTitle = ogTitle || docTitle;
    if (rawTitle.includes(" at ")) {
      const parts = rawTitle.split(" at ");
      position = position || parts[0].trim();
      company = company || parts[1].split("|")[0].split("-")[0].trim();
    } else if (rawTitle.includes(" - ")) {
      const parts = rawTitle.split(" - ");
      position = position || parts[0].trim();
      company = company || parts[1].trim();
    } else {
      position = position || rawTitle.slice(0, 80);
    }
  }

  // Fallback body text
  if (!description) {
    const mainEl = document.querySelector("main, article, #job-details, .job-description, body");
    description = mainEl ? mainEl.innerText.slice(0, 10000) : "";
  }

  return {
    url,
    company: company.slice(0, 120),
    position: position.slice(0, 120),
    location: location.slice(0, 100),
    description,
  };
}

// Return result when executed via chrome.scripting
extractJobMetadata();
