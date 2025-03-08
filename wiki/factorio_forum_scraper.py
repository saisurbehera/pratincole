import scrapy
from scrapy.crawler import CrawlerProcess
import re
import os
from urllib.parse import urlparse, parse_qs, unquote

class FactorioForumSpider(scrapy.Spider):
    name = "factorio_forum_spider"
    
    # Configure for forum website
    allowed_domains = ["forums.factorio.com"]
    start_urls = ["https://forums.factorio.com/"]
    
    # Directory to save HTML files
    output_dir = "forum_pages"
    
    def __init__(self, *args, **kwargs):
        super(FactorioForumSpider, self).__init__(*args, **kwargs)
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def parse(self, response):
        """Main parsing method for forum pages"""
        # Skip non-HTML responses (like image downloads)
        if not isinstance(response, scrapy.http.TextResponse):
            self.logger.info(f"Skipping non-HTML content: {response.url}")
            return
            
        try:
            # Extract page title and content
            title = response.css('title::text').get()
            
            # Save the page content
            self.save_page(response)
            
            # Output current page data
            yield {
                'url': response.url,
                'title': title,
            }
            
            # Process all links on the page
            for link in response.css('a::attr(href)').getall():
                # Skip problematic links
                if self.should_skip_link(link):
                    continue
                    
                # Follow valid links
                try:
                    yield response.follow(link, self.parse)
                except ValueError as e:
                    self.logger.error(f"Error following link {link}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error processing {response.url}: {e}")
    
    def should_skip_link(self, link):
        """Return True if link should be skipped"""
        # Skip empty, javascript and fragment links
        if not link or link.startswith('javascript:') or link.startswith('#'):
            return True
            
        # Skip file downloads and media files
        if any(pattern in link.lower() for pattern in [
            'download/file.php', 
            '.jpg', '.jpeg', '.png', '.gif', 
            '.pdf', '.zip', '.rar', '.mp4'
        ]):
            return True
            
        return False
    
    def save_page(self, response):
        """Save the page content to a file"""
        # Parse the URL to create a filename
        parsed_url = urlparse(response.url)
        path = parsed_url.path
        
        # Create a reasonable filename
        if path == "/" or not path:
            filename = "index"
        else:
            # Remove leading slash and replace slashes with underscores
            filename = path.lstrip('/').replace('/', '_')
        
        # Add query parameters to filename if they exist
        if parsed_url.query:
            query_part = parsed_url.query.replace('&', '_').replace('=', '_')
            filename = f"{filename}_{query_part}"
        
        # Replace problematic characters and limit length
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        filename = filename[:100]  # Limit filename length
        
        # Prepend underscore and add extension
        filename = f"_{filename}.html"
        
        # Save the HTML content
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(response.body)

# Run the spider
if __name__ == "__main__":
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'FEED_FORMAT': 'csv',
        'FEED_URI': 'factorio_forum_pages.csv',
        'ROBOTSTXT_OBEY': False,  # WARNING: Disabling robots.txt - use responsibly
        'DOWNLOAD_DELAY': 0.1,    # Very aggressive crawling
        'CONCURRENT_REQUESTS': 32,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 32,
        'DEPTH_LIMIT': 5,         # Limit crawl depth
        'LOG_LEVEL': 'INFO',
        # Performance optimizations
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 86400,
        'HTTPCACHE_DIR': 'forum_cache',
        'COOKIES_ENABLED': False,
        'RETRY_ENABLED': False,
        'REDIRECT_ENABLED': True,
        'MEDIA_ALLOW_REDIRECTS': True,
        # Skip media downloads
        'MEDIA_DOWNLOADS': False,
    })
    
    print("Starting Factorio Forums scraper...")
    print("Pages will be saved to the 'forum_pages' directory")
    print("URLs will be saved to 'factorio_forum_pages.csv'")
    
    process.crawl(FactorioForumSpider)
    process.start()
    
    print("Scraping complete!")