"""
Diagnose Wellfound scraper: check what selectors actually exist on the page.
Run: /home/kzamd22/job/venv/bin/python debug_wellfound.py
"""
import asyncio
import urllib.parse
from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        params = {"q": "Instructional Designer", "l": "remote"}
        url = "https://wellfound.com/jobs?" + urllib.parse.urlencode(params)
        print(f"Loading: {url}")

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        title = await page.title()
        print(f"Page title: {title}")

        # Check current URL (may have redirected)
        print(f"Current URL: {page.url}")

        # Save a screenshot
        await page.screenshot(path="output/debug_wellfound.png", full_page=False)
        print("Screenshot saved → output/debug_wellfound.png")

        # Check for the old selectors
        old_selectors = [
            "[data-test='JobSearchResult']",
            ".styles_component__",
            ".styles_jobResult__",
            "div[class*='JobSearchResult']",
        ]
        print("\n--- Old selector counts ---")
        for sel in old_selectors:
            count = await page.locator(sel).count()
            print(f"  {sel!r:55s} → {count}")

        # Dump all unique data-test attribute values
        data_tests = await page.evaluate("""() => {
            const elems = document.querySelectorAll('[data-test]');
            const vals = {};
            for (const el of elems) {
                const v = el.getAttribute('data-test');
                vals[v] = (vals[v] || 0) + 1;
            }
            return Object.entries(vals).sort((a,b)=>b[1]-a[1]);
        }""")
        print("\n--- data-test values on page ---")
        for val, count in data_tests[:30]:
            print(f"  {count:3d}x  data-test={val!r}")

        # Dump div classes that appear 2-30 times (card frequency)
        classes = await page.evaluate("""() => {
            const divs = document.querySelectorAll('div[class], li[class], article[class]');
            const counts = {};
            for (const d of divs) {
                const c = d.className.trim().split(/\s+/).join(' ');
                if (c) counts[c] = (counts[c] || 0) + 1;
            }
            return Object.entries(counts)
                .filter(([,n]) => n >= 2 && n <= 40)
                .sort((a,b) => b[1]-a[1])
                .slice(0, 30)
                .map(([c,n]) => `${n}x  ${c}`);
        }""")
        print("\n--- div/li/article classes appearing 2-40 times ---")
        for c in classes:
            print(f"  {c}")

        # Check for any job-related text on the page
        body_text = await page.evaluate("document.body.innerText.slice(0, 1000)")
        print(f"\n--- First 1000 chars of page text ---\n{body_text}")

        # Check for any <a> tags that look like job links
        job_links = await page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            return links
                .map(a => a.href)
                .filter(h => h.includes('/jobs/') || h.includes('/job/'))
                .slice(0, 10);
        }""")
        print(f"\n--- Sample job-like links ---")
        for lnk in job_links:
            print(f"  {lnk}")

        await browser.close()

asyncio.run(main())
