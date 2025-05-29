from bs4 import BeautifulSoup
import feedparser
import requests
import xml.etree.ElementTree as ET
import os

# TODO: store current feeds somewhere better

def get_image_from_url(url, img_filter):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        img_url = soup.find("img", src=lambda s: s and img_filter in s).get("src")
        return img_url
    except Exception as e:
        print(f"Error processing {url}")
        return None

def get_existing_entries(xml_file):
    try:
        if not os.path.exists(xml_file):
            return {}

        tree = ET.parse(xml_file)
        root = tree.getroot()
        existing_entries = {}

        for item in root.findall('.//item'):
            guid = item.find('guid')
            if guid is not None:
                existing_entries[guid.text] = item
        return existing_entries
    except Exception as e:
        print(f"Error reading existing file: {e}")
        return {}

def process_rss_feed(rss_url, output_file, img_filter):
    # Get existing entries
    existing_entries = get_existing_entries(output_file)

    # Parse the RSS feed
    feed = feedparser.parse(rss_url)

    # Create root element for new RSS feed
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')

    # Add feed metadata
    ET.SubElement(channel, 'title').text = feed.feed.title
    ET.SubElement(channel, 'link').text = feed.feed.link
    ET.SubElement(channel, 'description').text = feed.feed.description

    total_items = 0
    new_items = 0

    # Process each item
    for entry in feed.entries:
        if total_items >= 50:
            break

        # Get the GUID
        guid = entry.get('guid', entry.link)
        if guid in existing_entries:
            channel.append(existing_entries[guid])
            total_items += 1
            continue

        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = entry.title
        ET.SubElement(item, 'link').text = entry.link

        ET.SubElement(item, 'guid').text = guid

        # New entry - get image from the linked page
        image_url = get_image_from_url(entry.link, img_filter)
        if image_url:
            # Replace description with image HTML
            image_html = f'<link rel="preload" as="image" href="{image_url}"/><img src="{image_url}">'
            ET.SubElement(item, 'description').text = image_html
        else:
            # Keep original description if no image found
            ET.SubElement(item, 'description').text = entry.description if hasattr(entry, 'description') else ''

        if 'published' in entry:
            ET.SubElement(item, 'pubDate').text = entry.published

        total_items += 1
        new_items += 1

    # Create XML tree and save to file
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="\t", level=0)
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    return ET.tostring(tree.getroot(), encoding='unicode')