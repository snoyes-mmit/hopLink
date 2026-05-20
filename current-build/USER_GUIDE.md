# URL Health Checker — User Guide

A simple desktop tool that checks every URL in your Excel file to see which links still work.

---

## What this tool does

If you keep a spreadsheet of URLs — vendor websites, reference links, supplier portals, anything — links go stale over time. Pages get moved, companies disappear, sites change addresses.

This tool opens your Excel file, visits every URL, and produces a tidy report listing only the URLs that didn't work — along with the exact cell each one is in, so you can fix them quickly.

It will check **thousands of URLs in a few minutes**. You don't have to do anything during the run.

---

## How to use it

### Step 1 — Open the app

Double-click the application (`URL Health Checker.exe` on Windows, `URL Health Checker.app` on Mac).

### Step 2 — Add your Excel file

Either:
- **Drag your `.xlsx` file** onto the dotted area at the top of the window, **or**
- **Click the dotted area** to open a file picker.

The app remembers the last file you used, so next time you open it, your previous file will already be loaded.

### Step 3 — Pick the sheet (the column is optional)

Two dropdowns appear after you load a file:
- **Sheet** — which tab in your workbook to look at.
- **Column** — which column contains the URLs. Defaults to **"Auto-detect — scan every column"**, meaning HopLink will find URLs anywhere on the sheet without you having to point at a specific column.

The app **auto-picks** the most likely sheet for you. Most of the time you don't need to change anything: just glance at the sheet name and click **Check URLs**.

You only need to touch the **Column** dropdown if you want to restrict the scan to a single column — for example, on a sheet where some URLs are reference material you don't care about. In that case, pick the column from the dropdown and the scan will be limited to it.

### Step 4 — Click "Check URLs"

The button is the big blue one in the middle. Click it.

While the check runs, you'll see:
- A progress bar showing how many URLs have been checked.
- Live counters: **OK**, **Broken**, **Possibly blocked**.
- An estimated time remaining.

You can use other apps during the run — the tool runs in the background and won't lock up your computer.

If you change your mind, click **Cancel** to stop. Already-checked URLs are discarded.

### Step 5 — Save the results

When the run finishes, you'll see a summary like:

> ✅ Checked 2,315 URLs.
> • Broken: 12
> • Possibly blocked: 54

Click **"Save Results…"** and pick where to save the report. The default filename is `url_issues_<today's-date>.xlsx`.

After saving, click **"Show in folder"** to open the location of the report.

---

## Understanding the report

The report is an Excel file with **two sheets**:

### Sheet 1: "Broken URLs"

These links **don't work**. Most are 404 ("page not found") or DNS errors (the website doesn't exist anymore). For each one you'll see:

- **URL** — the link.
- **Cell Location(s)** — exactly where in your original file the URL appears (e.g. `Sheet1!B12`). If the same URL appears in multiple cells, all locations are listed.
- **HTTP Code** — the technical code returned. 404 means "not found", 500 means "server error", etc.
- **Error Detail** — a short description of what went wrong.
- **Final URL** — where the link redirected to (sometimes a redirect lands on a broken page).
- **Response Time** and **Checked At** — for reference.

These usually need to be **updated or removed** from your original file.

### Sheet 2: "Possibly Blocked"

These links **probably still work in a browser**, but the tool couldn't confirm because the website is blocking automated checks. You'll see the same columns as above, plus:

- **Likely Reason** — e.g. "Cloudflare bot protection", "Rate limited", "Akamai / bot manager".

These are worth a **manual spot-check**. Open one or two in your browser. If they work fine for you, they're probably fine — the website just doesn't like robots.

If a whole bunch of URLs from the same domain show up here, that's the website blocking the tool, not bad URLs. You can ignore that domain or check a couple manually.

### "All Clear" report

If every URL worked, the report is just one sheet that says "✅ No URL issues found." — proof for your records that the check ran.

---

## Common Questions

### Why are some sites "blocked"?

Many websites have anti-bot protection (Cloudflare, Akamai, etc.) that blocks automated traffic — including this tool. They're not broken; they just don't trust automated requests. If a link works for you in a browser, it's fine.

### Why didn't my file load?

Most common reasons:
- **The file is open in Excel.** Close it in Excel first, then try again.
- **It's a `.xls` file (older format).** Open it in Excel and use *Save As* to save it as `.xlsx`.
- **It's password-protected.** This tool doesn't handle password-protected workbooks. Save an unprotected copy and use that.

### What about URLs in formulas like `=HYPERLINK(...)`?

Those work — the tool reads the cached cell value, so it sees the resulting URL.

### Can I check a URL list that isn't in Excel?

Not from this app. If you need that, the command-line version (for technical users) accepts plain text files. Otherwise, paste your URLs into a one-column Excel file and you're set.

### What should I actually do with the results?

Most teams:
1. Filter the "Broken URLs" sheet by domain — broken patterns are often clustered.
2. Update or remove broken links from the original file.
3. Spot-check the "Possibly Blocked" sheet by opening 2–3 in a browser. If they work, leave them alone.

### Will this damage anything?

No. The tool only **reads** your file — it never modifies the original. The report is a separate new file.

### How long does it take?

Roughly:
- 1,000 URLs → about a minute
- 10,000 URLs → 5–15 minutes
- 100,000 URLs → 30–60 minutes

It depends on how fast websites respond.

### Does it need internet?

Yes — the tool needs internet to visit each URL. If you're on a corporate VPN or behind a proxy, things should still work; the tool uses your computer's normal network settings.

---

## Known Limitations

- **Some domains will always show as "Possibly Blocked."** That's their anti-bot protection, not a bug in this tool. They'd block any automated checker.
- **The tool only checks if a URL responds with a 200 OK.** It doesn't check if the page *content* is meaningful. A site that returns "Page Not Found" with a 200 status code (yes, this happens) will be reported as OK.
- **Login-protected pages will usually show as broken.** If a page requires a login, the tool gets a "401 Unauthorized" or similar. There's no way around this without your credentials.
- **JavaScript-only pages.** Some modern sites build the page entirely with JavaScript. The tool checks the underlying URL, not the rendered page.
- **Corporate proxies and VPNs** can cause unusual results. If everything fails on your work network but works on your home network, that's almost certainly the proxy.

---

## Troubleshooting

### The app won't start

- **Windows:** If Windows SmartScreen blocks it, click *More info* → *Run anyway*. (This is a one-time prompt for unsigned apps. Ask your IT department if it keeps happening.)
- **macOS:** If macOS says "the app is damaged" or "from an unidentified developer", right-click the app icon and choose *Open* — this only needs to be done once.

### "Cannot save here" when saving the report

The folder you picked is probably read-only, or the report file is already open in Excel. Pick a different folder, or close the previous report first.

### The progress bar is stuck

Some URLs simply take a long time. Look at the counters underneath — if **Checked** is still going up, it's working. If you really think it's stuck, click **Cancel** and try again with a smaller test file (10–20 rows) to confirm the tool itself works.

### Lots of URLs are showing as "Possibly Blocked"

Two common causes:

1. **You're on a corporate network with a strict firewall.** Try from a regular network.
2. **Your input has a lot of URLs from the same big company** (Google, Amazon, etc.). They block automated traffic by default. Spot-check a few in a browser — they're probably fine.

### I want to start over

Close the app and reopen it. Or just drop a different file.

### I think the tool has a bug

There's a log file that captures errors and run summaries. Help text:

- **Windows:** `%APPDATA%\urlcheck\logs\urlchecker.log`
- **macOS:** `~/Library/Logs/urlcheck/urlchecker.log`

If you report an issue, attach this log file — it usually contains everything needed to diagnose what went wrong.

### Restart fixes weird stuff

If things look strange (settings remembered wrong, dropdowns not populating), close the app and reopen it. That fixes 90% of intermittent issues.

---

## A note on what "checking a URL" really means

When this tool checks a URL, it sends a polite "are you there?" request to the web server, the same kind your browser sends. It reads only enough of the response to know whether the page exists — it doesn't download whole pages, run JavaScript, or click through anything.

Servers can choose to respond, redirect, refuse, or ignore us. The tool reports faithfully what each server said.

For URLs that "possibly blocked," the most reliable next step is **opening a couple in a browser yourself**. Your eyes will figure out in 5 seconds what no automated tool can.
