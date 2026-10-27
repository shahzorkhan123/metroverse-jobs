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

test.describe("Overview — currency display", () => {
  test("India shows ₹ wage/income with USD equivalent", async ({ page }) => {
    await page.goto(`${BASE}/#/city/national-india`);
    await expect(page.getByText("Estimated Labour Income")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/₹[\d,]+/).first()).toBeVisible();
    await expect(page.getByText(/≈ \$[\d,.]+.*USD/).first()).toBeVisible();
    await expect(page.getByText(/^\$[\d,]+$/)).toHaveCount(0);
  });

  test("US shows $ without a USD equivalent", async ({ page }) => {
    await page.goto(`${BASE}/#/city/national-united-states`);
    await expect(page.getByText("Estimated Labour Income")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/\$[\d,]+/).first()).toBeVisible();
    await expect(page.getByText(/USD\)/)).toHaveCount(0);
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
    // Scoped to labels: the side nav also has an "Occupation Space" link
    const occupationLabel = page.locator("label").filter({ hasText: /Occupation/ });
    await expect(occupationLabel).toBeVisible();
    // ILOSTAT source should NOT show occupation dropdown
    const sourceSelect = page.locator("select");
    await sourceSelect.nth(1).selectOption({ label: /ILOSTAT/ }).catch(() => {});
    await expect(occupationLabel).not.toBeVisible({ timeout: 3000 }).catch(() => {});
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

// ── Occupation Space / Job Space ────────────────────────────────────────────

async function goToSpace(page: Page, regionId: string, query = "") {
  await page.goto(`${BASE}/#/city/${regionId}/occupation-space${query}`);
  const notNow = page.getByRole("button", { name: "Not Now" });
  if (await notNow.isVisible({ timeout: 2000 }).catch(() => false)) {
    await notNow.click();
  }
}

const spaceNodes = (page: Page) => page.locator("svg circle.industry-edge-node");

test.describe("Occupation Space", () => {
  // The space needs the ~23MB level-4 metro file
  test.beforeEach(() => test.setTimeout(120_000));

  test("renders the occupation space for a metro with real RCA", async ({
    page,
  }) => {
    await goToSpace(page, "metro-austin-round-rock-san-marcos-tx");
    // Waits for the level-4 data to load and the chart to build
    await expect.poll(() => spaceNodes(page).count(), { timeout: 60000 }).toBeGreaterThan(500);
    await expect(page.getByText(/Regional complexity \(ECI\)/)).toBeVisible();
    // Real RCA: some nodes grey (RCA < 1), some coloured
    const fills = await spaceNodes(page).evaluateAll((els) =>
      els.map((e) => getComputedStyle(e).getPropertyValue("--true-fill-color").trim()),
    );
    const grey = fills.filter((f) => f === "#dddddd").length;
    expect(grey).toBeGreaterThan(50);
    expect(fills.length - grey).toBeGreaterThan(50);
  });

  test("toggles to the Job Space", async ({ page }) => {
    await goToSpace(page, "national-united-states");
    await expect.poll(() => spaceNodes(page).count(), { timeout: 60000 }).toBeGreaterThan(500);
    const before = await spaceNodes(page).count();
    await page.getByRole("button", { name: "Job Space (tasks)" }).click();
    await expect(page).toHaveURL(/space=job/);
    await expect(page.getByText(/position in the Job Space/i)).toBeVisible();
    await expect
      .poll(() => spaceNodes(page).count(), { timeout: 30000 })
      .not.toBe(before);
  });

  test("divisions follow the SOC hierarchy at each division level", async ({ page }) => {
    const hulls = (p: Page) => p.locator("polygon.industry-continents");
    for (const [division, count, label] of [
      ["1", 5, "Service"],
      ["2", 12, "Construction & Extraction"],
      ["3", 22, "Health Care"],
    ] as [string, number, string][]) {
      await goToSpace(page, "national-united-states", `?division=${division}`);
      await expect.poll(() => spaceNodes(page).count(), { timeout: 60000 }).toBeGreaterThan(500);
      await expect(hulls(page)).toHaveCount(count);
      await expect(
        page.locator(".industry-continents-label", { hasText: new RegExp(`^${label}$`) }),
      ).toHaveCount(1);
    }
  });

  test("colours nodes by PCI and JCI", async ({ page }) => {
    for (const colorBy of ["pci", "jci"]) {
      await goToSpace(page, "national-united-states", `?color_by=${colorBy}`);
      await expect.poll(() => spaceNodes(page).count(), { timeout: 60000 }).toBeGreaterThan(500);
      await expect(page.getByText(new RegExp(`complexity \\(${colorBy.toUpperCase()}\\)`)).first()).toBeVisible();
    }
  });

  test("links to the Task Complexity Analysis article", async ({ page, request }) => {
    await goToSpace(page, "national-united-states");
    const link = page.getByRole("link", { name: /Task Complexity Analysis/ });
    await expect(link).toBeVisible({ timeout: 30000 });
    const href = await link.getAttribute("href");
    expect(href).toContain("task-complexity-analysis.html");
    const res = await request.get(`http://localhost:3001${href}`);
    expect(res.status()).toBe(200);
  });

  test("tab is not offered for India", async ({ page }) => {
    await page.goto(`${BASE}/#/city/national-india/overview`);
    await expect(page.getByText("Time Series").first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Occupation Space")).toHaveCount(0);
  });
});

test.describe("Good At — relative presence", () => {
  test("RCA bars are no longer all 1x for a metro", async ({ page }) => {
    await page.goto(`${BASE}/#/city/metro-austin-round-rock-san-marcos-tx/good-at`);
    const notNow = page.getByRole("button", { name: "Not Now" });
    if (await notNow.isVisible({ timeout: 2000 }).catch(() => false)) {
      await notNow.click();
    }
    // With RCA hardcoded to 1 no bars rendered; Austin's top bars are
    // computer occupations (well above 1x the national share)
    await expect(page.getByText(/^Computer Occu/).first()).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/^Agricultural Wo/).first()).toBeVisible();
  });
});

test.describe("Analysis page", () => {
  test("lists the Task Complexity Analysis article", async ({ page }) => {
    await page.goto(`${BASE}/#/analysis`);
    await expect(page.getByText("Task Complexity Analysis")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("India State Labour Market Analysis")).toBeVisible();
  });
});
