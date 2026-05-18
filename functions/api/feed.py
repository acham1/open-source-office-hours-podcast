from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring

from config import load_config


def build_rss_xml(reports: list[dict]) -> str:
    config = load_config()
    site_url = config["site_url"]

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = config["name"]
    SubElement(channel, "link").text = site_url
    SubElement(channel, "description").text = config["description"]
    SubElement(channel, "language").text = "en-us"

    for report in reports:
        item = SubElement(channel, "item")
        title = report.get("title", report.get("project_name", "Untitled"))
        SubElement(item, "title").text = title

        report_id = report.get("id", "")
        link = f"{site_url}/report.html?id={report_id}"
        SubElement(item, "link").text = link
        SubElement(item, "guid").text = link

        tagline = report.get("tagline", "")
        why = report.get("why_it_matters", "")
        SubElement(item, "description").text = f"{tagline}\n\n{why}" if tagline else why

        created = report.get("created_at")
        if created:
            if isinstance(created, str):
                dt = datetime.fromisoformat(created)
            else:
                dt = created
            dt = dt.astimezone(timezone.utc)
            SubElement(item, "pubDate").text = dt.strftime(
                "%a, %d %b %Y %H:%M:%S +0000"
            )

    xml_str = tostring(rss, encoding="unicode", xml_declaration=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
