"""Optional dev check: drive the real UI through the acceptance.md demo in headless Chromium.

Not an app dependency. Needs Playwright (1.49.x works on Ubuntu 20.04) and both servers running:
    python scripts/browser_demo_check.py --base http://127.0.0.1:3000 --shots /tmp/shots
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "handoff" / "fixtures"
TIMEOUT = 20_000


def sidebar(page: Page, n: int):
    return page.locator("nav .stagelist li").nth(n - 1)


def status_of(page: Page, n: int, label: str):
    expect(sidebar(page, n)).to_contain_text(label, timeout=TIMEOUT)


def open_stage(page: Page, n: int):
    sidebar(page, n).locator("button").click()
    expect(page.locator("main h2").first).to_contain_text(f"S{n} ", timeout=TIMEOUT)


def run_stage(page: Page, n: int):
    page.get_by_role("button", name=f"S{n} 실행", exact=True).click()
    status_of(page, n, "검토 필요")
    expect(page.locator("main")).to_contain_text("현재 결과 · v", timeout=TIMEOUT)


def approve(page: Page, n: int):
    page.get_by_role("button", name="승인", exact=True).click()
    status_of(page, n, "승인")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:3000")
    ap.add_argument("--shots", default="/tmp/shots")
    args = ap.parse_args()
    shots = Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    project = json.loads((FIX / "project_input.json").read_text(encoding="utf-8"))
    log = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(args.base)
        expect(page.locator("body")).to_contain_text("데모 모드: 사전 작성 산출물 사용", timeout=TIMEOUT)
        page.fill("#name", project["name"])
        page.fill("#idea", project["idea"])
        page.get_by_role("button", name="프로젝트 만들기").click()
        page.wait_for_url(re.compile(r"/projects/"), timeout=TIMEOUT)
        log.append("1-2 project created from fixtures/project_input.json, demo badge shown")

        open_stage(page, 1)
        run_stage(page, 1)
        open_stage(page, 2)
        expect(page.get_by_role("button", name="S2 실행", exact=True)).to_be_disabled()
        log.append("3 S2 locked before S1 approval")
        open_stage(page, 1)
        approve(page, 1)
        open_stage(page, 2)
        run_stage(page, 2)
        expect(page.locator("main")).to_contain_text("Adam: A Method for Stochastic Optimization")
        expect(page.locator("main")).to_contain_text("bundled_snapshot")
        approve(page, 2)
        log.append("4 S2 references with source/date shown, approved")

        open_stage(page, 3)
        run_stage(page, 3)
        page.locator("main textarea").first.fill("반복 seed 확인 계획을 더 분명히 적어 주세요")
        page.get_by_role("button", name="재생성 요청").click()
        expect(page.locator("main")).to_contain_text("현재 결과 · v2", timeout=TIMEOUT)
        page.screenshot(path=str(shots / "s3_regenerated.png"), full_page=True)
        approve(page, 3)
        log.append("5 S3 regenerated with comment -> v2, approved")

        open_stage(page, 4)
        run_stage(page, 4)
        expect(page.locator("main")).to_contain_text("서버 미실행")
        approve(page, 4)
        with page.expect_download() as dl:
            page.get_by_role("button", name="코드 zip 다운로드").click()
        dl.value.save_as(shots / "code.zip")
        log.append("6 S4 approved, code.zip downloaded")

        open_stage(page, 5)
        page.set_input_files("main input[type=file]", str(FIX / "experiment_result.valid.json"))
        page.get_by_role("button", name="업로드").click()
        expect(page.locator("main")).to_contain_text("0.9666666666666667", timeout=TIMEOUT)
        expect(page.locator("main")).to_contain_text("Maximum iterations")
        run_stage(page, 5)
        expect(page.locator("main")).to_contain_text("판단 불가(inconclusive)")
        approve(page, 5)
        log.append("7 valid JSON uploaded, 4 metrics + warnings shown, S5 analysed and approved")

        open_stage(page, 6)
        run_stage(page, 6)
        expect(page.locator("main")).to_contain_text("Related Work")
        approve(page, 6)
        for name, label in (("paper.md", "논문 Markdown"), ("references.bib", "BibTeX")):
            with page.expect_download() as dl:
                page.get_by_role("button", name=label).click()
            dl.value.save_as(shots / name)
        page.screenshot(path=str(shots / "s6_approved.png"), full_page=True)
        log.append("8 S6 approved, paper.md and references.bib downloaded")

        # change propagation
        open_stage(page, 3)
        page.get_by_role("button", name="직접 수정").click()
        body = page.locator("main form textarea").first
        body.fill(body.input_value().replace("같은 split과 seed를 두 학습에 사용한다.",
                                             "같은 split과 seed를 두 학습에 사용한다. 반복 seed 확인은 후속 과제로 둔다."))
        page.get_by_role("button", name="새 버전으로 저장").click()
        expect(page.locator("main")).to_contain_text("승인되지 않은 새 초안", timeout=TIMEOUT)
        status_of(page, 3, "검토 필요")
        approve(page, 3)
        for n in (4, 5, 6):
            status_of(page, n, "오래됨")
        open_stage(page, 4)
        expect(page.locator("main")).to_contain_text("오래됨")
        page.locator("main textarea").first.fill("새 S3 반영")
        page.get_by_role("button", name="재생성 요청").click()
        status_of(page, 4, "검토 필요")
        page.get_by_role("button", name=re.compile(r"^Research Brief")).click()  # open the Research Brief panel (closed by default)
        expect(page.locator("aside.right")).to_contain_text("S3 실험 설계 v3", timeout=TIMEOUT)
        open_stage(page, 5)
        expect(page.get_by_role("button", name="재생성 요청")).to_be_disabled()
        page.screenshot(path=str(shots / "propagation.png"), full_page=True)
        log.append("change propagation: S3 edit saved (not approved) -> approved -> S4-S6 stale; S4 regenerated reads S3 v3; S5 blocked")

        page.get_by_role("tab", name="변경 이력").click()
        expect(page.locator("aside.right")).to_contain_text("S1 v1")
        page.get_by_role("button", name="S1 v1").first.click()
        expect(page.locator(".modal")).to_contain_text("읽기 전용")
        page.get_by_role("button", name="닫기").click()
        log.append("Brief history opened read-only")

        # project deletion (DEVIATIONS D-04)
        page.goto(args.base)
        page.get_by_role("button", name=f"{project['name']} 삭제").first.click()
        expect(page.get_by_role("alertdialog")).to_contain_text("되돌릴 수 없습니다")
        before = page.locator(".pcard").count()
        page.get_by_role("alertdialog").get_by_role("button", name="삭제", exact=True).click()
        expect(page.locator(".pcard")).to_have_count(before - 1, timeout=TIMEOUT)
        log.append("project deleted from the dashboard after confirmation")

        if errors:
            raise SystemExit("page errors: " + " | ".join(errors))
        browser.close()

    print("\n".join("PASS " + line for line in log))


if __name__ == "__main__":
    main()
