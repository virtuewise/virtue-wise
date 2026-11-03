"""Browser-level acceptance checks for the local VIRTUE WISE workflow."""

import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("VIRTUE_WISE_BASE_URL", "http://127.0.0.1:8000")
ROOT = Path(__file__).resolve().parents[1]


def test_core_workflow_and_responsive_layout():
    page_errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(BASE_URL, wait_until="networkidle")
        expect(page.locator("#notice")).to_contain_text("Ready.")
        expect(page.get_by_role("heading", name="Explore with an AI model")).to_be_visible()
        expect(page.locator("#local-ai-consent")).not_to_be_checked()
        expect(page.locator("#ai-provider")).to_be_disabled()
        expect(page.locator("#ai-model")).to_be_disabled()
        expect(page.get_by_role("button", name="Analyze with selected AI")).to_be_disabled()

        # Keyboard users can skip directly to the workspace and navigate its sections.
        page.keyboard.press("Tab")
        expect(page.get_by_role("link", name="Skip to workspace")).to_be_focused()
        page.keyboard.press("Enter")
        expect(page.locator("#main-content")).to_be_in_viewport()
        expect(page.get_by_role("navigation", name="Workspace sections")).to_be_visible()
        expect(page.get_by_role("navigation", name="Workspace sections").get_by_role(
            "link", name="Evidence"
        )).to_have_attribute("href", "#statements-heading")

        # Interactive controls must expose a usable accessible name.
        unnamed_buttons = page.locator("button").evaluate_all(
            "(items) => items.filter((item) => !(item.innerText.trim() || item.getAttribute('aria-label') || item.getAttribute('title'))).length"
        )
        assert unnamed_buttons == 0
        unnamed_fields = page.locator("input:not([type=hidden]), select, textarea").evaluate_all(
            "(items) => items.filter((item) => !(item.labels?.length || item.getAttribute('aria-label') || item.getAttribute('aria-labelledby'))).map((item) => item.id || item.outerHTML.slice(0, 120))"
        )
        assert not unnamed_fields, f"Controls without accessible labels: {unnamed_fields}"
        assert page.locator("main").count() == 1
        assert page.get_by_role("heading", level=1).count() == 1
        expect(page.locator("#notice")).to_have_attribute("role", "status")

        # Conversational intake creates a reviewable draft, saves once, and persists.
        intake_text = "Explore planning delays\n\nThe team observed two meetings running over time."
        page.locator("#intake-text").fill(intake_text)
        page.get_by_role("button", name="Build my starting workspace").click()
        expect(page.locator("#intake-preview")).to_be_visible()
        expect(page.locator("#intake-preview")).to_contain_text("Input statements to preserve (2)")
        expect(page.locator("#intake-preview")).to_contain_text("What evidence or source would help verify")
        page.get_by_role("button", name="Save this starting workspace").click()
        expect(page.locator("#notice")).to_contain_text("starting workspace has been saved")
        expect(page.locator("#statement-list")).to_contain_text("The team observed two meetings running over time.")
        page.reload(wait_until="networkidle")
        expect(page.locator("#statement-list")).to_contain_text("The team observed two meetings running over time.")

        # Project details remain editable but are secondary to conversational intake.
        page.locator("details").filter(has_text="Edit project details manually").locator("summary").click()
        expect(page.get_by_label("Project name")).to_have_value("Explore planning delays")
        page.get_by_label("Project name").fill("Browser acceptance project")
        page.get_by_label("Goal or question").fill("Verify the complete local workflow.")
        page.get_by_role("button", name="Save project details").click()
        expect(page.locator("#notice")).to_contain_text("Saved locally.")
        page.reload(wait_until="networkidle")
        page.locator("details").filter(has_text="Edit project details manually").locator("summary").click()
        expect(page.get_by_label("Project name")).to_have_value("Browser acceptance project")

        # Statements remain separately visible and can be linked to a hypothesis.
        page.locator("details").filter(has_text="Add a statement manually").locator("summary").click()
        page.locator("#statement-text").fill("Two planning meetings overran.")
        page.get_by_label("Source label").fill("Fictional planning notes")
        page.get_by_label("Optional source excerpt").fill("Two meetings exceeded the planned duration.")
        page.get_by_role("button", name="Add statement").click()
        expect(page.locator("#statement-list")).to_contain_text("Two planning meetings overran.")
        statement_id = page.locator("#hypothesis-evidence option").last.get_attribute("value")
        assert statement_id

        page.locator("details").filter(has_text="Add a hypothesis manually").locator("summary").click()
        page.get_by_label("Possible relationship or explanation").fill(
            "Agenda scope may contribute to overruns."
        )
        page.get_by_label("Why might this be true?").fill(
            "The fictional notes record repeated overruns; other causes remain possible."
        )
        page.get_by_label("Evidence statements").select_option(statement_id)
        page.get_by_label("Uncertainty").select_option("tentative")
        page.get_by_role("button", name="Add hypothesis").click()
        expect(page.locator("#hypothesis-list")).to_contain_text(
            "Agenda scope may contribute to overruns."
        )
        expect(page.locator("#hypothesis-list")).to_contain_text(
            "Evidence: Two planning meetings overran."
        )

        # Explicit human review remains separate from the source statement.
        page.get_by_role("textbox", name="Review note for Agenda scope may contribute to overruns.").fill(
            "Review the agenda and compare with other possible causes."
        )
        page.get_by_role("button", name="Accept").click()
        expect(page.locator("#hypothesis-list")).to_contain_text("accepted")
        expect(page.locator("#hypothesis-list")).to_contain_text(
            "Review note: Review the agenda and compare with other possible causes."
        )

        # Scenarios are displayed descriptively, without scores.
        page.locator("details").filter(has_text="Add a scenario manually").locator("summary").click()
        page.get_by_label("Scenario name").fill("Reduce agenda scope")
        page.get_by_label("Assumptions (one per line)").fill("The agenda can be shortened.\nOwners agree.")
        page.get_by_label("Expected outcome and trade-offs").fill(
            "Meetings may be shorter; some topics may move to follow-up."
        )
        page.get_by_role("button", name="Add scenario").click()
        expect(page.get_by_label("Scenario name")).to_be_disabled()
        expect(page.get_by_role("button", name="Add scenario")).to_be_disabled()
        expect(page.locator(".scenario-card")).to_have_count(1)
        expect(page.get_by_label("Scenario name")).to_be_enabled()
        page.get_by_label("Scenario name").fill("Keep current agenda")
        page.get_by_label("Assumptions (one per line)").fill("All topics remain necessary.")
        page.get_by_label("Expected outcome and trade-offs").fill(
            "Coverage remains broad; overruns may continue."
        )
        page.get_by_role("button", name="Add scenario").click()
        expect(page.locator(".scenario-card")).to_have_count(2)
        expect(page.locator("#scenario-comparison-note")).to_contain_text("descriptive, not scored")

        # Dynamically rendered controls retain accessible names after records are added.
        unnamed_dynamic_buttons = page.locator("button").evaluate_all(
            "(items) => items.filter((item) => !(item.innerText.trim() || item.getAttribute('aria-label') || item.getAttribute('title'))).length"
        )
        assert unnamed_dynamic_buttons == 0
        unnamed_dynamic_fields = page.locator("input:not([type=hidden]), select, textarea").evaluate_all(
            "(items) => items.filter((item) => !(item.labels?.length || item.getAttribute('aria-label') || item.getAttribute('aria-labelledby'))).map((item) => item.id || item.outerHTML.slice(0, 120))"
        )
        assert not unnamed_dynamic_fields, f"Dynamic controls without accessible labels: {unnamed_dynamic_fields}"

        # Native edit dialog supports Escape, exposes its name, and restores focus.
        edit_button = page.locator(".scenario-card").filter(has_text="Reduce agenda scope").get_by_role(
            "button", name="Edit"
        )
        edit_button.click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        expect(dialog).to_have_attribute("aria-labelledby", "editor-dialog-title")
        expect(dialog.get_by_role("heading", name="Edit scenario")).to_be_visible()
        expect(dialog.get_by_label("Scenario name")).to_be_focused()
        page.keyboard.press("Escape")
        expect(dialog).not_to_be_visible()
        expect(edit_button).to_be_focused()

        # Reopen the dialog and verify keyboard-accessible editing and saving.
        edit_button.click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        dialog.get_by_label("Scenario name").fill("Reduce agenda scope carefully")
        dialog.get_by_role("button", name="Save changes").click()
        expect(
            page.locator(".scenario-card").filter(has_text="Reduce agenda scope carefully")
        ).to_be_visible()

        # JSON export is downloadable; validated import restores the documented demo.
        with page.expect_download() as download_info:
            page.get_by_role("link", name="Export JSON").click()
        download = download_info.value
        assert download.suggested_filename == "virtue-wise-model.json"

        page.locator("#import-file").set_input_files(ROOT / "examples" / "demo-project.json")
        expect(page.locator("#notice")).to_contain_text("JSON model imported and validated.")
        expect(page.locator("#project-title")).to_have_value(
            "Improve a small team planning cycle"
        )
        expect(page.locator("#statement-list li")).to_have_count(3)
        expect(page.locator("#hypothesis-list li")).to_have_count(1)
        expect(page.locator(".scenario-card")).to_have_count(2)

        # Stale browser edits receive a clear recovery instruction, never an overwrite.
        page.locator("details").filter(has_text="Edit project details manually").locator("summary").click()
        page.get_by_label("Project name").fill("Stale tab edit")
        page.route("**/api/model", lambda route: route.fulfill(
            status=412, content_type="application/json", body='{"detail":"stale revision"}'
        ) if route.request.method == "PUT" else route.continue_())
        page.get_by_role("button", name="Save project details").click()
        expect(page.locator("#notice")).to_contain_text("changed elsewhere")
        expect(page.get_by_role("button", name="Reload latest workspace")).to_be_visible()
        page.unroute_all()
        page.get_by_role("button", name="Reload latest workspace").click()
        expect(page.locator("#notice")).to_contain_text("Ready.")

        # Provider throttling is described in actionable, non-technical language.
        page.route("**/api/analysis/status", lambda route: route.fulfill(
            status=429, content_type="application/json", body='{"detail":"too many requests"}'
        ))
        page.get_by_role("button", name="Find available AI models").click()
        expect(page.locator("#local-ai-status")).to_contain_text("rate-limiting requests")
        page.unroute_all()
        page.route("**/api/analysis/status", lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"The provider rate limit was reached. Wait and try again."}'
        ))
        page.get_by_role("button", name="Find available AI models").click()
        expect(page.locator("#local-ai-status")).to_contain_text("provider rate limit was reached")
        page.unroute_all()

        # Destructive action requires confirmation and returns an empty workspace.
        page.get_by_role("button", name="Delete local model").click()
        expect(page.locator("#notice")).to_contain_text("Local model deleted.")
        expect(page.locator("#statement-count")).to_have_text("0")
        expect(page.locator("#hypothesis-count")).to_have_text("0")
        expect(page.locator("#scenario-count")).to_have_text("0")

        # Narrow layouts should not create horizontal document overflow.
        page.set_viewport_size({"width": 375, "height": 812})
        expect(page.locator("body")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.set_viewport_size({"width": 640, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        # A 640 CSS-pixel layout viewport approximates a 1280px desktop at 200% zoom.
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        assert not page_errors, f"Browser JavaScript errors: {page_errors}"
        browser.close()
