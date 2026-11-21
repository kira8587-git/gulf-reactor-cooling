const { chromium } = require('playwright');
(async () => {
  const [, , html, pdf, footer] = process.argv;
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + html, { waitUntil: 'load' });
  // wait for MathJax (if the page uses it) to finish typesetting every equation
  await page.evaluate(async () => { if (window.MathJax && MathJax.startup) { await MathJax.startup.promise; } });
  await page.pdf({ path: pdf, format: 'A4', printBackground: true,
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#777">' + (footer || '') + ' · page <span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    margin: { top: '16mm', bottom: '16mm', left: '15mm', right: '15mm' } });
  await browser.close();
})();
