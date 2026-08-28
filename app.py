import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from flask import Flask, jsonify, render_template, request
import urllib.request

app = Flask(__name__)

FEED_URL = "https://docs.cloud.google.com/feeds/bigquery-release-notes.xml"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

# Cache structure to avoid spamming the upstream server
_cache = {
    "data": None,
    "last_fetched": 0,
    "cache_duration": 60,  # seconds
}


def strip_html_tags(text):
    """Simple regex fallback to strip HTML tags."""
    clean = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", clean).strip()


def parse_entry_content(content_html, entry_link, entry_title, entry_index):
    """
    Parses entry HTML content into discrete items (e.g., Feature, Security, Bug Fix).
    BigQuery feeds structure content with <h3> tags denoting categories.
    """
    if BeautifulSoup is not None:
        soup = BeautifulSoup(content_html, "html.parser")
        items = []

        # Ensure all relative links have full Google Docs URLs
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("/"):
                a["href"] = f"https://docs.cloud.google.com{a['href']}"
            a["target"] = "_blank"
            a["rel"] = "noopener noreferrer"

        h3_elements = soup.find_all("h3")

        if h3_elements:
            for idx, h3 in enumerate(h3_elements):
                category = h3.get_text(strip=True)
                item_elements = []
                curr = h3.next_sibling
                while curr and getattr(curr, "name", None) != "h3":
                    if getattr(curr, "name", None) or (isinstance(curr, str) and curr.strip()):
                        item_elements.append(curr)
                    curr = curr.next_sibling

                item_soup = BeautifulSoup("".join(str(el) for el in item_elements), "html.parser")
                plain_text = item_soup.get_text(separator=" ", strip=True)
                plain_text = re.sub(r"\s+", " ", plain_text)

                items.append({
                    "id": f"entry-{entry_index}-item-{idx}",
                    "category": category or "Update",
                    "html": str(item_soup),
                    "plain_text": plain_text,
                    "entry_title": entry_title,
                    "link": entry_link,
                })
        else:
            plain_text = soup.get_text(separator=" ", strip=True)
            plain_text = re.sub(r"\s+", " ", plain_text)
            items.append({
                "id": f"entry-{entry_index}-item-0",
                "category": "Update",
                "html": str(soup),
                "plain_text": plain_text,
                "entry_title": entry_title,
                "link": entry_link,
            })

        return items
    else:
        # Fallback when bs4 is not installed
        # Split on <h3> tags
        sections = re.split(r"<h3>(.*?)</h3>", content_html, flags=re.IGNORECASE)
        items = []
        if len(sections) > 1:
            # sections[0] is before first h3, then pairs: (category, body)
            idx = 0
            for i in range(1, len(sections), 2):
                cat = sections[i].strip()
                body = sections[i + 1] if i + 1 < len(sections) else ""
                plain_text = strip_html_tags(body)
                items.append({
                    "id": f"entry-{entry_index}-item-{idx}",
                    "category": cat or "Update",
                    "html": body,
                    "plain_text": plain_text,
                    "entry_title": entry_title,
                    "link": entry_link,
                })
                idx += 1
        else:
            plain_text = strip_html_tags(content_html)
            items.append({
                "id": f"entry-{entry_index}-item-0",
                "category": "Update",
                "html": content_html,
                "plain_text": plain_text,
                "entry_title": entry_title,
                "link": entry_link,
            })
        return items


def fetch_and_parse_feed(force_refresh=False):
    now = time.time()
    if not force_refresh and _cache["data"] and (now - _cache["last_fetched"] < _cache["cache_duration"]):
        return _cache["data"], None

    try:
        headers = {
            "User-Agent": "BigQueryReleaseNotesTracker/1.0 (+https://cloud.google.com/bigquery)"
        }
        if requests is not None:
            resp = requests.get(FEED_URL, headers=headers, timeout=12)
            resp.raise_for_status()
            xml_bytes = resp.content
        else:
            req = urllib.request.Request(FEED_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                xml_bytes = response.read()

        root = ET.fromstring(xml_bytes)

        feed_title = root.findtext("atom:title", default="BigQuery Release Notes", namespaces=ATOM_NS)
        feed_updated = root.findtext("atom:updated", default="", namespaces=ATOM_NS)
        
        entries = []
        raw_entries = root.findall("atom:entry", namespaces=ATOM_NS)

        for entry_idx, entry in enumerate(raw_entries):
            entry_id = entry.findtext("atom:id", default=f"entry-{entry_idx}", namespaces=ATOM_NS)
            title = entry.findtext("atom:title", default="Release Note", namespaces=ATOM_NS)
            updated = entry.findtext("atom:updated", default="", namespaces=ATOM_NS)
            
            link_elem = entry.find("atom:link[@rel='alternate']", namespaces=ATOM_NS)
            if link_elem is None:
                link_elem = entry.find("atom:link", namespaces=ATOM_NS)
            link = link_elem.attrib.get("href", "https://docs.cloud.google.com/bigquery/docs/release-notes") if link_elem is not None else "https://docs.cloud.google.com/bigquery/docs/release-notes"

            content_elem = entry.find("atom:content", namespaces=ATOM_NS)
            content_html = content_elem.text if content_elem is not None and content_elem.text else ""

            # Parse sub-items
            items = parse_entry_content(content_html, link, title, entry_idx)

            entries.append({
                "id": entry_id,
                "title": title,
                "updated": updated,
                "link": link,
                "raw_html": content_html,
                "items": items,
                "item_count": len(items),
            })

        parsed_data = {
            "title": feed_title,
            "updated": feed_updated,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "total_entries": len(entries),
            "total_items": sum(len(e["items"]) for e in entries),
            "entries": entries,
        }

        _cache["data"] = parsed_data
        _cache["last_fetched"] = now
        return parsed_data, None

    except requests.RequestException as e:
        # If upstream fails but we have cached data, return cached data with warning
        if _cache["data"]:
            return _cache["data"], f"Upstream fetch failed ({str(e)}). Serving cached data."
        return None, f"Failed to fetch feed: {str(e)}"
    except ET.ParseError as e:
        return None, f"Failed to parse XML feed: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/feed")
def get_feed():
    force = request.args.get("refresh", "false").lower() in ("true", "1", "yes")
    data, error = fetch_and_parse_feed(force_refresh=force)
    
    if data is None:
        return jsonify({"success": False, "error": error}), 502
    
    response_payload = {
        "success": True,
        "data": data,
    }
    if error:
        response_payload["warning"] = error

    return jsonify(response_payload)


@app.route("/api/tweet-preview", methods=["POST"])
def tweet_preview():
    """Helper endpoint to generate and format tweet text nicely within 280 characters."""
    req_data = request.get_json(silent=True) or {}
    text = req_data.get("text", "").strip()
    title = req_data.get("title", "").strip()
    category = req_data.get("category", "").strip()
    link = req_data.get("link", "https://docs.cloud.google.com/bigquery/docs/release-notes").strip()

    prefix = f"🚀 BigQuery {category} ({title}):\n\n" if category else f"🚀 BigQuery Update ({title}):\n\n"
    hashtags = "\n\n#BigQuery #GoogleCloud #DataEngineering"
    
    # Target max length around 280 chars (accounting for t.co link length ~23 chars)
    # Total = len(prefix) + snippet + len("...\n\n") + link + len(hashtags)
    reserved_len = len(prefix) + 25 + len(hashtags) + 5
    max_snippet_len = max(50, 280 - reserved_len)

    if len(text) > max_snippet_len:
        snippet = text[:max_snippet_len - 3].rstrip() + "..."
    else:
        snippet = text

    tweet_body = f"{prefix}{snippet}\n\n🔗 {link}{hashtags}"
    tweet_url = f"https://x.com/intent/tweet?text={quote(tweet_body)}"

    return jsonify({
        "tweet_body": tweet_body,
        "char_count": len(tweet_body),
        "tweet_url": tweet_url,
    })


if __name__ == "__main__":
    print("Starting BigQuery Release Notes Web App on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
