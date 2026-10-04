"""Real browser smoke test. Run explicitly; uses a temporary database and Edge.

Every browser request leaving loopback is rejected. The companion model test
blocks Python socket connects, so together they cover both runtime layers.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import threading
import socket
import sqlite3
from urllib.request import urlopen
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]

def verify_seeded_demo(page, expect):
    """Exercise the actual seeded database in a disposable SQLite copy."""
    from calendar import month_name
    report = json.loads((ROOT/"backend/data/synthetic/noor_demo_report.json").read_text(encoding="utf-8"))
    page.get_by_role("button",name="Noor's Dashboard",exact=True).click()
    for _ in range(4): page.get_by_role("button",name="0",exact=True).click()
    page.get_by_role("button",name="Enter",exact=True).click()
    expect(page.get_by_text("Hi Noor",exact=True)).to_be_visible()
    expect(page.get_by_text("Demo data: 225 synthetic reviews 2026.",exact=False)).to_be_visible()
    page.get_by_role("button",name="All Reviews",exact=False).click()
    expect(page.locator("article.review")).to_have_count(20)
    expect(page.get_by_text("Synthetic",exact=True)).to_have_count(20)
    expect(page.locator("article.review").first.locator(".swline").first).to_be_visible()
    page.get_by_role("button",name="Show all 225",exact=True).click()
    expect(page.locator("article.review")).to_have_count(225)
    page.get_by_role("button",name="Home",exact=True).first.click()
    page.get_by_role("button",name="My Plans",exact=False).click()
    expect(page.get_by_text("Better",exact=True)).to_be_visible()
    expect(page.get_by_text("7 of 58 complained",exact=True)).to_be_visible()
    expect(page.get_by_text("0 of 167 complained",exact=True)).to_be_visible()
    page.get_by_role("button",name="Home",exact=True).first.click()
    page.get_by_role("button",name="Plans What",exact=False).click()
    page.locator("button.topiccard").filter(has_text="Visitors raised concerns about coffee tasting.").click()
    expect(page.get_by_text("Confidence: High",exact=True)).to_be_visible()
    expect(page.get_by_text("Add a few extra minutes to the coffee tasting portion of the tour.",exact=True)).to_be_visible()
    page.get_by_role("button",name="Plans",exact=True).first.click()
    page.locator("button.topiccard").filter(has_text="Visitors raised concerns about group size and hearing noor.").click()
    expect(page.get_by_text("Confidence: Medium",exact=True)).to_be_visible()
    page.get_by_role("button",name="Plans",exact=True).first.click()
    page.get_by_role("button",name="Home",exact=True).first.click()
    page.get_by_role("button",name="Monthly Performance",exact=False).click()
    for month in report["months"]:
        name = month_name[int(month["month"][-2:])]
        page.get_by_role("button",name="Month",exact=True).click()
        page.get_by_role("button",name=f"{name} 2026",exact=False).click()
        expect(page.get_by_text(f"{name} reviews ({month['review_count']})",exact=True)).to_be_visible()
        expect(page.locator(".display.tnum")).to_have_text(f"{month['average_rating']:.1f}")
    page.get_by_role("button",name="Home",exact=True).first.click()
    output = ROOT/"backend/test-results"
    output.mkdir(exist_ok=True)
    page.screenshot(path=str(output/"noor-demo-browser.png"),animations="disabled")


def run(seed_demo=False):
    from playwright.sync_api import sync_playwright, expect
    with tempfile.TemporaryDirectory(prefix="echo-browser-", ignore_cleanup_errors=True) as directory:
        if seed_demo:
            with sqlite3.connect(ROOT/"backend/echo.db") as source_db, sqlite3.connect(Path(directory)/"echo.db") as target_db:
                source_db.backup(target_db)
        os.environ.update({"ECHO_DB":str(Path(directory)/"echo.db"),"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1"})
        original_connect = socket.socket.connect
        def local_connect(sock, address):
            if isinstance(address, tuple) and address[0] not in {"127.0.0.1","localhost","::1"}:
                raise AssertionError("Backend attempted an external connection: " + str(address))
            return original_connect(sock,address)
        socket.socket.connect = local_connect
        sys.path.insert(0,str(ROOT/"backend"))
        import uvicorn
        with (Path(directory)/"server.log").open("w") as log:
            server = uvicorn.Server(uvicorn.Config("api:app",host="127.0.0.1",port=8018,log_level="warning"))
            thread = threading.Thread(target=server.run,daemon=True)
            thread.start()
            try:
                for _ in range(120):
                    try:
                        if urlopen("http://127.0.0.1:8018/health",timeout=1).status == 200: break
                    except OSError:
                        if not thread.is_alive(): raise RuntimeError("Server thread stopped")
                        time.sleep(.5)
                else: raise RuntimeError("Server did not start")
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(channel="msedge",headless=True)
                    context = browser.new_context(viewport={"width":1100,"height":1100})
                    external, errors = [], []
                    def route_request(route):
                        if urlparse(route.request.url).hostname not in {"127.0.0.1","localhost",None}:
                            external.append(route.request.url);route.abort()
                        else: route.continue_()
                    context.route("**/*",route_request)
                    page = context.new_page()
                    def page_error(error):
                        errors.append(str(error))
                        print("Browser error:", error.stack, flush=True)
                    page.on("pageerror",page_error)
                    page.set_default_timeout(15000)
                    page.goto("http://127.0.0.1:8018/")
                    page.get_by_label("Username",exact=True).fill("noor")
                    page.get_by_label("Password",exact=True).fill("coffee2025")
                    page.get_by_role("button",name="Log in",exact=True).click()
                    expect(page.get_by_text("Welcome, Noor",exact=True)).to_be_visible()
                    if seed_demo:
                        verify_seeded_demo(page,expect)
                        assert not external, external
                        assert not errors, errors
                        (ROOT/"backend/test-results/noor-demo-browser-result.json").write_text(json.dumps({"reviews":225,"months_checked":12,"patterns":["tasting High","group size Medium"],"plan_progress":"Better","external_requests":external,"browser_errors":errors},indent=2))
                        browser.close()
                        print("Offline seeded Noor demo browser smoke passed")
                        return
                    for _ in range(3):
                        page.get_by_role("button",name="Visitor Feedback",exact=True).click()
                        page.get_by_role("button",name="English",exact=True).click()
                        page.get_by_role("radio",name="5 stars, Excellent",exact=True).click()
                        page.locator("textarea").nth(0).fill("The guide was friendly.")
                        page.get_by_role("button",name="Submit review",exact=True).click()
                        expect(page.get_by_text("Thank you!",exact=True)).to_be_visible(timeout=120000)
                    page.get_by_role("button",name="Noor's Dashboard",exact=True).click()
                    for _ in range(4): page.get_by_role("button",name="0",exact=True).click()
                    page.get_by_role("button",name="Enter",exact=True).click()
                    expect(page.get_by_text("Hi Noor",exact=True)).to_be_visible()
                    page.get_by_role("button",name="All Reviews",exact=False).click()
                    expect(page.locator("article.review")).to_have_count(3)
                    first = page.locator("article.review").first
                    assert first.locator(".swline").first.is_visible()
                    assert "Original English:" in first.inner_text()
                    assert first.locator(".rv-field").first.locator("p").first.get_attribute("lang") == "sw"
                    page.get_by_role("button",name="Home",exact=True).first.click()
                    page.get_by_role("button",name="Plans What",exact=False).click()
                    page.get_by_role("button",name="Guide quality",exact=False).click()
                    expect(page.get_by_text("Confidence: Medium",exact=True)).to_be_visible()
                    page.get_by_role("button",name="Try it",exact=True).click()
                    expect(page.get_by_text("Added to My Plans",exact=True)).to_be_visible()
                    page.get_by_role("button",name="View",exact=True).click()
                    expect(page.get_by_text("Waiting for 3+ new reviews",exact=True)).to_be_visible()
                    page.get_by_role("button",name="Home",exact=True).first.click()
                    page.get_by_role("button",name="Monthly Performance",exact=False).click()
                    page.get_by_role("button",name="Month",exact=True).click()
                    current = page.evaluate('new Date().toLocaleString("en",{month:"long"}) + " " + new Date().getFullYear()')
                    page.get_by_role("button",name=current,exact=False).click()
                    expect(page.get_by_text("5.0",exact=True)).to_be_visible()
                    page.get_by_role("button",name="Home",exact=True).first.click()
                    page.get_by_role("button",name="All Reviews",exact=False).click()
                    page.locator("article.review").first.get_by_role("button",name="More options").click()
                    page.get_by_role("button",name="Delete",exact=True).click()
                    expect(page.locator("article.review")).to_have_count(2)
                    page.get_by_role("button",name="Undo",exact=True).click()
                    expect(page.locator("article.review")).to_have_count(3)
                    page.get_by_role("button",name="Home",exact=True).first.click()
                    page.get_by_role("button",name="My Plans",exact=False).click()
                    page.get_by_role("button",name="More options").click()
                    page.get_by_role("button",name="Move to saved for later",exact=True).click()
                    expect(page.get_by_text("SAVED FOR LATER",exact=True)).to_be_visible()
                    page.get_by_role("button",name="Start trying",exact=True).click()
                    expect(page.get_by_text("TRYING NOW",exact=True)).to_be_visible()
                    page.get_by_role("button",name="More options").click()
                    page.get_by_role("button",name="Mark as done",exact=True).click()
                    expect(page.get_by_text("DONE",exact=True)).to_be_visible()
                    result = page.request.post("http://127.0.0.1:8018/api/reviews",data={"rating":3,"favorite_en":"xyzzy quux 7392"},timeout=120000)
                    assert result.status == 201
                    unknown = result.json()
                    assert unknown["classification_status"] == "not_sure"
                    page.reload()
                    expect(page.get_by_text("Welcome, Noor",exact=True)).to_be_visible()
                    page.get_by_role("button",name="Noor's Dashboard",exact=True).click()
                    page.get_by_role("button",name="Not Sure",exact=False).click()
                    page.get_by_role("button",name="Guide quality · Good experience",exact=True).click()
                    expect(page.get_by_text("All clear",exact=True)).to_be_visible()
                    corrected = page.request.get("http://127.0.0.1:8018/api/reviews/"+unknown["id"]).json()
                    assert corrected["model_prediction"] == unknown["model_prediction"]
                    assert corrected["manual_override"]["topics"][0]["topic"] == "guide_quality"
                    assert not external, external
                    assert not errors, errors
                    output = ROOT/"backend"/"test-results"
                    output.mkdir(exist_ok=True)
                    page.screenshot(path=str(output/"offline-browser.png"))
                    (output/"browser-result.json").write_text(json.dumps({"flows":["login","three visitor submissions","PIN unlock","bilingual reviews","medium-confidence suggestion","accepted plan","monthly statistics","delete and undo","save/start/complete plan","reload persistence","Not Sure manual correction"],"external_requests":external,"browser_errors":errors},indent=2))
                    browser.close()
            finally:
                server.should_exit = True
                thread.join(timeout=30)
                socket.socket.connect = original_connect
    print("Offline browser smoke passed")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeded-demo",action="store_true",help="Check all twelve months using a disposable copy of the seeded database.")
    run(seed_demo=parser.parse_args().seeded_demo)
