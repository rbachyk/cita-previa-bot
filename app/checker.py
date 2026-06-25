"""
Automated availability checker — monitoring only.

Navigates the ICPPlus wizard through all 5 steps to reach the acCitar result
page, reads whether appointment slots are available, then exits without booking.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from app.config import (
    ICPPLUS_URL,
    BROWSER_SLOW_MO,
    PROVINCE_URL_PATH,
    SEDE_VALUE,
    TRAMITE_GROUP_INDEX,
    TRAMITE_VALUE,
    SUBTRAMITE_VALUE,
    NIE,
    NOMBRE,
    ALERT_COOLDOWN_SECONDS,
)
from app.database import get_connection
from app.telegram_bot import send_message

NO_SLOTS_MARKER = "no hay citas disponibles"
CAPTCHA_MARKER = "captcha"
STEP_TIMEOUT = 15_000  # ms

_HEARTBEAT = Path("/tmp/cita_previa_heartbeat")


async def _walk_wizard(page: Page) -> str:
    """Navigate all wizard steps; return body text of the final result page."""

    # Step 0 — province selection
    await page.goto(ICPPLUS_URL, wait_until="domcontentloaded")
    try:
        await page.wait_for_selector("#form", timeout=STEP_TIMEOUT)
    except PlaywrightTimeout:
        html = await page.content()
        print(f"[checker] DEBUG url={page.url!r}")
        print(f"[checker] DEBUG html={html[:1000]!r}")
        raise
    await page.select_option("#form", value=PROVINCE_URL_PATH)
    await page.click("#btnAceptar")
    await page.wait_for_load_state("domcontentloaded")

    # Step 1 — office + procedure
    await page.wait_for_selector("#sede", timeout=STEP_TIMEOUT)
    await page.select_option("#sede", value=SEDE_VALUE)
    tramite_sel = f'select[name="tramiteGrupo[{TRAMITE_GROUP_INDEX}]"]'
    await page.select_option(tramite_sel, value=TRAMITE_VALUE)
    if SUBTRAMITE_VALUE:
        await page.wait_for_selector("#subtramite:not([disabled])", timeout=STEP_TIMEOUT)
        await page.select_option("#subtramite", value=SUBTRAMITE_VALUE)
    await page.click("#btnAceptar")
    await page.wait_for_load_state("domcontentloaded")

    # Step 2 — info page
    await page.wait_for_selector("#btnEntrar", timeout=STEP_TIMEOUT)
    await page.click("#btnEntrar")
    await page.wait_for_load_state("domcontentloaded")

    # Step 3 — personal data
    await page.wait_for_selector("#citadoForm", timeout=STEP_TIMEOUT)
    await page.check("#rdbTipoDocNie")
    await page.fill("#txtIdCitado", NIE)
    await page.fill("#txtDesCitado", NOMBRE)
    await page.click("#btnEnviar")
    await page.wait_for_load_state("domcontentloaded")

    # Step 4 — options: click "Solicitar Cita" to reach the availability result
    await page.wait_for_selector("#btnEnviar", timeout=STEP_TIMEOUT)
    await page.click("#btnEnviar")
    await page.wait_for_load_state("domcontentloaded")

    # Step 5 — result page (acCitar): read and return, do NOT interact further
    return await page.inner_text("body")


async def check_once() -> dict:
    """Run one full check cycle. Returns status dict."""
    result: dict = {"slots_available": False, "status": "unknown", "snippet": ""}
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                slow_mo=BROWSER_SLOW_MO,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            context = await browser.new_context(locale="es-ES")
            page = await context.new_page()
            body_text = await _walk_wizard(page)
            await browser.close()

        result["snippet"] = body_text[:500]
        text_lower = body_text.lower()

        if CAPTCHA_MARKER in text_lower:
            result["status"] = "captcha_blocked"
        elif NO_SLOTS_MARKER in text_lower:
            result["status"] = "no_slots"
        else:
            result["status"] = "slots_available"
            result["slots_available"] = True

    except PlaywrightTimeout as e:
        result["status"] = f"timeout:{e}"
    except Exception as e:
        result["status"] = f"error:{e}"

    return result


def _should_notify(current_slots: bool) -> bool:
    """
    Return True only when a Telegram alert should fire.

    Fires on:
    - First transition from non-slots → slots_available
    - Re-alert when slots stay open longer than ALERT_COOLDOWN_SECONDS
    Never fires when current_slots is False.
    Reads from DB *before* the current result is recorded.
    """
    if not current_slots:
        return False

    conn = get_connection()
    try:
        prev = conn.execute(
            "SELECT status FROM monitor_checks ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if not prev or prev["status"] != "slots_available":
            return True  # Fresh transition → alert immediately

        # Slots were already open — re-alert only after cooldown expires
        last_notif = conn.execute(
            "SELECT sent_at FROM notifications_sent ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not last_notif:
            return True
        elapsed = (
            datetime.utcnow() - datetime.fromisoformat(last_notif["sent_at"])
        ).total_seconds()
        return elapsed >= ALERT_COOLDOWN_SECONDS
    finally:
        conn.close()


def _record(result: dict) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO monitor_checks (status, slots_found, raw_json) VALUES (?,?,?)",
            (result["status"], int(result["slots_available"]), json.dumps(result["snippet"])),
        )
    conn.close()


def _record_notification(message: str) -> None:
    conn = get_connection()
    with conn:
        conn.execute("INSERT INTO notifications_sent (message) VALUES (?)", (message,))
    conn.close()


async def run_checker(interval_seconds: int) -> None:
    """Poll in a loop forever."""
    if not NIE or not NOMBRE:
        raise SystemExit("[checker] NIE and NOMBRE must be set in .env before running.")

    print(
        f"[checker] Starting — interval={interval_seconds}s "
        f"cooldown={ALERT_COOLDOWN_SECONDS}s "
        f"tramiteGrupo[{TRAMITE_GROUP_INDEX}]={TRAMITE_VALUE}"
    )

    while True:
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[checker] {ts} — checking...", end=" ", flush=True)

        result = await check_once()
        notify = _should_notify(result["slots_available"])
        _record(result)
        print(result["status"])

        if notify:
            alert_msg = (
                "🚨 <b>¡CITA DISPONIBLE!</b>\n\n"
                "Se han encontrado citas disponibles en ICPPlus.\n"
                f"Entra ahora: {ICPPLUS_URL}"
            )
            await send_message(alert_msg)
            _record_notification(alert_msg)
            print("[checker] Telegram alert sent.")
        elif result["status"] == "captcha_blocked":
            print("[checker] CAPTCHA detected — will retry next cycle.")

        _HEARTBEAT.touch()
        await asyncio.sleep(interval_seconds)
