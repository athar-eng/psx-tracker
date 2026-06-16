import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timezone, timedelta
import re

PKT = timezone(timedelta(hours=5))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def scrape_movers():
    """Scrape top 10 gainers and losers from PSX."""
    gainers = []
    losers = []

    try:
        # PSX market summary page
        url = "https://www.psx.com.pk/market-summary/"
        res = requests.get(url, headers=HEADERS, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # Try to find gainers/losers tables
        tables = soup.find_all("table")
        for table in tables:
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
            rows = table.find_all("tr")[1:]  # skip header row

            is_gainer = any("gain" in h or "top" in h for h in headers)
            is_loser = any("loss" in h or "declin" in h for h in headers)

            parsed = []
            for row in rows[:10]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cols) >= 3:
                    parsed.append({
                        "symbol": cols[0],
                        "price": cols[1],
                        "change": cols[2] if len(cols) > 2 else "",
                        "change_pct": cols[3] if len(cols) > 3 else "",
                    })

            if is_gainer and not gainers:
                gainers = parsed
            elif is_loser and not losers:
                losers = parsed

    except Exception as e:
        print(f"Movers scrape error: {e}")

    # Fallback: try the main homepage
    if not gainers and not losers:
        try:
            res = requests.get("https://www.psx.com.pk/", headers=HEADERS, timeout=20)
            soup = BeautifulSoup(res.text, "html.parser")

            for section in soup.find_all(["section", "div"]):
                text = section.get_text(strip=True).lower()
                if "top gain" in text or "top los" in text:
                    rows = section.find_all("tr")
                    parsed = []
                    for row in rows[1:11]:
                        cols = [td.get_text(strip=True) for td in row.find_all("td")]
                        if cols:
                            parsed.append({
                                "symbol": cols[0] if len(cols) > 0 else "",
                                "price": cols[1] if len(cols) > 1 else "",
                                "change": cols[2] if len(cols) > 2 else "",
                                "change_pct": cols[3] if len(cols) > 3 else "",
                            })
                    if "gain" in text and not gainers:
                        gainers = parsed
                    elif "los" in text and not losers:
                        losers = parsed
        except Exception as e:
            print(f"Homepage fallback error: {e}")

    return gainers, losers


def scrape_media_releases():
    """Scrape last 5 days of media releases from PSX."""
    releases = []

    try:
        url = "https://www.psx.com.pk/psx/media-center/media-releases"
        res = requests.get(url, headers=HEADERS, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        cutoff = datetime.now(PKT) - timedelta(days=5)

        # Find all links that look like release entries
        entries = soup.find_all(["article", "li", "div"], class_=re.compile(r"post|entry|item|release", re.I))

        if not entries:
            # Fallback: find all anchor tags with dates nearby
            entries = soup.find_all("a", href=re.compile(r"media-release|press-release|announcement", re.I))

        for entry in entries:
            title_el = entry.find(["h2", "h3", "h4", "a"])
            date_el = entry.find(["time", "span", "p"], class_=re.compile(r"date|time|publish", re.I))

            title = title_el.get_text(strip=True) if title_el else ""
            date_str = date_el.get_text(strip=True) if date_el else ""
            link = ""

            a_tag = entry.find("a", href=True)
            if a_tag:
                href = a_tag["href"]
                link = href if href.startswith("http") else f"https://www.psx.com.pk{href}"

            if title:
                releases.append({
                    "title": title,
                    "date": date_str,
                    "link": link,
                })

            if len(releases) >= 20:
                break

    except Exception as e:
        print(f"Media releases error: {e}")

    return releases[:20]


def main():
    now_pkt = datetime.now(PKT)
    gainers, losers = scrape_movers()
    media = scrape_media_releases()

    data = {
        "updated_at": now_pkt.strftime("%Y-%m-%d %I:%M %p PKT"),
        "date": now_pkt.strftime("%B %d, %Y"),
        "gainers": gainers,
        "losers": losers,
        "media_releases": media,
    }

    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Done. Gainers: {len(gainers)}, Losers: {len(losers)}, Media: {len(media)}")


if __name__ == "__main__":
    main()
