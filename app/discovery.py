"""
Discovery mode — opens the ICPPlus wizard in a headed browser and captures
each page's state after you manually advance through the steps.

Press ENTER in the terminal after each wizard step to capture that page.
Type 'done' and press ENTER when finished.
"""
import asyncio
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page

from app.config import DISCOVERY_DIR, ICPPLUS_URL, DB_PATH, BROWSER_SLOW_MO
from app.database import get_connection


async def _capture_step(page: Page, run_id: str, step: int) -> dict:
    step_dir = DISCOVERY_DIR / run_id / f"step_{step:02d}"
    step_dir.mkdir(parents=True, exist_ok=True)

    url = page.url
    title = await page.title()

    # Screenshot
    screenshot_path = step_dir / "screenshot.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)

    # HTML
    html = await page.content()
    (step_dir / "page.html").write_text(html, encoding="utf-8")

    # Visible text
    visible_text = await page.evaluate("""() => {
        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            { acceptNode: n => n.parentElement.offsetParent !== null ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT }
        );
        const parts = [];
        let node;
        while ((node = walker.nextNode())) {
            const t = node.textContent.trim();
            if (t) parts.push(t);
        }
        return parts.join('\\n');
    }""")
    (step_dir / "visible_text.txt").write_text(visible_text, encoding="utf-8")

    # Buttons
    buttons = await page.evaluate("""() =>
        Array.from(document.querySelectorAll('button, input[type=submit], input[type=button], a[role=button]'))
            .map(el => ({
                tag: el.tagName,
                text: el.innerText || el.value || el.getAttribute('aria-label') || '',
                id: el.id || null,
                name: el.getAttribute('name') || null,
                type: el.getAttribute('type') || null,
            }))
    """)

    # Forms
    forms = await page.evaluate("""() =>
        Array.from(document.querySelectorAll('form')).map(f => ({
            id: f.id || null,
            action: f.action || null,
            method: f.method || null,
            fields: Array.from(f.querySelectorAll('input, select, textarea')).map(el => ({
                tag: el.tagName,
                type: el.getAttribute('type') || null,
                name: el.getAttribute('name') || null,
                id: el.id || null,
                placeholder: el.getAttribute('placeholder') || null,
            }))
        }))
    """)

    # Select options
    selects = await page.evaluate("""() =>
        Array.from(document.querySelectorAll('select')).map(sel => ({
            name: sel.getAttribute('name') || null,
            id: sel.id || null,
            options: Array.from(sel.options).map(o => ({ value: o.value, text: o.text.trim() }))
        }))
    """)

    meta = {
        "run_id": run_id,
        "step": step,
        "url": url,
        "page_title": title,
        "captured_at": datetime.utcnow().isoformat(),
        "screenshot": str(screenshot_path.relative_to(DISCOVERY_DIR.parent)),
        "buttons": buttons,
        "forms": forms,
        "selects": selects,
    }
    (step_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Persist to DB
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO discovery_runs (run_id, step, url, page_title) VALUES (?,?,?,?)",
            (run_id, step, url, title),
        )
    conn.close()

    print(f"[discovery] Step {step} captured — {title[:60]!r} @ {url[:80]}")
    print(f"            Saved to {step_dir}")
    return meta


async def run_discovery() -> None:
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    print(f"[discovery] Starting run {run_id}")
    print(f"[discovery] Output → {DISCOVERY_DIR / run_id}")
    print()
    print("  Navigate through the ICPPlus wizard manually in the browser.")
    print("  Press ENTER here after each page to capture it.")
    print("  Type 'done' and press ENTER when you are finished.")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=BROWSER_SLOW_MO)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="es-ES",
        )
        page = await context.new_page()

        print(f"[discovery] Opening {ICPPLUS_URL}")
        await page.goto(ICPPLUS_URL, wait_until="domcontentloaded")

        step = 0
        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, ">> Press ENTER to capture (or type 'done'): "
                )
            except EOFError:
                break

            if user_input.strip().lower() == "done":
                print("[discovery] Finished.")
                break

            await _capture_step(page, run_id, step)
            step += 1

        await browser.close()

    print(f"\n[discovery] Run complete — {step} steps captured in {DISCOVERY_DIR / run_id}")
