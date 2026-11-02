"""Browser-level acceptance checks for the local VIRTUE WISE workflow."""

from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

BASE_URL = "http://127.0.0.1:8000"
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

        # Project edits persist across a full page reload.
        page.get_by_label("Project name").fill("Browser acceptance project")
        page.get_by_label("Goal or question").fill("Verify the complete local workflow.")
        page.get_by_role("button", name="Save project").click()
        expect(page.locator("#notice")).to_contain_text("Saved locally.")
        page.reload(wait_until="networkidle")
        expect(page.get_by_label("Project name")).to_have_value("Browser acceptance project")

        # Statements remain separately visible and can be linked to a hypothesis.
        page.get_by_label("Statement").fill("Two planning meetings overran.")
        page.get_by_label("Source label").fill("Fictional planning notes")
        page.get_by_label("Optional source excerpt").fill("Two meetings exceeded the planned duration.")
        page.get_by_role("button", name="Add statement").click()
        expect(page.locator("#statement-list")).to_contain_text("Two planning meetings overran.")
        statement_id = page.locator("#hypothesis-evidence option").first.get_attribute("value")
        assert statement_id

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
        page.get_by_label("Scenario name").fill("Reduce agenda scope")
        page.get_by_label("Assumptions (one per line)").fill("The agenda can be shortened.\nOwners agree.")
        page.get_by_label("Expected outcome and trade-offs").fill(
            "Meetings may be shorter; some topics may move to follow-up."
        )
        page.get_by_role("button", name="Add scenario").click()
        page.get_by_label("Scenario name").fill("Keep current agenda")
        page.get_by_label("Assumptions (one per line)").fill("All topics remain necessary.")
        page.get_by_label("Expected outcome and trade-offs").fill(
            "Coverage remains broad; overruns may continue."
        )
        page.get_by_role("button", name="Add scenario").click()
        expect(page.locator(".scenario-card")).to_have_count(2)
        expect(page.locator("#scenario-comparison-note")).to_contain_text("descriptive, not scored")

        # Native edit dialog exposes labels and saves changed content.
        page.locator(".scenario-card").filter(has_text="Reduce agenda scope").get_by_role(
            "button", name="Edit"
        ).click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        dialog.get_by_label("Scenario name").fill("Reduce agenda scope carefully")
        dialog.get_by_role("button", name="Save changes").click()
        expect(page.locator(".scenario-card")).to_contain_text(
            "Reduce agenda scope carefully"
        )

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

        assert not page_errors, f"Browser JavaScript errors: {page_errors}"
        browser.close()
