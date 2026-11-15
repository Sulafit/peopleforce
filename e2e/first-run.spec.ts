import { expect, test, type Page } from "@playwright/test";

/**
 * The success criterion of the product, end to end, with a refresh at every stage:
 * Landing -> Quiz -> Preview -> Magic link -> Journey map -> First lesson -> Avatar -> XP -> Next lesson -> Tour complete.
 */

const SHOTS = process.env.E2E_SCREENSHOTS;

async function shot(page: Page, name: string, options: { settle?: number; fullPage?: boolean } = {}) {
  if (!SHOTS) return;
  if (options.settle) await page.waitForTimeout(options.settle); // let entrance animations finish
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: options.fullPage ?? true });
}

async function choose(page: Page, label: string) {
  await page.getByRole("radio", { name: label, exact: true }).click();
}

test("first-time user journey survives refreshes and re-login", async ({ page }) => {
  test.setTimeout(180_000);
  const email = `e2e-${Date.now()}@example.com`;

  // Landing
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Turn your skills into a freelance business");
  await shot(page, "01-landing");
  await page.getByRole("link", { name: "Start your freelance journey" }).first().click();

  // Quiz: seven questions, one per screen
  await expect(page.getByText("Question 1 of 7")).toBeVisible();
  await expect(page.getByRole("radio", { name: /Design/ })).toBeDisabled();
  await shot(page, "02-quiz");
  await choose(page, "Software Development");
  await expect(page.getByText("Question 2 of 7")).toBeVisible();
  await choose(page, "Backend / APIs");
  await choose(page, "1–3 years");
  await expect(page.getByText("Question 4 of 7")).toBeVisible();

  await page.reload(); // answers are stored server-side, so the quiz resumes
  await expect(page.getByText("Question 4 of 7")).toBeVisible();
  await page.getByRole("button", { name: "Back" }).click();
  await expect(page.getByRole("radio", { name: "1–3 years" })).toBeChecked();
  await page.getByRole("button", { name: "Continue" }).click();

  await choose(page, "Never");
  await expect(page.getByText("Question 5 of 7")).toBeVisible();
  await page.getByRole("checkbox", { name: "Existing work samples" }).click();
  await page.getByRole("checkbox", { name: "LinkedIn presence" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await choose(page, "Upwork");
  await expect(page.getByText("Question 7 of 7")).toBeVisible();
  await choose(page, "Get my first client");

  // Preview, before any email is asked for
  await expect(page).toHaveURL(/\/start\/plan$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Your path from backend developer to independent freelancer");
  await expect(page.getByText("Prepare your Upwork profile")).toBeVisible();
  await expect(page.getByLabel("Your email")).toHaveCount(0);
  await shot(page, "03-plan");

  // Email -> magic link
  await page.getByRole("button", { name: "Save my journey" }).click();
  await page.getByLabel("Your email").fill("not-an-email");
  await page.getByRole("button", { name: "Email me my link" }).click();
  await expect(page.getByText("Enter a valid email address.")).toBeVisible();
  await page.getByLabel("Your email").fill(email);
  await page.getByRole("button", { name: "Email me my link" }).click();
  await expect(page.getByRole("heading", { name: "Check your inbox" })).toBeVisible();
  await shot(page, "04-link-sent");

  await page.reload();
  await page.getByRole("button", { name: "Save my journey" }).click();
  await expect(page.getByRole("heading", { name: "Check your inbox" })).toBeVisible();

  await page.getByRole("link", { name: "Open the sign-in link" }).click();
  await expect(page.getByRole("heading", { name: "Open your journey" })).toBeVisible();
  await expect(page).toHaveURL(/\/auth\/verify$/); // the token is gone from the address bar
  await page.getByRole("button", { name: "Continue to my journey" }).click();

  // Journey map + tour step 1
  await expect(page).toHaveURL(/\/journey$/);
  const popover = page.locator(".driver-popover");
  await expect(popover).toContainText("Welcome to your journey!");
  await expect(page.getByText("0 XP", { exact: true })).toBeVisible();
  await shot(page, "05-journey-tour");
  await page.reload();
  await expect(popover).toContainText("Welcome to your journey!");
  await popover.getByRole("button", { name: "Start first lesson" }).click();

  // First lesson + tour step 2
  await expect(page).toHaveURL(/\/journey\/lessons\/define-your-offer$/);
  await expect(popover).toContainText("You'll learn by doing.");
  await shot(page, "06-lesson-tour");
  await popover.getByRole("button", { name: "Got it" }).click();

  // The lesson is played one step per screen, one question per screen.
  const next = page.getByRole("button", { name: "Continue" });
  await expect(page.getByText("Step 1 of 5")).toBeVisible();
  await next.click();
  await expect(page.getByText("I build and repair APIs for small product teams")).toBeVisible(); // matched to "Backend / APIs"
  await next.click();
  await expect(next).toBeDisabled(); // a required step cannot be skipped
  const answers: [string, string][] = [
    ["What can you build?", "APIs and integrations between business tools"],
    ["Who might need it?", "Small product teams without a backend developer"],
    ["What specific problem can you solve?", "Their app slows down or breaks as usage grows"],
    ["What relevant experience can you demonstrate?", "Built a practice inventory API with a public repository"],
  ];
  for (const [index, [label, text]] of answers.entries()) {
    await expect(page.getByText(`Question ${index + 1} of 4`)).toBeVisible();
    await page.getByLabel(label).fill(text);
    await page.getByRole("button", { name: index === 3 ? "Save draft" : "Next question" }).click();
  }
  await expect(page.getByRole("button", { name: "Edit answers" })).toBeVisible();
  await shot(page, "07-lesson-step");

  await page.reload(); // the lesson reopens at the first step still to do, with the draft intact
  await expect(page.getByText("Step 5 of 5")).toBeVisible();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await expect(page.getByText("APIs and integrations between business tools")).toBeVisible();
  await next.click();
  await page.getByRole("button", { name: "Skip" }).click(); // coach feedback is optional

  const finish = page.getByRole("button", { name: "Finish lesson" });
  await expect(finish).toBeDisabled();
  await page.getByRole("button", { name: "Save to my profile" }).click();
  await expect(page.getByRole("button", { name: "Saved to your profile" })).toBeVisible();
  await finish.click();

  // Avatar comes after the lesson and before any XP
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Great start! Choose a character to accompany you on your journey.");
  await shot(page, "08-avatar");
  await page.reload(); // interrupted at the avatar step: it comes back
  await expect(dialog).toContainText("Choose a character");
  await dialog.getByRole("radio", { name: "Fox" }).click();
  await dialog.getByRole("button", { name: "Choose this character" }).click();

  // XP celebration
  await expect(dialog).toContainText("You completed your first lesson and earned your first XP.");
  await expect(dialog).toContainText("+40 XP");
  await expect(dialog).toContainText("First Step");
  await expect(dialog).toContainText("Rank up! You are now Explorer.");
  await shot(page, "09-reward", { settle: 600, fullPage: false });
  await shot(page, "09b-reward-settled", { settle: 1800, fullPage: false });
  await page.reload();
  await expect(dialog).toContainText("earned your first XP");
  await expect(page.locator(".confetti")).toHaveCount(1);
  await expect(dialog.getByRole("progressbar")).toBeVisible(); // rank bar fills toward the next rank
  await dialog.getByRole("button", { name: "Continue" }).click();

  // Next lesson unlocked + last tour step, with a small note of overall progress
  await expect(page).toHaveURL(/\/journey$/);
  await expect(page.getByRole("status").filter({ hasText: "40 XP so far" })).toBeVisible();
  await shot(page, "09c-toast", { settle: 500, fullPage: false });
  await expect(popover).toContainText("Your next lesson is ready.");
  await expect(page.getByText("40 XP", { exact: true })).toBeVisible();
  await shot(page, "10-next-lesson");
  await popover.getByRole("button", { name: "Open next lesson" }).click();
  await expect(page).toHaveURL(/\/journey\/lessons\/spot-a-strong-offer$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Spot a strong offer");

  // Tour is finished for good; locked lessons stay locked
  await page.goto("/journey/lessons/write-your-bio");
  await expect(page.getByText("This lesson is still locked.")).toBeVisible();
  await page.goto("/journey");
  await expect(page.getByText("More coming soon")).toBeVisible(); // the path is open-ended
  await expect(page.getByText("Coming soon").first()).toBeVisible();
  await page.waitForTimeout(1500);
  await expect(popover).toHaveCount(0);

  // Daily challenge: a real-world task with a count. Tick it off; partial progress survives a reload.
  await page.getByRole("button", { name: "Open", exact: true }).click();
  await expect(dialog).toContainText("Today's challenge");
  const boxes = dialog.locator(".tally__box");
  const target = await boxes.count();
  expect(target).toBeGreaterThan(0);
  await boxes.nth(0).click();
  await expect(dialog).toContainText(`1 of ${target}`);
  await shot(page, "10b-daily-task", { settle: 500, fullPage: false });
  if (target > 1) {
    await page.reload();
    await expect(page.getByText(`1 of ${target} done. Keep going.`)).toBeVisible();
    await page.getByRole("button", { name: "Continue", exact: true }).click();
    for (let index = 1; index < target; index += 1) {
      await boxes.nth(index).click();
      // The last tick completes the challenge and replaces the boxes with the result.
      if (index < target - 1) await expect(dialog).toContainText(`${index + 1} of ${target}`);
    }
  }
  await expect(dialog).toContainText("1-day streak");
  const earned = Number((await dialog.locator(".reward__xp").innerText()).replace(/\D/g, ""));
  expect(earned).toBeGreaterThan(0);
  const total = 40 + earned;
  await shot(page, "11-daily", { settle: 1200, fullPage: false });
  await dialog.getByRole("button", { name: "Close" }).click();
  await expect(page.getByRole("status").filter({ hasText: `${total} XP so far` })).toBeVisible(); // overall progress note
  await expect(page.getByText(`${total} XP`, { exact: true })).toBeVisible();
  await expect(page.getByText("Come back tomorrow")).toBeVisible();
  await shot(page, "12-journey");

  // Profile: avatar is the way in; rank ladder, streak, achievements, saved work
  await page.getByRole("link", { name: /Your profile/ }).click();
  await expect(page).toHaveURL(/\/journey\/profile$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Explorer");
  await expect(page.getByText(/\d+ XP to Builder/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Freelance offer" })).toBeVisible();
  await expect(page.getByText("Built a practice inventory API with a public repository")).toBeVisible();
  await shot(page, "13-profile");
  await page.getByRole("button", { name: /Your character/ }).click();
  await dialog.getByRole("radio", { name: "Owl" }).click();
  await dialog.getByRole("button", { name: "Choose this character" }).click();
  await expect(page.getByRole("button", { name: /Your character: Owl/ })).toBeVisible();

  // Returning user: sign out, sign in again, nothing repeats
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/journey");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Your email").fill(email);
  // A second email for the same address is rate-limited for a short while; wait it out like a person would.
  const devLink = page.getByRole("link", { name: "Open the sign-in link" });
  await expect(async () => {
    await page.getByRole("button", { name: "Email me a sign-in link" }).click();
    await expect(devLink).toBeVisible({ timeout: 3000 });
  }).toPass({ timeout: 45_000, intervals: [5000] });
  await devLink.click();
  await page.getByRole("button", { name: "Continue to my journey" }).click();
  await expect(page).toHaveURL(/\/journey$/);
  await expect(page.getByText(`${total} XP`, { exact: true })).toBeVisible();
  await page.waitForTimeout(1500);
  await expect(popover).toHaveCount(0);
  await expect(dialog).toHaveCount(0);
});
