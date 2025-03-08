# Factorio Web Scrapers

Simple web scrapers for Factorio-related websites using Python's Scrapy framework.

## Tools Included

1. **factorio_scraper.py** - Scrapes the official Factorio Wiki
   - Filters out non-English language pages
   - Saves HTML content to local files
   - Generates a CSV report of crawled pages

2. **factorio_forum_scraper.py** - Scrapes the Factorio Forums
   - Saves forum pages to local files
   - Skips media files and downloads
   - Generates a CSV report of crawled pages

## Requirements

- Python 3.x
- Scrapy

## Usage

To run the wiki scraper:
```
python factorio_scraper.py
```

To run the forum scraper:
```
python factorio_forum_scraper.py
```

## Notes

- The scrapers are configured to be very aggressive by default (high concurrency, low delay)
- Both scrapers ignore robots.txt (please use responsibly)
- Results are saved in the "scraped_html_files" and "forum_pages" directories