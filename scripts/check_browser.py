"""Local release smoke test with real Chromium; no publishing or external data.

Run with QA Python and PLAYWRIGHT_BROWSERS_PATH pointing at .qa-browsers.
The script owns and stops its loopback-only test server.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "qa"
OUTPUT.mkdir(parents=True, exist_ok=True)
URL = "http://127.0.0.1:8599"
TABS = {
    "en": ["My financial profile", "Financial assessment", "Emergency simulator", "Recovery strategies", "Wealth readiness"],
    "es": ["Mi perfil financiero", "Diagnóstico financiero", "Simulador de emergencias", "Estrategias de recuperación", "Preparación patrimonial"],
}


def settle(page):
    # Tab selection changes on the client before Streamlit finishes its rerun.
    # Wait through that transition before inspecting financial values.
    page.wait_for_timeout(250)
    expect(page.get_by_test_id("stApp")).to_have_attribute("data-test-script-state", "notRunning", timeout=30000)


def profile_values(page):
    return {key: page.locator(f".st-key-{key} input").input_value()
            for key in ("income", "essential_expenses", "discretionary_expenses", "savings", "debt_balance", "minimum_debt_payment")}


def main():
    print("Starting isolated local server", flush=True)
    report = {"checks": [], "console_errors": [], "page_errors": [], "screenshots": []}
    with (OUTPUT / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.headless=true",
             "--server.address=127.0.0.1", "--server.port=8599", "--browser.gatherUsageStats=false"],
            cwd=ROOT, stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            deadline = time.monotonic() + 45
            while True:
                try:
                    with urllib.request.urlopen(URL + "/_stcore/health", timeout=2) as response:
                        assert response.status == 200
                    break
                except OSError:
                    if time.monotonic() > deadline or server.poll() is not None:
                        raise RuntimeError("Local test server did not become healthy")
                    time.sleep(.25)
            report["checks"].append("Fresh-environment loopback HTTP health: 200")
            print("HTTP health passed; launching Chromium", flush=True)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                print("Chromium launched", flush=True)
                report["browser_version"] = browser.version
                for device, viewport in [("desktop", {"width": 1440, "height": 1000}),
                                          ("mobile", {"width": 390, "height": 844})]:
                    context = browser.new_context(viewport=viewport, is_mobile=device == "mobile", has_touch=device == "mobile")
                    page = context.new_page()
                    page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
                    page.on("console", lambda message: report["console_errors"].append(message.text) if message.type == "error" else None)
                    page.goto(URL, wait_until="domcontentloaded")
                    print(f"Loaded {device} page", flush=True)
                    expect(page.get_by_text("Welcome, Carlos", exact=True)).to_be_visible(timeout=45000)
                    settle(page)
                    for language in ("en", "es"):
                        if language == "es":
                            sidebar = page.get_by_test_id("stSidebar")
                            if not sidebar.is_visible():
                                page.get_by_test_id("stExpandSidebarButton").click()
                            page.locator(".st-key-language").get_by_role("combobox").click()
                            page.get_by_role("option", name="Español", exact=True).click()
                            expect(page.get_by_text("Bienvenido, Carlos", exact=True)).to_be_visible()
                            settle(page)
                            if device == "mobile":
                                page.get_by_test_id("stSidebarCollapseButton").click()
                        for index, label in enumerate(TABS[language]):
                            tab = page.get_by_role("tab", name=label, exact=True)
                            tab.click()
                            expect(tab).to_have_attribute("aria-selected", "true")
                            settle(page)
                            current_values = profile_values(page)
                            expected_values = dict(income=4000, essential_expenses=2000, discretionary_expenses=500,
                                                   savings=4500, debt_balance=3000, minimum_debt_payment=150)
                            assert {key: float(value) for key, value in current_values.items()} == expected_values, current_values
                            panel = page.locator('[role="tabpanel"]:visible')
                            expect(panel).to_be_visible()
                            expect(page.get_by_test_id("stException")).to_have_count(0)
                            if index == 1:
                                expect(panel.get_by_text("69.77%", exact=False).first).to_be_visible()
                            if index in (1, 2, 3, 4):
                                expect(panel.get_by_test_id("stPlotlyChart").first).to_be_visible()
                            dimensions = page.evaluate("({width: innerWidth, content: document.documentElement.scrollWidth})")
                            assert dimensions["content"] <= dimensions["width"] + 2, dimensions
                            screenshot = f"{device}_{language}_tab{index + 1}.png"
                            page.screenshot(path=str(OUTPUT / screenshot), full_page=True)
                            report["screenshots"].append(screenshot)
                            if index > 0:
                                first_chart = panel.get_by_test_id("stPlotlyChart").first
                                first_chart.scroll_into_view_if_needed()
                                first_screenshot = f"{device}_{language}_tab{index + 1}_first_chart.png"
                                page.screenshot(path=str(OUTPUT / first_screenshot))
                                report["screenshots"].append(first_screenshot)
                                chart = panel.get_by_test_id("stPlotlyChart").last
                                chart.scroll_into_view_if_needed()
                                chart_screenshot = f"{device}_{language}_tab{index + 1}_chart.png"
                                page.screenshot(path=str(OUTPUT / chart_screenshot))
                                report["screenshots"].append(chart_screenshot)
                            report["checks"].append(f"{device}/{language}/{label}: visible, no page overflow or Streamlit exception")
                            print(report["checks"][-1], flush=True)
                    context.close()
                browser.close()
            assert not report["page_errors"], report["page_errors"]
        except Exception as error:
            report["failure"] = repr(error)
            if "page" in locals() and not page.is_closed():
                page.screenshot(path=str(OUTPUT / "failure.png"))
                report["failure_profile"] = profile_values(page)
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
            (OUTPUT / "browser.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
