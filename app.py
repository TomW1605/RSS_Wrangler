import importlib
import os
import shutil

import yaml
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response

from generic_rss import process_rss_feed

# Config setup
if not os.path.exists('config.yml'):
    shutil.copyfile("config.example.yml", "config.yml")

with open("config.yml", mode='r') as f:
    config = yaml.safe_load(f)

# Ensure base_url has leading and trailing slashes
if not config["base_url"].startswith('/'):
    config["base_url"] = '/' + config["base_url"]
if not config["base_url"].endswith('/'):
    config["base_url"] = config["base_url"] + '/'

app = Flask(__name__, static_url_path=config["base_url"] + 'static')

@app.route(config["base_url"], methods=["GET"])
def index():
    return render_template("index.html")

@app.route(config["base_url"] + "<name>.xml", methods=["GET"])
def feed(name):
    if name in config["feeds"]:
        feed_data = config["feeds"][name]
        xml_data = process_rss_feed(feed_data["url"], f"{name}.xml", feed_data["img_filter"])
    elif name in config["custom_feeds"]:
        custom_feed = importlib.import_module(f'custom_feeds.{name}')
        importlib.reload(custom_feed)
        if not hasattr(custom_feed, 'process_feed'):
            return jsonify({"error": f"Custom feed `{name}` does not have a `process_feed` function"}), 500
        feed_data = config["custom_feeds"][name]
        try:
            xml_data = custom_feed.process_feed(feed_data["url"], f"{name}.xml")
        except Exception as e:
            return jsonify({"error": f"Custom feed processing failed: `{str(e)}`"}), 500
    else:
        return jsonify({"error": "Feed not found"}), 404

    response = Response(xml_data, mimetype='application/xml')
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config["port"], debug=True)