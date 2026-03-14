#!/usr/bin/env python3
"""
Apartment Agent — main entry point.

Flow:
  1. Scrape all 4 sites
  2. Filter to only NEW listings (not seen before)
  3. Ask Claude for a short AI summary of each
  4. Build a beautiful HTML email digest
  5. Send via SendGrid
  6. Save newly seen IDs (committed back to repo by GitHub Actions)
"""

import os
import sys
import logging

from agent.scraper import scrape_all
from agent.store import load_seen, save_seen, filter_new
from agent.email_builder import summarize_listing, build_email
from agent.mailer import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main():
    city = os.environ.get("CITY", "Berlin")
    dry_run = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

    # 1. Scrape
    all_listings = scrape_all()
    if not all_listings:
        log.warning("No listings found. Exiting without sending email.")
        sys.exit(0)

    # 2. Filter new
    seen = load_seen()
    new_listings = filter_new(all_listings, seen)
    log.info(f"New listings: {len(new_listings)} / {len(all_listings)} total")

    if not new_listings:
        log.info("No new listings today. No email sent.")
        sys.exit(0)

    # 3. AI summaries (cap at 20 to keep API costs low)
    listings_to_send = new_listings[:20]
    summaries = {}
    for i, listing in enumerate(listings_to_send, 1):
        log.info(f"Summarising {i}/{len(listings_to_send)}: {listing.title[:50]}")
        summaries[listing.id] = summarize_listing(listing)

    # 4. Build email
    subject, html = build_email(listings_to_send, city, summaries)

    # 5. Send (or dry-run)
    if dry_run:
        log.info("DRY RUN — writing email to email_preview.html instead of sending")
        with open("email_preview.html", "w") as f:
            f.write(html)
        log.info("Preview saved to email_preview.html")
    else:
        ok = send_email(subject, html)
        if not ok:
            log.error("Email delivery failed.")
            sys.exit(1)

    # 6. Mark as seen
    seen.update(l.id for l in listings_to_send)
    save_seen(seen)
    log.info("Done.")


if __name__ == "__main__":
    main()
