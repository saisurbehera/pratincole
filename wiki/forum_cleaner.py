#!/usr/bin/env python3
import os
import re
import json
import datetime
from bs4 import BeautifulSoup
import html
import csv

# Configuration
FORUM_PAGES_DIR = "/mnt/sai/factorio_forum"
OUTPUT_DIR = "/home/sai/Desktop/factorio/pratincole/wiki/cleaned_forum_all"
CSV_OUTPUT = "/home/sai/Desktop/factorio/pratincole/wiki/forum_topics_all.csv"

def clean_filename(filename):
    """Create a clean filename from the original forum page filename"""
    # Extract topic ID or post ID from filename
    topic_match = re.search(r'_viewtopic\.php_t_(\d+)', filename)
    post_match = re.search(r'_viewtopic\.php_p_(\d+)', filename)
    
    if topic_match:
        return f"topic_{topic_match.group(1)}.json"
    elif post_match:
        return f"post_{post_match.group(1)}.json"
    else:
        # Fallback - just remove special characters
        clean = re.sub(r'[^\w\-\.]', '_', filename)
        return f"forum_{clean}.json"

def extract_topic_info(soup):
    """Extract basic topic information from the page"""
    info = {
        "title": "",
        "topic_id": None,
        "post_id": None,
        "url": "",
        "section": "",
        "timestamp": "",
        "author": "",
        "author_id": None,
        "extracted_date": datetime.datetime.now().isoformat()
    }
    
    # Extract title
    title_tag = soup.find('title')
    if title_tag:
        info["title"] = title_tag.get_text().replace(" - Factorio Forums", "").strip()
    
    # Extract topic/post IDs from meta tags
    og_url = soup.find('meta', property='og:url')
    if og_url:
        url = og_url.get('content', '')
        info["url"] = url
        
        # Try to extract topic or post ID
        topic_match = re.search(r't=(\d+)', url)
        post_match = re.search(r'p=(\d+)', url)
        
        if topic_match:
            info["topic_id"] = int(topic_match.group(1))
        if post_match:
            info["post_id"] = int(post_match.group(1))
    
    # Extract section
    section_meta = soup.find('meta', property='article:section')
    if section_meta:
        info["section"] = section_meta.get('content', '')
    
    # Extract author and timestamp
    author_meta = soup.find('meta', property='article:author')
    if author_meta:
        info["author"] = author_meta.get('content', '')
        
    time_meta = soup.find('meta', property='article:published_time')
    if time_meta:
        info["timestamp"] = time_meta.get('content', '')
        
    # Try to extract author ID if it exists
    author_link = soup.find('a', href=lambda href: href and 'memberlist.php?mode=viewprofile&u=' in href)
    if author_link:
        author_id_match = re.search(r'u=(\d+)', author_link.get('href', ''))
        if author_id_match:
            info["author_id"] = int(author_id_match.group(1))
            
    return info

def extract_posts(soup):
    """Extract all posts from the topic page"""
    posts = []
    
    # Find all post divs
    post_divs = soup.find_all('div', class_='post')
    
    for post_div in post_divs:
        post = {
            "post_id": None,
            "author": "",
            "author_id": None,
            "date": "",
            "content": "",
            "quotes": []
        }
        
        # Get post ID
        post_id_attr = post_div.get('id', '')
        post_id_match = re.search(r'p(\d+)', post_id_attr)
        if post_id_match:
            post["post_id"] = int(post_id_match.group(1))
        
        # Get author
        author_elem = post_div.find('a', class_='username')
        if author_elem:
            post["author"] = author_elem.get_text().strip()
            
            # Try to extract author ID
            author_link = author_elem.get('href', '')
            author_id_match = re.search(r'u=(\d+)', author_link)
            if author_id_match:
                post["author_id"] = int(author_id_match.group(1))
        
        # Get date
        date_elem = post_div.find('time')
        if date_elem:
            post["date"] = date_elem.get('datetime', '')
        
        # Get content
        content_div = post_div.find('div', class_='content')
        if content_div:
            # Extract quotes
            quotes = []
            for quote_div in content_div.find_all('blockquote'):
                quote = {
                    "author": "",
                    "content": ""
                }
                
                cite = quote_div.find('cite')
                if cite:
                    quote["author"] = cite.get_text().strip()
                
                quote_content = quote_div.find('div', class_='quote-content')
                if quote_content:
                    quote["content"] = quote_content.get_text().strip()
                
                quotes.append(quote)
                
                # Remove the blockquote to avoid duplicating content
                quote_div.extract()
            
            post["quotes"] = quotes
            
            # Clean up remaining content
            post["content"] = content_div.get_text(separator=' ').strip()
        
        posts.append(post)
    
    return posts

def process_forum_pages():
    """Process all forum page files in the source directory"""
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # List of all processed topic data
    all_topics = []
    
    # Get viewtopic files
    viewtopic_files = [f for f in os.listdir(FORUM_PAGES_DIR) if "_viewtopic" in f]
    total_files = len(viewtopic_files)
    
    print(f"Found {total_files} forum topic pages to process")
    
    # Process each file
    for i, filename in enumerate(viewtopic_files):
        if i % 10 == 0:
            print(f"Processing file {i+1}/{total_files}: {filename}")
        
        filepath = os.path.join(FORUM_PAGES_DIR, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
                html_content = file.read()
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract topic info and posts
            topic_info = extract_topic_info(soup)
            posts = extract_posts(soup)
            
            # Create output data structure
            output_data = {
                "topic_info": topic_info,
                "posts": posts
            }
            
            # Generate output filename
            output_filename = clean_filename(filename)
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
            # Save to JSON file
            with open(output_path, 'w', encoding='utf-8') as out_file:
                json.dump(output_data, out_file, ensure_ascii=False, indent=2)
            
            # Add to all topics list
            all_topics.append({
                "filename": output_filename,
                "title": topic_info["title"],
                "topic_id": topic_info["topic_id"],
                "post_id": topic_info["post_id"],
                "url": topic_info["url"],
                "section": topic_info["section"],
                "author": topic_info["author"],
                "timestamp": topic_info["timestamp"],
                "post_count": len(posts)
            })
            
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
    
    # Write topics to CSV
    with open(CSV_OUTPUT, 'w', newline='', encoding='utf-8') as csv_file:
        fieldnames = ['filename', 'title', 'topic_id', 'post_id', 'url', 'section', 
                     'author', 'timestamp', 'post_count']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
        writer.writeheader()
        for topic in all_topics:
            writer.writerow(topic)
    
    print(f"Processed {len(all_topics)} forum topics")
    print(f"Results saved to {OUTPUT_DIR}")
    print(f"Topic index saved to {CSV_OUTPUT}")

if __name__ == "__main__":
    print("Starting Factorio forum page cleaner...")
    process_forum_pages()
