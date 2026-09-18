const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const REPORT_DIR = 'C:\\Users\\Hp\\.gstack\\projects\\Parallel Mind 2.0\\designs\\design-audit-20260918';
const SCREENSHOTS_DIR = path.join(REPORT_DIR, 'screenshots');

if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

async function captureFirstImpression() {
    // Use system Chrome/Edge instead of downloading Chromium
    const browser = await chromium.launch({ 
        headless: true,
        channel: 'chrome' // or 'msedge' for Edge
    });
    const context = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 2,
    });
    const page = await context.newPage();

    // Capture console errors
    const consoleErrors = [];
    page.on('console', msg => {
        if (msg.type() === 'error') {
            consoleErrors.push(msg.text());
        }
    });
    page.on('pageerror', error => {
        consoleErrors.push('uncaught: ' + error.message);
    });

    const url = 'http://localhost:3000';
    console.log('Navigating to:', url);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });

    // Take full page screenshot
    const screenshotPath = path.join(SCREENSHOTS_DIR, 'first-impression.jpg');
    await page.screenshot({ path: screenshotPath, fullPage: true, type: 'jpeg', quality: 60 });
    console.log('Screenshot saved to:', screenshotPath);

    // Get page text
    const text = await page.evaluate(() => document.body.innerText);
    console.log('TEXT_START');
    console.log(text.slice(0, 20000));
    console.log('TEXT_END');

    // Get console errors
    console.log('CONSOLE_ERRORS=' + JSON.stringify(consoleErrors));

    // Get navigation timing
    const navTiming = await page.evaluate(() => {
        const entries = performance.getEntriesByType('navigation');
        return entries[0] ? JSON.stringify(entries[0]) : '{}';
    });
    console.log('NAV=' + navTiming);

    // Get annotated screenshot (with element labels)
    await page.evaluate(() => {
        const style = document.createElement('style');
        style.textContent = `
            *:hover { outline: 2px solid #7C5CFF !important; outline-offset: 2px; }
        `;
        document.head.appendChild(style);
    });
    const annotatedPath = path.join(SCREENSHOTS_DIR, 'first-impression-annotated.png');
    await page.screenshot({ path: annotatedPath, fullPage: true, type: 'png' });
    console.log('Annotated screenshot saved to:', annotatedPath);

    // Responsive screenshots
    const viewports = [
        { name: 'mobile', width: 375, height: 812 },
        { name: 'tablet', width: 768, height: 1024 },
        { name: 'desktop', width: 1440, height: 900 }
    ];

    for (const vp of viewports) {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.waitForTimeout(300);
        const respPath = path.join(SCREENSHOTS_DIR, `first-impression-${vp.name}.jpg`);
        await page.screenshot({ path: respPath, fullPage: true, type: 'jpeg', quality: 60 });
        console.log(`Responsive ${vp.name} screenshot saved to:`, respPath);
    }

    await browser.close();
    console.log('GSTACK_STEP_OK');
}

captureFirstImpression().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});