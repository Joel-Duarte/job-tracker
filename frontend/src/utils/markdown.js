/**
 * Shared Markdown parsing utility for frontend Vue views and components.
 * Converts raw markdown string into sanitized HTML.
 */

function escapeHtml(text) {
  if (!text) return ''
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

export function renderMarkdown(text) {
  if (!text) return ''

  let html = escapeHtml(text)

  // Fenced code blocks ```code```
  html = html.replace(/```([\s\S]*?)```/g, (_, p1) => {
    return `<pre><code>${p1.trim()}</code></pre>`
  })

  // Inline code `code`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')

  // Tables
  const lines = html.split('\n')
  let inTable = false
  let tableHtml = ''
  const newLines = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (line.startsWith('|') && line.endsWith('|')) {
      const cells = line.split('|').slice(1, -1).map((c) => c.trim())
      if (cells.every((c) => /^:?-+:?$/.test(c))) {
        continue
      }
      if (!inTable) {
        inTable = true
        tableHtml =
          '<table><thead><tr>' +
          cells.map((c) => `<th>${c}</th>`).join('') +
          '</tr></thead><tbody>'
      } else {
        tableHtml +=
          '<tr>' + cells.map((c) => `<td>${c}</td>`).join('') + '</tr>'
      }
    } else {
      if (inTable) {
        tableHtml += '</tbody></table>'
        newLines.push(tableHtml)
        inTable = false
        tableHtml = ''
      }
      newLines.push(lines[i])
    }
  }
  if (inTable) {
    tableHtml += '</tbody></table>'
    newLines.push(tableHtml)
  }
  html = newLines.join('\n')

  // Headings
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>')
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>')
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>')

  // Blockquotes
  html = html.replace(/^&gt;\s?(.*$)/gim, '<blockquote>$1</blockquote>')

  // Bold and Italics
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')

  // Unordered / Ordered Lists
  html = html.replace(/^\s*[\-\*]\s+(.*$)/gim, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)/gis, '<ul class="jd-list">$1</ul>')
  html = html.replace(/<\/ul>\s*<ul class="jd-list">/g, '')

  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, p1, p2) => {
    const safeUrl =
      p2.startsWith('http://') || p2.startsWith('https://') || p2.startsWith('/')
        ? p2
        : '#'
    return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${p1}</a>`
  })

  // Paragraph breaks
  html = html.replace(/\n\n+/g, '</p><p>')
  html = `<p>${html}</p>`
  html = html.replace(/<p>\s*<\/p>/g, '')
  html = html.replace(/<p>(<h[1-3]>.*?<\/h[1-3]>)<\/p>/g, '$1')
  html = html.replace(/<p>(<pre>.*?<\/pre>)<\/p>/gs, '$1')
  html = html.replace(/<p>(<table>.*?<\/table>)<\/p>/gs, '$1')
  html = html.replace(/<p>(<ul.*?>.*?<\/ul>)<\/p>/gs, '$1')
  html = html.replace(/<p>(<blockquote>.*?<\/blockquote>)<\/p>/gs, '$1')

  return html
}
