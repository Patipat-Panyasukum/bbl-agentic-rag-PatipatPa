import { access, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "playwright-core";

const edgePath =
  process.env.EDGE_PATH ||
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.DEMO_UI_URL || "http://127.0.0.1:3000";
const captureLiveAnswer = process.env.LIVE_UI_SMOKE === "1";
const captureAllScenarios = process.env.CAPTURE_ALL_DEMO === "1";
const outputDirectory = resolve(import.meta.dirname, "../../docs/assets");

await access(edgePath);
await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch({
  executablePath: edgePath,
  headless: true,
});

async function enterProfile(page, employeeId) {
  await page.locator("label.profile-row", { hasText: employeeId }).click();
  await page.getByRole("button", { name: `Enter as ${employeeId}` }).click();
  await page.waitForURL(`${baseUrl}/chat`);
  await page
    .locator('.graph-status[data-status="online"]')
    .waitFor({ timeout: 15000 });
}

async function changeProfile(page) {
  const profileButton = page.locator('button[aria-label^="Employee profile"]');
  await profileButton.click();
  await page.getByRole("button", { name: "Change demo profile" }).click();
  await page.getByRole("heading", { name: "Select a demo profile" }).waitFor();
}

async function openHistory(page) {
  await page.getByRole("link", { name: "Chat history" }).click();
  await page.waitForURL(`${baseUrl}/history`);
  await page.getByRole("heading", { name: "Chat history" }).waitFor();
  await page
    .getByText("Saved LangGraph threads", { exact: true })
    .waitFor({ timeout: 15000 });
}

async function returnToChat(page) {
  await page.getByRole("link", { name: "Return to chat" }).first().click();
  await page.waitForURL(`${baseUrl}/chat`);
}

async function ask(page, question, expectedText) {
  await page.getByPlaceholder("Ask a benefits question...").fill(question);
  await page.getByRole("button", { name: "Send" }).click();
  await page.getByRole("button", { name: "Send" }).waitFor({ timeout: 120000 });
  await page
    .locator(".markdown-content", { hasText: expectedText })
    .last()
    .waitFor({ timeout: 15000 });
}

async function assertComposerIsOutsideMessagePane(page) {
  const messagePane = await page.locator(".chat-scroll").boundingBox();
  const composer = await page.locator(".chat-composer-zone").boundingBox();
  if (!messagePane || !composer) {
    throw new Error("Could not measure the message pane and composer");
  }
  if (messagePane.y + messagePane.height > composer.y + 1) {
    throw new Error("The message pane overlaps the chat composer");
  }
}

try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 960 },
  });
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Select a demo profile" }).waitFor();
  await page.screenshot({
    path: resolve(outputDirectory, "demo-login.png"),
    fullPage: true,
  });

  await enterProfile(page, "E001");
  const profileButton = page.locator(
    'button[aria-label="Employee profile E001"]',
  );
  await profileButton.hover();
  const profileCard = page.locator(".employee-profile-card");
  await profileCard.getByText("E001", { exact: true }).waitFor();
  await page.waitForTimeout(200);
  await page.screenshot({
    path: resolve(outputDirectory, "demo-chat-profile-e001.png"),
    fullPage: true,
  });

  await openHistory(page);
  await page.screenshot({
    path: resolve(outputDirectory, "demo-chat-history-e001.png"),
    fullPage: true,
  });
  await returnToChat(page);

  if (!captureLiveAnswer) {
    await changeProfile(page);
  }

  if (captureLiveAnswer) {
    await ask(page, "ค่ารักษาพยาบาลผู้ป่วยนอกเบิกได้เท่าไร", "14,250");
    const activityLog = page.locator(".agent-activity").last();
    await activityLog.getByText("4 of 4 observable steps").waitFor();
    await activityLog
      .getByText("Returned 3 policy excerpts with profile applicability")
      .waitFor();
    const evidenceToggle = activityLog.getByText("View retrieved evidence");
    await evidenceToggle.click();
    await activityLog.getByText("MED-OPD-GENERAL-JL2-8").waitFor();
    await assertComposerIsOutsideMessagePane(page);
    await page.screenshot({
      path: resolve(outputDirectory, "demo-chat-evidence-expanded.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await assertComposerIsOutsideMessagePane(page);
    await page.screenshot({
      path: resolve(outputDirectory, "demo-chat-evidence-expanded-mobile.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 1440, height: 960 });
    await evidenceToggle.click();
    const activitySummary = activityLog.locator(":scope > summary");
    await activitySummary.click();
    await activitySummary.click();
    const answer = await page.locator(".markdown-content").last().textContent();
    if (answer?.toLowerCase().includes("insufficient")) {
      throw new Error("The Thai OPD query incorrectly returned an abstention");
    }
    await page.locator(".markdown-content").last().scrollIntoViewIfNeeded();
    await page.screenshot({
      path: resolve(outputDirectory, "demo-chat-opd-th-e001.png"),
      fullPage: true,
    });
    await openHistory(page);
    const savedConversation = page.locator(".history-item").first();
    await savedConversation.getByRole("link", { name: "Open conversation" }).waitFor();
    await savedConversation
      .getByRole("link", { name: "Open conversation" })
      .click();
    await page.waitForURL((url) => url.pathname === "/chat" && url.searchParams.has("threadId"));
    await page.locator(".markdown-content", { hasText: "14,250" }).last().waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    await activityLog.scrollIntoViewIfNeeded();
    await page.screenshot({
      path: resolve(outputDirectory, "demo-chat-activity-mobile.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 1440, height: 960 });

    await ask(
      page,
      "นโยบายสำหรับพนักงานระดับ JL8 เบิกค่ารักษาพยาบาลผู้ป่วยนอกได้เท่าไร",
      "14,250",
    );
    const policyScopeActivity = page.locator(".agent-activity").last();
    await policyScopeActivity
      .getByText("Returned 3 policy excerpts with profile applicability")
      .waitFor();
    const policyScopeAnswer = await page
      .locator(".markdown-content")
      .last()
      .textContent();
    if (
      !policyScopeAnswer?.includes("MED-OPD-GENERAL-JL2-8") ||
      !policyScopeAnswer.includes("E001 (JL3)")
    ) {
      throw new Error(
        "The JL8 policy-scope answer did not include OPD evidence and E001 applicability",
      );
    }
    await page.locator(".markdown-content").last().scrollIntoViewIfNeeded();
    await page.screenshot({
      path: resolve(outputDirectory, "demo-chat-policy-jl8-e001.png"),
      fullPage: true,
    });

    const hideTools = page.getByRole("switch", { name: "Hide tool calls" });
    await hideTools.click();
    if ((await page.locator(".agent-activity").count()) !== 0) {
      throw new Error(
        "Agent activity remained visible after enabling Hide tool calls",
      );
    }

    if (captureAllScenarios) {
      const scenarios = [
        {
          employeeId: "E003",
          question:
            "How much OPD can I claim per visit and how many visits per year?",
          expectedText: "300",
          screenshot: "demo-chat-opd-e003.png",
        },
        {
          employeeId: "E002",
          question: "What is my inpatient room and food limit?",
          expectedText: "3,500",
          screenshot: "demo-chat-ipd-e002.png",
        },
        {
          employeeId: "E001",
          question: "Where can I park my car?",
          expectedText: "insufficient to answer",
          screenshot: "demo-chat-insufficient-e001.png",
        },
      ];

      for (const scenario of scenarios) {
        await changeProfile(page);
        await enterProfile(page, scenario.employeeId);
        await ask(page, scenario.question, scenario.expectedText);
        await page.locator(".markdown-content").last().scrollIntoViewIfNeeded();
        await page.screenshot({
          path: resolve(outputDirectory, scenario.screenshot),
          fullPage: true,
        });
      }
    }
  }

  const mobilePage = await browser.newPage({
    viewport: { width: 390, height: 844 },
  });
  await mobilePage.goto(baseUrl, { waitUntil: "networkidle" });
  await mobilePage
    .getByRole("heading", { name: "Select a demo profile" })
    .waitFor();
  await mobilePage.screenshot({
    path: resolve(outputDirectory, "demo-login-mobile.png"),
    fullPage: true,
  });
  await enterProfile(mobilePage, "E003");
  await mobilePage
    .locator('button[aria-label="Employee profile E003"]')
    .click();
  await mobilePage
    .locator(".employee-profile-card")
    .getByText("E003", { exact: true })
    .waitFor();
  await mobilePage.waitForTimeout(200);
  await mobilePage.screenshot({
    path: resolve(outputDirectory, "demo-chat-mobile.png"),
    fullPage: true,
  });
  await mobilePage
    .locator('button[aria-label="Employee profile E003"]')
    .click();
  await openHistory(mobilePage);
  await mobilePage.screenshot({
    path: resolve(outputDirectory, "demo-chat-history-mobile.png"),
    fullPage: true,
  });
  await mobilePage.close();

  if (consoleErrors.length) {
    throw new Error(`Browser console errors:\n${consoleErrors.join("\n")}`);
  }

  console.log(
    `UI smoke passed (${captureLiveAnswer ? "live graph" : "layout only"}).`,
  );
} finally {
  await browser.close();
}
