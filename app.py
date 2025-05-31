import importlib
import os
import shutil
import traceback

import yaml
from flask import Flask, render_template, jsonify, Response

# Config setup
if not os.path.exists('config.yml'):
    shutil.copyfile("config.example.yml", "config.yml")

def reload_config():
    """Reload the configuration from config.yml."""
    global config
    with open("config.yml", mode='r') as f:
        config = yaml.safe_load(f)

reload_config()

# Ensure base_url has leading and trailing slashes
if not config["base_url"].startswith('/'):
    config["base_url"] = '/' + config["base_url"]
if not config["base_url"].endswith('/'):
    config["base_url"] = config["base_url"] + '/'

app = Flask(__name__, static_url_path=config["base_url"] + 'static')

def dict_path_exists(data, path, sep='/'):
    """Check if a nested dict path exists (e.g. 'feeds/type_1/feed_1')."""
    keys = path.strip(sep).split(sep)
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return False
        data = data[key]
    return True

def dict_get_by_path(data, path, sep='/'):
    """Access nested dict value by path string (e.g. 'feeds/type_1/feed_1')."""
    keys = path.strip(sep).split(sep)
    for key in keys:
        data = data[key]
    return data

@app.route(config["base_url"], methods=["GET"])
def index():
    return render_template("index.html")

@app.route(config["base_url"] + "<path:feed_path>.xml", methods=["GET"])
def feed(feed_path):
    reload_config()

    if not dict_path_exists(config["feeds"], f"{feed_path}"):
        return jsonify({"error": "Feed not found"}), 404

    feed_data = dict_get_by_path(config["feeds"], f"{feed_path}")
    feed_name = feed_path.split('/')[-1]

    try:
        if feed_data["processor"].endswith('.py'):
            feed_data["processor"] = feed_data["processor"][:-3]
        feed_module = importlib.import_module(f'feed_processors.{feed_data["processor"]}')
        importlib.reload(feed_module)
    except ImportError as e:
        return jsonify({"error": f"Feed processor `{feed_data['processor']}` not found: {traceback.format_exc(0).strip()}"}), 500

    if not hasattr(feed_module, 'process_feed'):
        return jsonify({"error": f"Feed processor `{feed_data['processor']}` does not have a `process_feed` function"}), 500

    try:
        xml_data = feed_module.process_feed(feed_data["name"], feed_data["url"], f"{feed_name}.xml", **feed_data.get("args", {}))
    except Exception as e:
        return jsonify({"error": f"Custom feed processing failed: `{traceback.format_exc(0).strip()}`"}), 500

    response = Response(xml_data, mimetype='application/xml')
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config["port"], debug=True)