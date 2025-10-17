#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

import requests


CROSSREF_API = "https://api.crossref.org/works"
UNPAYWALL_API = "https://api.unpaywall.org/v2"
USER_AGENT = "CitationFetcher/1.0 (+https://example.org/contact)"
REQ_TIMEOUT = 20
RETRY_BACKOFF = [0.5, 1.0, 2.0]


@dataclass
class ResolvedWork:
    citation: str
    doi: Optional[str]
    title: Optional[str]
    source: str  # "parsed" or "crossref"


def read_citations(args_citations: Iterable[str], input_file: Optional[str]) -> list[str]:
    items: list[str] = []
    if input_file:
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s:
                    items.append(s)
    for c in args_citations:
        c = c.strip()
        if c:
            items.append(c)
    # de-duplicate while preserving order
    seen = set()
    unique = []
    for c in items:
        if c not in seen:
            unique.append(c)
            seen.add(c)
    return unique


def is_doi(s: str) -> bool:
    # Loose DOI pattern (case-insensitive), handles prefixes like doi: or https://doi.org/
    s = s.strip()
    s = re.sub(r"(?i)\bdoi:\s*", "", s)
    s = re.sub(r"(?i)^https?://(dx\.)?doi\.org/", "", s)
    return bool(re.match(r"^10\.\d{4,9}/\S+$", s))


def extract_doi_from_text(citation: str) -> Optional[str]:
    # Try to pull a DOI directly from a citation string
    m = re.search(r"(?i)\b10\.\d{4,9}/\S+\b", citation)
    if m:
        doi = m.group(0)
        # Trim trailing punctuation
        doi = doi.rstrip(").,;]")
        return doi
    # doi.org link
    m2 = re.search(r"(?i)https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/\S+)", citation)
    if m2:
        doi = m2.group(1).rstrip(").,;]")
        return doi
    return None


def http_get_json(url: str, params: dict) -> Optional[dict]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    for delay in [0.0] + RETRY_BACKOFF:
        if delay:
            time.sleep(delay)
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=REQ_TIMEOUT)
            if 200 <= resp.status_code < 300:
                return resp.json()
            # 429 or 5xx → retry
            if resp.status_code in (429, 500, 502, 503, 504):
                continue
            # Other errors → do not retry
            return None
        except requests.RequestException:
            continue
    return None


def crossref_resolve(citation: str) -> Optional[ResolvedWork]:
    """
    Use Crossref works search to resolve a free-form citation to a DOI.
    """
    params = {
        "query.bibliographic": citation,
        "rows": 1,
        "select": "DOI,title,author,issued,type",
        "sort": "score",
        "order": "desc",
    }
    data = http_get_json(CROSSREF_API, params)
    if not data or "message" not in data or "items" not in data["message"]:
        return None
    items = data["message"]["items"]
    if not items:
        return None
    top = items[0]
    doi = top.get("DOI")
    title = None
    t = top.get("title")
    if isinstance(t, list) and t:
        title = t[0]
    elif isinstance(t, str):
        title = t
    if not doi:
        return None
    return ResolvedWork(citation=citation, doi=doi, title=title, source="crossref")


def resolve_citation(citation: str) -> Optional[ResolvedWork]:
    # Fast path: DOI present
    doi = extract_doi_from_text(citation)
    if doi:
        return ResolvedWork(citation=citation, doi=doi, title=None, source="parsed")
    # Fallback: Crossref search
    return crossref_resolve(citation)


def unpaywall_pdf_url(doi: str, email: str) -> Optional[Tuple[str, str]]:
    """
    Returns (pdf_url, host) if an open-access PDF is available.
    """
    url = f"{UNPAYWALL_API}/{requests.utils.quote(doi)}"
    params = {"email": email}
    data = http_get_json(url, params)
    if not data:
        return None
    # Prefer best_oa_location, fall back to oa_locations
    locs = []
    if data.get("best_oa_location"):
        locs.append(data["best_oa_location"])
    if data.get("oa_locations"):
        locs.extend(data["oa_locations"])
    for loc in locs:
        pdf_url = loc.get("url_for_pdf") or ""
        if pdf_url:
            return pdf_url, loc.get("host_type", "unknown")
    return None


def safe_filename(s: str, max_len: int = 200) -> str:
    s = re.sub(r"[\\/:*?\"<>|]+", "_", s)
    s = s.strip()
    if len(s) > max_len:
        s = s[:max_len]
    return s or "file"


def download_pdf(url: str, out_path: str) -> bool:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        "Referer": "https://doi.org/",
    }
    for delay in [0.0] + RETRY_BACKOFF:
        if delay:
            time.sleep(delay)
        try:
            with requests.get(url, headers=headers, timeout=REQ_TIMEOUT, stream=True, allow_redirects=True) as r:
                if r.status_code == 403 or r.status_code == 401:
                    return False
                if 200 <= r.status_code < 300:
                    # Heuristic content-type check
                    ctype = r.headers.get("Content-Type", "").lower()
                    if "pdf" not in ctype and not url.lower().endswith(".pdf"):
                        # Might still be PDF; proceed cautiously.
                        pass
                    with open(out_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    # Basic validation: file not empty
                    if os.path.getsize(out_path) < 1000:
                        return False
                    return True
                if r.status_code in (429, 500, 502, 503, 504):
                    continue
                return False
        except requests.RequestException:
            continue
    return False


def process_one(citation: str, out_dir: str, unpaywall_email: str) -> dict:
    result = {
        "citation": citation,
        "doi": None,
        "title": None,
        "status": "failed",
        "pdf_path": None,
        "note": "",
    }
    resolved = resolve_citation(citation)
    if not resolved or not resolved.doi:
        result["note"] = "Could not resolve DOI"
        return result

    result["doi"] = resolved.doi
    result["title"] = resolved.title

    oa = unpaywall_pdf_url(resolved.doi, unpaywall_email)
    if not oa:
        result["note"] = "No open-access PDF found (Unpaywall)"
        return result

    pdf_url, host_type = oa
    base_name = safe_filename(resolved.title or resolved.doi)
    out_path = os.path.join(out_dir, f"{base_name}.pdf")
    ok = download_pdf(pdf_url, out_path)
    if not ok:
        result["note"] = "Failed to download PDF (access denied or non-PDF)"
        return result

    result["status"] = "ok"
    result["pdf_path"] = out_path
    result["note"] = f"Downloaded via Unpaywall ({host_type})"
    return result


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Resolve citations to DOIs and download open-access PDFs when available.",
        epilog="Tip: Provide --unpaywall-email to comply with Unpaywall's requirements."
    )
    p.add_argument("citations", nargs="*", help="Citation strings (can include DOIs or titles).")
    p.add_argument("-f", "--input-file", help="Path to a text file with one citation per line.")
    p.add_argument("-o", "--out-dir", default="pdfs", help="Directory to save PDFs (default: ./pdfs)")
    p.add_argument("-e", "--unpaywall-email", default="bt19ex@brocku.ca", help="Contact email for Unpaywall API.")
    p.add_argument("-j", "--jobs", type=int, default=min(8, (os.cpu_count() or 2)), help="Parallel downloads.")
    p.add_argument("--jsonl", help="Optional path to write JSONL results.")
    p.add_argument("--no-playwright-backup", action="store_false",
                   help="If Unpaywall fails, disable Brock Omni library search via Playwright.", dest="playwright_backup")

    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    citations = read_citations(args.citations, args.input_file)
    if not citations:
        print("No citations provided. Use positional args or --input-file.", file=sys.stderr)
        return 2

    os.makedirs(args.out_dir, exist_ok=True)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        futures = [ex.submit(process_one, c, args.out_dir, args.unpaywall_email) for c in citations]
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()

            if res["status"] != "ok" and args.playwright_backup:
                try:
                    fallback = playwright_fallback(
                        citation=res["citation"],
                        suggested_title=res.get("title"),
                        out_dir=args.out_dir
                    )
                    if fallback and fallback.get("pdf_path"):
                        res["status"] = "ok"
                        res["pdf_path"] = fallback["pdf_path"]
                        note = res.get("note", "")
                        res["note"] = (note + " | " if note else "") + fallback.get("note", "Downloaded via Playwright (Brock Omni)")
                    else:
                        note = res.get("note", "")
                        res["note"] = (note + " | " if note else "") + (fallback.get("note") if fallback else "Playwright fallback failed")
                except Exception:
                    note = res.get("note", "")
                    res["note"] = (note + " | " if note else "") + "Playwright fallback error"

            results.append(res)
            status = res["status"]
            doi = res.get("doi") or "-"
            title = res.get("title") or "-"
            note = res.get("note") or ""
            print(f"[{status}] DOI={doi} Title={title} [{note}]")

    if args.jsonl:
        with open(args.jsonl, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Summary
    ok = sum(1 for r in results if r["status"] == "ok")
    total = len(results)
    print(f"Done: {ok}/{total} PDF(s) downloaded.")
    return 0 if ok > 0 else 1

def playwright_fallback(
    citation: str,
    suggested_title: Optional[str],
    out_dir: str,
) -> Optional[dict]:
    """
    Headless Playwright backup that:
      1) Opens Brock Library homepage
      2) Fills the Omni search box with the query
      3) Submits the search form
      4) Opens the first result
      5) Finds a PDF link/button and downloads into out_dir

    Returns dict with keys: pdf_path, note
    """
    try:
        import asyncio
        from pathlib import Path
        from playwright.async_api import async_playwright, TimeoutError as PwTimeout
    except Exception:
        return {"note": "Playwright not available (not installed?)"}

    async def run() -> Optional[dict]:
        q = (suggested_title or citation).strip()
        safe_base = safe_filename(suggested_title or citation)
        target_path = os.path.join(out_dir, f"{safe_base}.pdf")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(accept_downloads=True,
                                                user_agent=USER_AGENT.replace("CitationFetcher", "Mozilla"))
            await context.add_init_script("""
              // Redirect same tab instead of opening a popup
              window.open = function(url, target, features) {
                if (url) location.href = url;
                return null;
              };
            """)

            page = await context.new_page()
            try:
                # 1) Open Brock Library
                await page.goto("https://brocku.ca/library/", timeout=60000, wait_until="load")
                print("Opened library page")

                # 2) Fill Omni search input by id
                sel = page.locator('input[id^="primoQueryTemp"]')
                await sel.fill(q)
                await sel.press("Enter")
                # await page.fill('input[id^="primoQueryTemp"]', q)

                # 3) Submit the form by name, try pressing Enter on the field and clicking the form's submit button
                # Try pressing Enter first
                # await page.press("#primoQueryTemp7330", "Enter")
                # If not navigated, try clicking the form's button
                # try:
                #     # generic submit inside the named form
                #     await page.click('form[name="searchForm7330"] button[type="submit"], form[name="searchForm7330"] button, form[name="searchForm7330"] input[type="submit"]', timeout=5000)
                # except PwTimeout:
                #     pass

                # Wait for results page to load (Primo often uses iframes/apps; we try some common markers)
                # Heuristic waits:
                await page.wait_for_load_state("load", timeout=30000)
                # Try to select first result link; use broad selectors
                result_selectors = [
                    'a[title][href*="/discovery/"]',     # Primo VE result links
                    'a[href*="/permalink/"]',
                    'a[href*="/fulldisplay"]',
                    'a[href]:has-text("View online")',
                    'a[href]:has-text("Full text available")',
                    'a[href]:has-text("Available online")',
                ]

                opened = False
                for sel in result_selectors:
                    locs = page.locator(sel)
                    if await locs.count() > 0:
                        await locs.first.click()
                        opened = True
                        break

                # If nothing clicked, try focusing results and pressing Enter
                if not opened:
                    try:
                        await page.keyboard.press("Enter")
                    except Exception:
                        pass

                # Give time for full display / record view
                await page.wait_for_timeout(3000)
                await page.wait_for_load_state("load", timeout=30000)

                results = await page.locator('div[class^="list-item-wrapper"]').element_handles()

                found_paper = None
                for result in results:
                    title = await result.query_selector('h3[class^="item-title"]')
                    title = await title.query_selector('span')
                    mark = await title.query_selector('mark')
                    title = await title.inner_text()
                    mark = await mark.text_content()
                    if mark and mark == suggested_title:
                        found_paper = result
                        break
                    if title and title == suggested_title:
                        found_paper = result
                        break

                if not found_paper:
                    await context.close()
                    await browser.close()
                    return {"note": "Playwright (Brock Omni): no PDF link/button found"}

                await found_paper.click()
                await page.wait_for_timeout(1000)

                await page.locator('button:has-text("View online")').first.click()

                await page.wait_for_timeout(1000)

                services_locator = page.locator('prm-full-view-service-container')
                services_locator = services_locator.filter(has_text="View Online")
                services_locator = services_locator.filter(has=page.get_by_role("link"))

                await services_locator.first.click()
                # attr = await href.get_attribute("href")
                # print(await href.text_content())
                # print(attr)
                # await page.goto(href, timeout=60000, wait_until="load")

                while True:
                    pass

                # await context.close()
                # await browser.close()

                # if pdf_saved:
                #     return {"pdf_path": target_path, "note": "Downloaded via Playwright (Brock Omni)"}

            except Exception:
                try:
                    await context.close()
                except Exception:
                    pass
                try:
                    await browser.close()
                except Exception:
                    pass
                return {"note": "Playwright (Brock Omni): unexpected error during fallback"}

    # Run the async flow
    return asyncio.run(run())

if __name__ == "__main__":
    raise SystemExit(main())