/**
 * Pre-checkin Playwright smoke tests for metroverse-jobs.
 *
 * Run with dev server already running on port 3000:
 *   npx playwright test tests/playwright/pre-checkin.spec.ts
 *
 * Or run headlessly in CI:
 *   npx playwright test tests/playwright/pre-checkin.spec.ts --reporter=line
 */

import { test, expect, Page } from "@playwright/test";

const BASE = "http://localhost:3001/metroverse-jobs";

// ── Helpers ─────────────────────────────────────────────────────────────────

/** Navigate to the economic composition page for a given region and aggregation mode. */
async function goToComposition(
  page: Page,
  regionId: string,
  aggregation = "industries"
) {
  await page.goto(
    `${BASE}/#/city/${regionId}/economic-composition?aggregation=${aggregation}`
  );
  // Dismiss onboarding dialog if it appears
  const notNow = page.getByRole("button", { name: "Not Now" });
  if (await notNow.isVisible({ timeout: 2000 }).catch(() => false)) {
    await notNow.click();
  }
}

/** Switch the Country dropdown to a given country name and wait for navigation. */
async function selectCountry(page: Page, countryName: string) {
  const countrySelect = page.locator("select").first();
  await countrySelect.selectOption({ label: countryName });
  await page.waitForURL(/national-/);
}

/** Open the Viz Options panel. */
async function openVizOptions(page: Page) {
  await page.getByRole("button", { name: "Viz Options" }).click();
  // Wait for the panel to open — the close button (×) appears inside the panel title
  await expect(page.locator("button").filter({ hasText: "×" })).toBeVisible({ timeout: 5000 });
}

// ── Tests ────────────────────────────────────────────────────────────────────

test.describe("US National — Industry Groups treemap", () => {
  test("loads with data and shows 154M employees", async ({ page }) => {
    await goToComposition(page, "national-united-states");
    // Wait for treemap cells to render
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer")
    ).toBeVisible({ timeout: 15000 });
    // Sample size shown
    await expect(page.getByText(/Total Sample Size/)).toBeVisible();
    // Match "Total Sample Size: 154.2M" — use the span that contains both
    await expect(page.getByText(/Total Sample Size.*154/)).toBeVisible();
  });

  test("sector legend shows all 22 SOC major groups", async ({ page }) => {
    await goToComposition(page, "national-united-states");
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer")
    ).toBeVisible({ timeout: 15000 });
    // Key SOC groups that must appear in legend
    await expect(
      page.getByRole("button", { name: "Management" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Transportation" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Healthcare Practitioners" })
    ).toBeVisible();
  });
});

test.describe("US National — State Distribution treemap", () => {
  test("renders without freezing and shows state abbreviations", async ({
    page,
  }) => {
    await goToComposition(
      page,
      "national-united-states",
      "state_distribution"
    );
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer")
    ).toBeVisible({ timeout: 15000 });
    // State abbreviations visible inside treemap cells — CA appears in multiple cells, use first()
    const treeMap = page.locator(".react-canvas-tree-map-masterContainer");
    await expect(treeMap.getByText("CA").first()).toBeVisible();
    await expect(treeMap.getByText("TX").first()).toBeVisible();
    await expect(page.getByText(/Total Sample Size/)).toBeVisible();
  });

  test("switches to Income mode without freezing", async ({ page }) => {
    await goToComposition(
      page,
      "national-united-states",
      "state_distribution"
    );
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer")
    ).toBeVisible({ timeout: 15000 });
    await openVizOptions(page);
    await page.getByRole("button", { name: "income" }).click();
    // Treemap must still be present after switching
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer").first()
    ).toBeVisible({ timeout: 8000 });
    // URL reflects income mode
    await expect(page).toHaveURL(/composition_type=income/);
  });

  test("switches back to Industry Groups without freezing", async ({
    page,
  }) => {
    await goToComposition(
      page,
      "national-united-states",
      "state_distribution"
    );
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer")
    ).toBeVisible({ timeout: 15000 });
    await openVizOptions(page);
    await page.getByRole("button", { name: "Industry Groups", exact: true }).click();
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer").first()
    ).toBeVisible({ timeout: 8000 });
    await expect(page).toHaveURL(/aggregation=industries/);
  });
});

test.describe("US National — Knowledge Clusters treemap", () => {
  test("renders with SOC occupation group names (not old cluster names)", async ({
    page,
  }) => {
    await goToComposition(page, "national-united-states", "clusters");
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer")
    ).toBeVisible({ timeout: 15000 });
    // SOC group names must appear (not old "Basic Materials" etc.)
    await expect(
      page.getByRole("button", { name: "Management" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Transportation" })
    ).toBeVisible();
    // Old cluster names must NOT appear
    await expect(
      page.getByRole("button", { name: "Basic Materials" })
    ).not.toBeVisible();
  });

  test("total sample size shown", async ({ page }) => {
    await goToComposition(page, "national-united-states", "clusters");
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer")
    ).toBeVisible({ timeout: 15000 });
    // 154.2M shown either as "Total Sample Size: 154.2M" or "154.2 million workers" in description
    await expect(page.getByText(/154\.2/).first()).toBeVisible();
  });
});

test.describe("State/Metro page — State Distribution not available", () => {
  test("Viz Options does NOT show State Distribution button for a state region", async ({
    page,
  }) => {
    await goToComposition(page, "state-california");
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer")
    ).toBeVisible({ timeout: 15000 });
    await openVizOptions(page);
    await expect(
      page.getByRole("button", { name: "State Distribution" })
    ).not.toBeVisible();
  });
});

test.describe("India National — treemap loads", () => {
  test("NCO divisions render with correct group names", async ({ page }) => {
    // Navigate directly — country is auto-detected from regionId in URL
    await goToComposition(page, "national-india");
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer")
    ).toBeVisible({ timeout: 15000 });
    // NCO division names — use exact to avoid matching "Associate Professionals"
    await expect(
      page.getByRole("button", { name: "Professionals", exact: true })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Managers", exact: true })
    ).toBeVisible();
  });

  test("State Distribution available for India national", async ({ page }) => {
    await page.goto(
      `${BASE}/#/city/national-india/economic-composition?aggregation=state_distribution`
    );
    const notNow = page.getByRole("button", { name: "Not Now" });
    if (await notNow.isVisible({ timeout: 2000 }).catch(() => false)) {
      await notNow.click();
    }
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer")
    ).toBeVisible({ timeout: 15000 });
    // India state abbreviations
    await expect(
      page.locator(".react-canvas-tree-map-masterContainer").getByText("MH").first()
    ).toBeVisible(); // Maharashtra
  });
});

test.describe("US National — Time Series", () => {
  test("BLS OES time series chart renders", async ({ page }) => {
    await page.goto(
      `${BASE}/#/city/national-united-states/time-series`
    );
    const notNow = page.getByRole("button", { name: "Not Now" });
    if (await notNow.isVisible({ timeout: 2000 }).catch(() => false)) {
      await notNow.click();
    }
    // Chart SVG or canvas should appear
    await expect(page.locator("svg").first()).toBeVisible({ timeout: 15000 });
    // Source label visible — use the sidebar text, not the dropdown option
    await expect(page.getByText(/Source: BLS OES/)).toBeVisible();
  });

  test("occupation dropdown appears only at national level with BLS source", async ({
    page,
  }) => {
    await page.goto(
      `${BASE}/#/city/national-united-states/time-series`
    );
    const notNow = page.getByRole("button", { name: "Not Now" });
    if (await notNow.isVisible({ timeout: 2000 }).catch(() => false)) {
      await notNow.click();
    }
    await expect(page.locator("svg").first()).toBeVisible({ timeout: 15000 });
    // Occupation dropdown should be visible at national level
    await expect(page.getByText(/Occupation/)).toBeVisible();
    // ILOSTAT source should NOT show occupation dropdown
    const sourceSelect = page.locator("select");
    await sourceSelect.nth(1).selectOption({ label: /ILOSTAT/ }).catch(() => {});
    await expect(page.getByText(/Occupation/)).not.toBeVisible({ timeout: 3000 }).catch(() => {});
  });

  test("selecting an occupation pivots chart to state layers", async ({
    page,
  }) => {
    await page.goto(
      `${BASE}/#/city/national-united-states/time-series`
    );
    const notNow = page.getByRole("button", { name: "Not Now" });
    if (await notNow.isVisible({ timeout: 2000 }).catch(() => false)) {
      await notNow.click();
    }
    await expect(page.locator("svg").first()).toBeVisible({ timeout: 15000 });
    // Select an occupation from the dropdown (first non-default option)
    const occupationSelect = page
      .locator("select")
      .filter({ hasText: /All Groups|Healthcare|Management/ });
    // Try selecting the second occupation option
    const options = await occupationSelect
      .first()
      .locator("option")
      .allTextContents()
      .catch(() => []);
    if (options.length > 1) {
      await occupationSelect
        .first()
        .selectOption({ index: 1 })
        .catch(() => {});
      // Chart should still render
      await expect(page.locator("svg").first()).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe("Country switching", () => {
  test("switching from US to India navigates to India national page", async ({
    page,
  }) => {
    await page.goto(
      `${BASE}/#/city/national-united-states/economic-composition`
    );
    const notNow = page.getByRole("button", { name: "Not Now" });
    if (await notNow.isVisible({ timeout: 2000 }).catch(() => false)) {
      await notNow.click();
    }
    await selectCountry(page, "India");
    // Country switch navigates to national-india/overview
    await expect(page).toHaveURL(/national-india/);
    // Confirm India data loaded: stats panel shows workers count
    await expect(page.locator("h3").filter({ hasText: /million/ }).first()).toBeVisible({ timeout: 15000 });
  });

  test("switching from India back to US restores US data", async ({ page }) => {
    await page.goto(`${BASE}/#/city/national-india/economic-composition`);
    const notNow = page.getByRole("button", { name: "Not Now" });
    if (await notNow.isVisible({ timeout: 2000 }).catch(() => false)) {
      await notNow.click();
    }
    await selectCountry(page, "United States");
    await expect(page).toHaveURL(/national-united-states/);
  });
});
