import { test, expect } from "@playwright/test";
const BASE = "http://localhost:3001/metroverse-jobs";

test("analysis article link opens the HTML article, not the root page", async ({ page, context }) => {
  await page.goto(`${BASE}/#/analysis`);
  await expect(page.getByText("India State Labour Market Analysis")).toBeVisible({ timeout: 10000 });

  // Click the article card — opens in new tab (target=_blank)
  const [articlePage] = await Promise.all([
    context.waitForEvent("page"),
    page.getByText("Read article →").click(),
  ]);
  await articlePage.waitForLoadState("domcontentloaded");

  console.log("Article URL:", articlePage.url());

  // Should show the Jupyter notebook HTML h1 title, not the React app
  await expect(articlePage.getByRole("heading", { name: /India State Labour Market Analysis/ })).toBeVisible({ timeout: 10000 });
  // Jupyter output has "In [" cells or specific analysis content
  await expect(articlePage.getByText(/Agriculture|Employment|Wage/i).first()).toBeVisible();
  // Should NOT show React app chrome (the landing page search box)
  await expect(articlePage.getByText("Pick a region")).not.toBeVisible();
});
