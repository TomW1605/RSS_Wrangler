"""
to use external libraries, add them to a `requirements.txt` file in the feed processor directory and restart the server.
"""

def process_feed(name, url, output_file, **kwargs):
    """
    generate an RSS feed XML string from the URL
    :param name: name of the feed, as specified in the config file
    :param url: URL of the page to generate the feed from
    :param output_file: file to store past feeds in to avoid regenerating data
    :param kwargs: any arguments from the `args` section of the config file
    :return: an RSS feed XML string
    """
    return f"<feed><title>Feed 1</title><link>{url}</link><description>Custom feed for Feed 1</description></feed>"