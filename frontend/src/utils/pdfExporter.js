export function exportHTMLToPDF(htmlContent, filename = 'document.pdf') {
  const iframe = document.createElement('iframe');
  iframe.style.position = 'absolute';
  iframe.style.width = '0';
  iframe.style.height = '0';
  iframe.style.border = 'none';

  document.body.appendChild(iframe);

  const doc = iframe.contentWindow.document;
  doc.open();
  doc.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${filename}</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          line-height: 1.6;
          color: #333;
          margin: 40px auto;
          max-width: 800px;
          padding: 0 20px;
        }
        h1, h2, h3 { color: #111; margin-top: 1.5em; margin-bottom: 0.5em; }
        h1 { font-size: 24px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        h2 { font-size: 20px; }
        p { margin-bottom: 1em; }
        ul { padding-left: 20px; margin-bottom: 1em; }
        li { margin-bottom: 0.5em; }
        strong { font-weight: 600; }
        @media print {
          body {
            margin: 0;
            padding: 0.5in;
            max-width: 100%;
          }
        }
      </style>
    </head>
    <body>
      ${htmlContent}
    </body>
    </html>
  `);
  doc.close();

  iframe.contentWindow.focus();
  setTimeout(() => {
    iframe.contentWindow.print();
    setTimeout(() => {
      document.body.removeChild(iframe);
    }, 1000);
  }, 500);
}