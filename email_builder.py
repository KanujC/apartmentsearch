"""
Uses Claude to write a short, human-friendly summary for each listing,
then renders a clean HTML email digest.
"""

import os
import logging
import anthropic

log = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ── AI SUMMARY ────────────────────────────────────────────────────────────────

def summarize_listing(listing) -> str:
    """Ask Claude for a 2-sentence punchy summary of a listing."""
    prompt = (
        f"You are a helpful apartment-hunting assistant. "
        f"Write exactly 2 short sentences summarising this German apartment listing "
        f"for someone deciding whether to click. Be specific and honest. "
        f"Mention standout positives and any potential concerns.\n\n"
        f"Title: {listing.title}\n"
        f"Price: {listing.price}\n"
        f"Size: {listing.size}\n"
        f"Rooms: {listing.rooms}\n"
        f"Address: {listing.address}\n"
        f"Description snippet: {listing.description[:300] if listing.description else 'n/a'}\n"
        f"Source: {listing.source}\n"
    )
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        log.warning(f"Claude summary failed for {listing.id}: {e}")
        return listing.description[:160] if listing.description else ""


# ── HTML EMAIL ────────────────────────────────────────────────────────────────

SOURCE_COLORS = {
    "ImmoScout24":      "#003d7a",
    "Immowelt":         "#e5001a",
    "eBay Kleinanzeigen": "#7b2d8b",
    "WG-Gesucht":       "#2d7d2d",
}

SOURCE_ICONS = {
    "ImmoScout24":      "&#127968;",
    "Immowelt":         "&#127969;",
    "eBay Kleinanzeigen": "&#128178;",
    "WG-Gesucht":       "&#128101;",
}


def _badge(source: str) -> str:
    color = SOURCE_COLORS.get(source, "#555")
    icon  = SOURCE_ICONS.get(source, "&#127760;")
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:12px;font-size:11px;font-weight:600;white-space:nowrap;">'
        f'{icon}&nbsp;{source}</span>'
    )


def _card(listing, summary: str) -> str:
    img_block = ""
    if listing.image_url:
        img_block = (
            f'<img src="{listing.image_url}" alt="apartment photo" '
            f'style="width:100%;height:160px;object-fit:cover;border-radius:8px 8px 0 0;display:block;">'
        )

    return f"""
<div style="background:#ffffff;border-radius:10px;overflow:hidden;
            margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.10);">
  {img_block}
  <div style="padding:16px 20px;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:6px;margin-bottom:8px;">
      <a href="{listing.url}" style="color:#1a1a1a;font-size:16px;font-weight:600;text-decoration:none;line-height:1.3;flex:1;">
        {listing.title}
      </a>
      {_badge(listing.source)}
    </div>

    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:10px;">
      <span style="background:#f0f4ff;color:#1e40af;padding:3px 10px;border-radius:20px;font-size:13px;font-weight:600;">
        &#128176; {listing.price}
      </span>
      <span style="background:#f0faf0;color:#166534;padding:3px 10px;border-radius:20px;font-size:13px;">
        &#9634; {listing.size}
      </span>
      <span style="background:#fff7ed;color:#9a3412;padding:3px 10px;border-radius:20px;font-size:13px;">
        &#127968; {listing.rooms} Zimmer
      </span>
    </div>

    <p style="color:#555;font-size:13px;margin:0 0 8px;">
      &#128205; {listing.address}
    </p>

    {f'<p style="color:#374151;font-size:14px;line-height:1.55;margin:0 0 12px;font-style:italic;">"{summary}"</p>' if summary else ''}

    <a href="{listing.url}"
       style="display:inline-block;background:#1d4ed8;color:#fff;text-decoration:none;
              padding:8px 18px;border-radius:6px;font-size:13px;font-weight:600;">
      Zur Anzeige &rarr;
    </a>
  </div>
</div>
"""


def build_email(listings, city: str, summaries: dict[str, str]) -> tuple[str, str]:
    """Returns (subject, html_body)."""
    count = len(listings)
    subject = f"&#127968; {count} neue Wohnungen in {city} gefunden"

    by_source: dict[str, list] = {}
    for l in listings:
        by_source.setdefault(l.source, []).append(l)

    stats_html = "".join(
        f'<span style="margin-right:16px;font-size:13px;color:#6b7280;">'
        f'<strong style="color:#111;">{len(v)}</strong> {k}</span>'
        for k, v in by_source.items()
    )

    cards_html = "".join(_card(l, summaries.get(l.id, "")) for l in listings)

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

<div style="max-width:620px;margin:0 auto;padding:24px 16px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e3a8a,#1d4ed8);border-radius:12px;
              padding:28px 28px 22px;margin-bottom:24px;color:#fff;">
    <h1 style="margin:0 0 6px;font-size:24px;font-weight:700;">
      &#127968; {count} neue Wohnungen in {city}
    </h1>
    <p style="margin:0;opacity:.85;font-size:14px;">
      Täglich aktualisiert &middot; Nur neue Anzeigen
    </p>
  </div>

  <!-- Stats bar -->
  <div style="background:#fff;border-radius:8px;padding:12px 16px;
              margin-bottom:20px;border:1px solid #e5e7eb;">
    {stats_html}
  </div>

  <!-- Listings -->
  {cards_html}

  <!-- Footer -->
  <div style="text-align:center;color:#9ca3af;font-size:12px;padding:16px 0 8px;">
    Automatisch generiert &middot; Gefilterte Anzeigen aus ImmoScout24, Immowelt,
    eBay Kleinanzeigen &amp; WG-Gesucht<br>
    Powered by Claude AI
  </div>

</div>
</body>
</html>"""

    return subject, html
