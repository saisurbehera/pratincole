import scrapy
from scrapy.crawler import CrawlerProcess
import re
import os
from urllib.parse import urlparse, parse_qs, unquote

class FactorioSpider(scrapy.Spider):
    name = "factorio_spider"
    
    # Configure for your target website
    allowed_domains = ["wiki.factorio.com"]
    start_urls = ["https://wiki.factorio.com/Main_Page"]
    
    # List of language codes to filter
    languages_to_filter = [
        'cs', 'da', 'de', 'es', 'fr', 'hu', 'it', 'ja', 'ko', 'ms',
        'nl', 'pl', 'pt-br', 'pt-pt', 'ru', 'sv', 'tr', 'uk', 'vi',
        'zh', 'zh-tw'
    ]
    
    # Directory to save HTML files
    output_dir = "scraped_html_files"
    
    def __init__(self, *args, **kwargs):
        super(FactorioSpider, self).__init__(*args, **kwargs)
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def parse(self, response):
        """Main parsing method"""
        # Extract page data
        title = response.css('h1#firstHeading::text').get()
        
        # Only process if this is not a language-specific page
        if not self.should_filter_link(response.url):
            # Save the page content to a file
            self.save_page(response)
            
            # Output current page
            yield {
                'url': response.url,
                'title': title,
            }
            
            # Process links
            for link in response.css('a::attr(href)').getall():
                # Skip javascript: links and other invalid URLs
                if link.startswith('javascript:') or link.startswith('#') or not link:
                    continue
                    
                # Only follow links that don't contain language codes
                if not self.should_filter_link(link):
                    try:
                        yield response.follow(link, self.parse)
                    except ValueError as e:
                        self.logger.error(f"Error following link {link}: {e}")
    
    def save_page(self, response):
        """Save the page content to a file"""
        # Parse the URL to get the path
        parsed_url = urlparse(response.url)
        path = parsed_url.path
        
        # Clean up the path to create a valid filename
        if path == "/" or not path:
            filename = "Main_Page"
        else:
            # Remove leading slash and replace slashes with underscores
            filename = path.lstrip('/').replace('/', '_')
        
        # Add query parameters to filename if they exist
        if parsed_url.query:
            query_part = parsed_url.query.replace('&', '_').replace('=', '_')
            filename = f"{filename}_{query_part}"
        
        # Replace problematic characters
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        
        # Prepend underscore to avoid issues with filenames starting with special characters
        filename = f"_{filename}.html"
        
        # Save the complete HTML content
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(response.body)
    
    def should_filter_link(self, link):
        """
        Returns True if the link should be filtered out (contains language code),
        False otherwise.
        """
        # Decode URL entities like &amp; to &
        decoded_link = unquote(link.replace('&amp;', '&'))
        
        # Parse the URL
        parsed = urlparse(decoded_link)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        # Handle different URL patterns
        
        # Pattern 1: Direct language suffix: /PageName/lang
        for lang in self.languages_to_filter:
            if re.search(r'/[^/]+/' + re.escape(lang) + '$', path):
                return True
        
        # Pattern 2: Special pages with language codes in path/query
        if 'title' in query:
            title_value = query['title'][0]
            # Check for language code at the end of title parameter
            for lang in self.languages_to_filter:
                if title_value.endswith('/' + lang):
                    return True
                # Handle Special:WhatLinksHere/PageName/lang
                if 'WhatLinksHere' in title_value and '/' + lang in title_value:
                    return True
                # Handle Special:RecentChangesLinked/PageName/lang
                if 'RecentChangesLinked' in title_value and '/' + lang in title_value:
                    return True
        
        # Pattern 3: Check for other special pages with language codes
        for lang in self.languages_to_filter:
            # Look for language code patterns in various URL formats
            lang_pattern = r'/' + re.escape(lang) + r'(&|$|/)'
            if re.search(lang_pattern, decoded_link):
                return True
            
            # Check for parenthesized content with language code
            if re.search(r'\([^)]+\)/' + re.escape(lang), decoded_link):
                return True
        
        # Not filtered
        return False

# To run the spider
if __name__ == "__main__":
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'FEED_FORMAT': 'csv',
        'FEED_URI': 'factorio_forum_pages.csv',
        'ROBOTSTXT_OBEY': False,  # WARNING: Disabling respect for robots.txt
        'DOWNLOAD_DELAY': 0.1,    # Very aggressive - not recommended for production use
        'CONCURRENT_REQUESTS': 32, # Very high concurrency
        'CONCURRENT_REQUESTS_PER_DOMAIN': 32,
        'DEPTH_LIMIT': 5,
        'LOG_LEVEL': 'INFO',
        # Cache settings
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 86400,
        'HTTPCACHE_DIR': 'http_cache',
        # Performance optimizations
        'COOKIES_ENABLED': False,
        'RETRY_ENABLED': False,
        'REDIRECT_ENABLED': True,
        'AJAXCRAWL_ENABLED': False,
        'MEDIA_ALLOW_REDIRECTS': True
    })
    
    print("Starting Factorio Forums scraper...")
    print("Pages will be saved to the 'forum_pages' directory")
    print("URLs will be saved to 'factorio_forum_pages.csv'")
    
    process.crawl(FactorioSpider)
    process.start()
    
    print("Scraping complete!")