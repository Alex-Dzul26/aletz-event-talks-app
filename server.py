import http.server
import json
import mimetypes
import os
import re
import socketserver
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEED_URL = "https://docs.cloud.google.com/feeds/bigquery-release-notes.xml"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

_cache = {
    "data": None,
    "last_fetched": 0,
    "cache_duration": 60,
}


def strip_html_tags(text):
    clean = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", clean).strip()


def parse_entry_content(content_html, entry_link, entry_title, entry_index):
    sections = re.split(r"<h3>(.*?)</h3>", content_html, flags=re.IGNORECASE)
    items = []
    if len(sections) > 1:
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
            link = (
                link_elem.attrib.get("href", "https://docs.cloud.google.com/bigquery/docs/release-notes")
                if link_elem is not None
                else "https://docs.cloud.google.com/bigquery/docs/release-notes"
            )

            content_elem = entry.find("atom:content", namespaces=ATOM_NS)
            content_html = content_elem.text if content_elem is not None and content_elem.text else ""

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
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "total_entries": len(entries),
            "total_items": sum(len(e["items"]) for e in entries),
            "entries": entries,
        }

        _cache["data"] = parsed_data
        _cache["last_fetched"] = now
        return parsed_data, None

    except Exception as e:
        if _cache["data"]:
            return _cache["data"], f"Upstream error ({str(e)}). Serving cache."
        return None, f"Failed to fetch feed: {str(e)}"


class AppRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            index_path = os.path.join(BASE_DIR, "templates", "index.html")
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Replace Flask template syntax for static files
                content = content.replace("{{ url_for('static', filename='css/style.css') }}", "/static/css/style.css")
                content = content.replace("{{ url_for('static', filename='js/app.js') }}", "/static/js/app.js")

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return

        elif path.startswith("/static/"):
            rel_path = path[len("/static/") :].replace("/", os.sep)
            file_path = os.path.join(BASE_DIR, "static", rel_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                self.send_response(200)
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "File Not Found")
                return

        elif path == "/api/feed":
            query = urllib.parse.parse_qs(parsed.query)
            force = query.get("refresh", ["false"])[0].lower() in ("true", "1", "yes")
            data, error = fetch_and_parse_feed(force_refresh=force)

            if data is None:
                resp = json.dumps({"success": False, "error": error})
                self.send_response(502)
            else:
                payload = {"success": True, "data": data}
                if error:
                    payload["warning"] = error
                resp = json.dumps(payload)
                self.send_response(200)

            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp.encode("utf-8"))
            return

        self.send_error(404, "Not Found")


def run():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), AppRequestHandler) as httpd:
        print(f"\n=======================================================")
        print(f"🚀 BigQuery Release Notes Web App running (Zero dependencies!)")
        print(f"👉 Open in browser: http://127.0.0.1:{PORT}")
        print(f"=======================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    run()
