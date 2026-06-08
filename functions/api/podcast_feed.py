import os
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

from config import load_config

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
register_namespace("itunes", ITUNES_NS)


def build_podcast_rss_xml(reports: list[dict]) -> str:
    config = load_config()
    site_url = config["site_url"]

    rss = Element("rss", version="2.0")

    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = config["name"]
    SubElement(channel, "link").text = site_url
    SubElement(channel, "language").text = "en-us"
    SubElement(channel, "description").text = config["podcast_description"]

    SubElement(channel, f"{{{ITUNES_NS}}}author").text = config["name"]
    SubElement(channel, f"{{{ITUNES_NS}}}summary").text = config["podcast_description"]
    SubElement(channel, f"{{{ITUNES_NS}}}explicit").text = "no"

    image = SubElement(channel, f"{{{ITUNES_NS}}}image")
    image.set("href", config["podcast_cover_url"])

    owner = SubElement(channel, f"{{{ITUNES_NS}}}owner")
    SubElement(owner, f"{{{ITUNES_NS}}}name").text = config["name"]
    SubElement(owner, f"{{{ITUNES_NS}}}email").text = os.environ.get(
        "ADMIN_EMAIL", config["from_email"]
    )

    category = SubElement(channel, f"{{{ITUNES_NS}}}category")
    category.set("text", config["podcast_category"])

    for report in reports:
        audio_url = report.get("audio_url")
        if not audio_url:
            continue

        item = SubElement(channel, "item")
        title = report.get("title", report.get("project_name", "Untitled"))
        SubElement(item, "title").text = title
        SubElement(item, f"{{{ITUNES_NS}}}author").text = config["name"]
        SubElement(item, f"{{{ITUNES_NS}}}explicit").text = "no"

        report_id = report.get("id", "")
        link = f"{site_url}/report.html?id={report_id}"
        SubElement(item, "link").text = link
        SubElement(item, "guid").text = audio_url

        tagline = report.get("tagline", "")
        why = report.get("why_it_matters", "")
        SubElement(item, "description").text = f"{tagline}\n\n{why}" if tagline else why

        enclosure = SubElement(item, "enclosure")
        enclosure.set("url", audio_url)
        enclosure.set("type", "audio/mpeg")
        enclosure.set("length", str(report.get("audio_size_bytes", 0)))

        duration_secs = report.get("audio_duration_secs", 0)
        minutes, secs = divmod(duration_secs, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            SubElement(item, f"{{{ITUNES_NS}}}duration").text = (
                f"{hours}:{minutes:02d}:{secs:02d}"
            )
        else:
            SubElement(item, f"{{{ITUNES_NS}}}duration").text = f"{minutes}:{secs:02d}"

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
