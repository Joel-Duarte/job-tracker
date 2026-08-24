import DOMPurify from 'dompurify'

/**
 * Safely sanitizes and linkifies email content for interactive viewing:
 * - Sanitizes HTML emails via DOMPurify, preserving styling/layout and button/link tags.
 * - Forces all anchor <a> tags to open in new tab (target="_blank", rel="noopener noreferrer").
 * - If plain text, escapes HTML entities, preserves line-breaks, and converts URLs into clickable links.
 */
export function renderEmailBody(rawContent) {
  if (!rawContent) return '<span class="text-muted">No message body available.</span>'
  const content = String(rawContent).trim()
  if (!content) return '<span class="text-muted">No message body available.</span>'

  // Check if string contains HTML tags
  const hasHtml = /<[a-z][\s\S]*>/i.test(content)

  if (hasHtml) {
    const clean = DOMPurify.sanitize(content, {
      ADD_ATTR: ['target', 'rel', 'style', 'class', 'align', 'valign', 'bgcolor', 'border', 'cellpadding', 'cellspacing', 'width', 'height'],
      FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form'],
    })

    if (typeof document !== 'undefined') {
      const tempDiv = document.createElement('div')
      tempDiv.innerHTML = clean
      const anchors = tempDiv.querySelectorAll('a')
      anchors.forEach((a) => {
        a.setAttribute('target', '_blank')
        a.setAttribute('rel', 'noopener noreferrer')
        a.classList.add('email-rendered-link')
      })
      return tempDiv.innerHTML
    }
    return clean
  }

  // Plaintext email rendering: escape HTML & linkify URLs
  const escaped = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  const urlRegex = /(https?:\/\/[^\s<>"']+)/gi
  const linkified = escaped.replace(urlRegex, (url) => {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="email-rendered-link">${url}</a>`
  })

  return `<div style="white-space: pre-wrap; word-break: break-word; font-family: inherit; line-height: 1.6;">${linkified}</div>`
}
