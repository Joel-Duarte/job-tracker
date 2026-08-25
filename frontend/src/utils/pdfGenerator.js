/**
 * Pure Client-Side Standard PDF 1.4 Generator for Cover Letters
 * Generates and downloads clean, standard-compliant vector PDF documents with zero external dependencies.
 */

export function downloadCoverLetterPdf({
  text,
  companyName = 'Company',
  positionTitle = 'Position',
}) {
  if (!text || !text.trim()) return

  // Page geometry (A4: 595.28 x 841.89 pt, 0.75in / 54pt margins)
  const pageWidth = 595.28
  const pageHeight = 841.89
  const margin = 54
  const usableWidth = pageWidth - margin * 2
  const topY = pageHeight - margin
  const bottomY = margin
  const fontSize = 10.5
  const lineHeight = 15.5

  // Approx character width for standard Helvetica (~5.5pt per char at 10.5pt font size)
  const maxCharsPerLine = Math.floor(usableWidth / 5.5)

  // Clean markdown asterisks and normalize newlines
  const cleanText = text
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')

  const paragraphs = cleanText.split('\n')
  const lines = []

  for (const para of paragraphs) {
    if (!para.trim()) {
      lines.push('') // Empty line for paragraph spacing
      continue
    }

    // Word wrap
    const words = para.split(/\s+/)
    let currentLine = ''
    for (const word of words) {
      if (!currentLine) {
        currentLine = word
      } else if ((currentLine + ' ' + word).length <= maxCharsPerLine) {
        currentLine += ' ' + word
      } else {
        lines.push(currentLine)
        currentLine = word
      }
    }
    if (currentLine) {
      lines.push(currentLine)
    }
  }

  // Split lines into pages
  const linesPerPage = Math.floor((topY - bottomY) / lineHeight)
  const pages = []
  let currentPageLines = []

  for (let i = 0; i < lines.length; i++) {
    currentPageLines.push(lines[i])
    if (currentPageLines.length >= linesPerPage) {
      pages.push(currentPageLines)
      currentPageLines = []
    }
  }
  if (currentPageLines.length > 0) {
    pages.push(currentPageLines)
  }
  if (pages.length === 0) {
    pages.push([''])
  }

  // Escape special PDF characters
  const escapePdf = (str) => {
    return str
      .replace(/\\/g, '\\\\')
      .replace(/\(/g, '\\(')
      .replace(/\)/g, '\\)')
  }

  // Build PDF Objects
  let objIndex = 1
  const objects = []

  const catalogObjId = objIndex++
  const pagesObjId = objIndex++
  const fontObjId = objIndex++

  const pageObjIds = []
  const contentObjIds = []

  for (let p = 0; p < pages.length; p++) {
    pageObjIds.push(objIndex++)
    contentObjIds.push(objIndex++)
  }

  const objCatalog = `${catalogObjId} 0 obj\n<< /Type /Catalog /Pages ${pagesObjId} 0 R >>\nendobj`
  const objPages = `${pagesObjId} 0 obj\n<< /Type /Pages /Kids [${pageObjIds.map((id) => `${id} 0 R`).join(' ')}] /Count ${pages.length} >>\nendobj`
  const objFont = `${fontObjId} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj`

  objects.push({ id: catalogObjId, content: objCatalog })
  objects.push({ id: pagesObjId, content: objPages })
  objects.push({ id: fontObjId, content: objFont })

  for (let p = 0; p < pages.length; p++) {
    const pageLines = pages[p]
    let streamText = `BT\n/F1 ${fontSize} Tf\n${margin} ${topY} Td\n${lineHeight} TL\n`
    for (let l = 0; l < pageLines.length; l++) {
      const line = pageLines[l]
      if (l === 0) {
        streamText += `(${escapePdf(line)}) Tj\n`
      } else {
        streamText += `T*\n(${escapePdf(line)}) Tj\n`
      }
    }
    streamText += `ET\n`

    const streamLength = new TextEncoder().encode(streamText).length
    const contentObj = `${contentObjIds[p]} 0 obj\n<< /Length ${streamLength} >>\nstream\n${streamText}endstream\nendobj`
    const pageObj = `${pageObjIds[p]} 0 obj\n<< /Type /Page /Parent ${pagesObjId} 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] /Contents ${contentObjIds[p]} 0 R /Resources << /Font << /F1 ${fontObjId} 0 R >> >> >>\nendobj`

    objects.push({ id: pageObjIds[p], content: pageObj })
    objects.push({ id: contentObjIds[p], content: contentObj })
  }

  // Sort objects by id
  objects.sort((a, b) => a.id - b.id)

  let pdfOutput = `%PDF-1.4\n%\xE2\xE3\xCF\xD3\n`
  const xrefOffsets = [0]

  for (const obj of objects) {
    const offset = new TextEncoder().encode(pdfOutput).length
    xrefOffsets[obj.id] = offset
    pdfOutput += `${obj.content}\n`
  }

  const startXref = new TextEncoder().encode(pdfOutput).length
  pdfOutput += `xref\n0 ${objects.length + 1}\n`
  pdfOutput += `0000000000 65535 f \n`
  for (let i = 1; i <= objects.length; i++) {
    const off = String(xrefOffsets[i]).padStart(10, '0')
    pdfOutput += `${off} 00000 n \n`
  }

  pdfOutput += `trailer\n<< /Size ${objects.length + 1} /Root ${catalogObjId} 0 R >>\n`
  pdfOutput += `startxref\n${startXref}\n%%EOF`

  const blob = new Blob([pdfOutput], { type: 'application/pdf' })
  const cleanComp = (companyName || 'Company').replace(/[^a-zA-Z0-9_-]/g, '_')
  const cleanPos = (positionTitle || 'Position').replace(/[^a-zA-Z0-9_-]/g, '_')
  const filename = `Cover_Letter_${cleanComp}_${cleanPos}.pdf`

  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  setTimeout(() => URL.revokeObjectURL(link.href), 1000)
}
