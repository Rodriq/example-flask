from flask import Flask, request, render_template_string
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import time
from requests.exceptions import RequestException

app = Flask(__name__)

# Set of visited URLs to avoid revisiting them
visited_urls = set()
# File to store the scraped content
output_file = 'scraped_content.txt'
# Rate limit: 1 request per second
RATE_LIMIT = 1

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def get_all_links(url, domain):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.attrs['href']
            full_url = urljoin(url, href)
            if is_valid_url(full_url) and domain in full_url:
                links.add(full_url)
        return links
    except RequestException as e:
        print(f"Failed to get links from {url}: {e}")
        return set()

def clean_content(soup):
    # Remove script and style elements
    for script_or_style in soup(['script', 'style']):
        script_or_style.decompose()
    # Get text
    text = soup.get_text(separator='\n', strip=True)
    return text

def scrape_website(start_url):
    domain = urlparse(start_url).netloc
    queue = [start_url]

    with open(output_file, 'w', encoding='utf-8') as f:
        while queue:
            url = queue.pop(0)
            if url in visited_urls:
                continue
            visited_urls.add(url)
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                page_content = clean_content(soup)
                f.write(f"### Page: {url} ###\n")
                f.write(page_content)
                f.write("\n" + "="*80 + "\n\n")
                print(f"Scraped {url}")
                links = get_all_links(url, domain)
                queue.extend(links - visited_urls)
                time.sleep(RATE_LIMIT)  # Respect rate limit
            except RequestException as e:
                print(f"Failed to scrape {url}: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_url = request.form['url']
        if is_valid_url(start_url):
            scrape_website(start_url)
            return f"Scraping completed. Content saved to {output_file}"
        else:
            return "Invalid URL. Please try again."
    return render_template_string('''
        <form method="post">
            Enter URL to scrape: <input type="text" name="url">
            <input type="submit" value="Scrape">
        </form>
    ''')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
