import { Marked } from 'marked'
import DOMPurify from 'dompurify'

const sdMarked = new Marked({
  gfm: true,
  breaks: true,
  renderer: {
    link({ href, title, text }) {
      const safeUrl =
        href &&
        (href.startsWith('http://') ||
          href.startsWith('https://') ||
          href.startsWith('/') ||
          href.startsWith('mailto:'))
          ? href
          : '#'
      const titleAttr = title ? ` title="${title}"` : ''
      return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer"${titleAttr}>${text}</a>`
    },
  },
})

/**
 * Render Markdown chat turns safely using an isolated Marked instance and DOMPurify.
 */
export function renderChatMarkdown(content) {
  if (!content) return ''
  try {
    const normalized = String(content).replace(/^([\t ]*)[•●○]\s+/gm, '$1- ')
    const rawHtml = sdMarked.parse(normalized)
    return DOMPurify.sanitize(rawHtml, { ADD_ATTR: ['target', 'rel'] })
  } catch {
    return DOMPurify.sanitize(String(content))
  }
}
