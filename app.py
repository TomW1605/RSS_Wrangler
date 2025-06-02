import importlib
import inspect
import os
import shutil
import subprocess
import sys
import traceback

import yaml
from flask import Flask, render_template, jsonify, Response, request

# Setup folders
CONFIG_FOLDER_PATH = os.getenv('CONFIG_PATH', "/config")
FEED_PROCESSORS_FOLDER_PATH = os.path.join(CONFIG_FOLDER_PATH, "feed_processors")
FEED_CACHE_FOLDER_PATH = os.path.join(CONFIG_FOLDER_PATH, "feed_cache")

if not os.path.exists(CONFIG_FOLDER_PATH):
    os.makedirs(CONFIG_FOLDER_PATH)

if not os.path.exists(FEED_PROCESSORS_FOLDER_PATH):
    os.makedirs(FEED_PROCESSORS_FOLDER_PATH)

if not os.path.exists(FEED_CACHE_FOLDER_PATH):
    os.makedirs(FEED_CACHE_FOLDER_PATH)

# Processor folder setup
EXAMPLE_FEED_PROCESSORS_FILE_PATH = os.path.join(FEED_PROCESSORS_FOLDER_PATH, "example_feed_processor.py")
if not os.path.exists(EXAMPLE_FEED_PROCESSORS_FILE_PATH):
    shutil.copyfile("example_feed_processor.py", EXAMPLE_FEED_PROCESSORS_FILE_PATH)
open(os.path.join(FEED_PROCESSORS_FOLDER_PATH, "requirements.txt"), 'a').close()

# Install feed processor requirements
if os.path.exists(os.path.join(FEED_PROCESSORS_FOLDER_PATH, "requirements.txt")):
    print("Installing feed processor requirements...")
    requirements_file_path = os.path.join(FEED_PROCESSORS_FOLDER_PATH, "requirements.txt")
    pip_command = f"{sys.executable} -m pip install --root-user-action ignore -r {requirements_file_path}"
    subprocess.run(pip_command.split())

# Config setup
CONFIG_FILE_PATH = os.path.join(CONFIG_FOLDER_PATH, "config.yml")
if not os.path.exists(CONFIG_FILE_PATH):
    shutil.copyfile("config.example.yml", CONFIG_FILE_PATH)

def reload_config():
    """Reload the configuration from config.yml."""
    global config
    with open(CONFIG_FILE_PATH, mode='r') as f:
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

def get_feed_paths(config_feeds, base_url, current_path=""):
    paths = []

    for key, value in config_feeds.items():
        new_path = f"{current_path}/{key}" if current_path else key

        # If the value is a dictionary and has 'url' and 'processor', it's a feed configuration
        if isinstance(value, dict) and 'url' in value and 'processor' in value:
            # Ensure base_url starts and ends with '/'
            clean_base_url = base_url.strip('/')
            clean_base_url = f"/{clean_base_url}/" if clean_base_url else "/"

            # Construct the full web path
            feed_url = f"{clean_base_url}{new_path}.xml"
            paths.append(feed_url)

        # If it's a dictionary but not a feed config, recurse deeper
        elif isinstance(value, dict):
            paths.append({key: get_feed_paths(value, base_url, new_path)})

    return paths

@app.route(config["base_url"], methods=["GET"])
def index():
    reload_config()

    feeds = get_feed_paths(config["feeds"], config["base_url"])

    return render_template("index.html", feeds=feeds)

@app.route(config["base_url"] + "<path:feed_path>.xml", methods=["GET"])
def feed(feed_path):
    reload_config()

    if not dict_path_exists(config["feeds"], f"{feed_path}"):
        return jsonify({"error": "Feed not found"}), 404

    feed_data = dict_get_by_path(config["feeds"], f"{feed_path}")
    feed_name = feed_path.split('/')[-1]

    if "args" not in feed_data:
        feed_data["args"] = {}

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
        query_args = request.args.to_dict()
        for parameter_name, parameter in inspect.signature(feed_module.process_feed).parameters.items():
            if parameter_name in request.args:
                query_args[parameter_name] = request.args.get(parameter_name, default=query_args[parameter_name], type=parameter.annotation)
        feed_data["args"] |= query_args
    except Exception as e:
        return jsonify({"error": f"Error processing query parameters: `{traceback.format_exc(0).strip()}`"}), 500

    try:
        xml_data = feed_module.process_feed(feed_data["name"], feed_data["url"], f"{os.path.join(FEED_CACHE_FOLDER_PATH, feed_name)}.xml", **feed_data["args"])
    except Exception as e:
        return jsonify({"error": f"Custom feed processing failed: `{traceback.format_exc(0).strip()}`"}), 500

    response = Response(xml_data, mimetype='application/xml')
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config["port"])