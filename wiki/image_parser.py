#!/usr/bin/env python3
import os
import zipfile
import re
import csv
from bs4 import BeautifulSoup
import urllib.parse

# Configuration
ZIP_FILE_PATH = "/home/sai/Desktop/factorio/pratincole/wiki/wiki_xml.zip"
OUTPUT_CSV = "/home/sai/Desktop/factorio/pratincole/wiki/wiki_images.csv"
OUTPUT_DIR = "/home/sai/Desktop/factorio/pratincole/wiki/image_data"
BASE_URL = "https://wiki.factorio.com/images/"

def clean_image_name(name):
    """Clean and normalize image name"""
    # Extract just the filename without path or extension
    filename = os.path.basename(name)
    # Remove any URL encoding
    filename = urllib.parse.unquote(filename)
    # Strip extension if present
    if '.' in filename:
        filename = filename[:filename.rindex('.')]
    
    # Remove pixel size prefix (like 32px-, 64px-, etc.)
    filename = re.sub(r'^\d+px-', '', filename)
    
    # Return clean name
    return filename

def find_images_in_html(html_content, source_file):
    """Extract image references from HTML content"""
    images = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Keep track of processed image names to avoid duplicates
    processed_images = set()
    
    # Find all img tags
    for img in soup.find_all('img'):
        src = img.get('src', '')
        alt = img.get('alt', '')
        title = img.get('title', '')
        
        if src:
            # Clean up the source path
            src = src.strip()
            if src.startswith('/'):
                src = src[1:]
                
            # Extract image name and create URL
            image_name = clean_image_name(src)
            file_extension = os.path.splitext(src)[1].lower()
            
            # Skip if we've already processed this base image name
            if image_name in processed_images:
                continue
                
            processed_images.add(image_name)
            
            # Create canonical URL
            url = BASE_URL + image_name + file_extension
            
            images.append({
                'source_file': source_file,
                'src': src,
                'alt': alt,
                'title': title,
                'image_name': image_name,
                'extension': file_extension,
                'url': url,
                'original_src': src  # Keep track of original source for reference
            })
    
    return images

def extract_direct_image_files(zip_ref):
    """Extract information about image files directly in the zip"""
    images = []
    # Filter for image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg']
    image_files = [f for f in zip_ref.namelist() 
                  if any(f.lower().endswith(ext) for ext in image_extensions)]
    
    # Keep track of processed image names to avoid duplicates
    processed_images = set()
    
    for image_path in image_files:
        filename = os.path.basename(image_path)
        image_name = clean_image_name(filename)
        file_extension = os.path.splitext(filename)[1].lower()
        url = BASE_URL + image_name + file_extension
        
        # Skip if we've already processed this base image name
        if image_name in processed_images:
            continue
            
        processed_images.add(image_name)
        
        images.append({
            'source_file': 'direct_file',
            'src': image_path,
            'alt': '',
            'title': '',
            'image_name': image_name,
            'extension': file_extension,
            'url': url,
            'original_filename': filename  # Keep track of original for reference
        })
    
    return images

def process_wiki_files():
    """Process all files in the ZIP archive to find images"""
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    all_images = []
    # Global set to track unique image names across both direct files and HTML references
    global_image_names = set()
    
    # Extract and process files
    with zipfile.ZipFile(ZIP_FILE_PATH, 'r') as zip_ref:
        # First, get direct image files
        direct_images = extract_direct_image_files(zip_ref)
        
        # Add these direct image names to our global tracking set
        for img in direct_images:
            global_image_names.add(img['image_name'])
            
        all_images.extend(direct_images)
        print(f"Found {len(direct_images)} direct image files in the archive")
        
        # Then extract images referenced in HTML files
        html_files = [f for f in zip_ref.namelist() if f.endswith('.html')]
        
        print(f"Processing {len(html_files)} HTML files for image references")
        
        for i, filename in enumerate(html_files):
            if i % 100 == 0:
                print(f"Processing file {i+1}/{len(html_files)}: {filename}")
            
            # Read file content
            try:
                with zip_ref.open(filename) as file:
                    html_content = file.read().decode('utf-8', errors='replace')
                
                # Extract images from HTML
                html_images = find_images_in_html(html_content, filename)
                
                # Only add images we haven't seen yet (across both direct and HTML)
                for img in html_images:
                    if img['image_name'] not in global_image_names:
                        global_image_names.add(img['image_name'])
                        all_images.append(img)
            except Exception as e:
                print(f"Error processing file {filename}: {e}")
    
    # Sort images by name for consistency
    all_images.sort(key=lambda x: x['image_name'])
    print(f"Found {len(all_images)} unique images after filtering duplicates")
    
    # Write image data to CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csv_file:
        fieldnames = ['image_name', 'extension', 'url', 'src', 'alt', 'title', 'source_file', 
                      'original_src', 'original_filename']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction='ignore')
        
        writer.writeheader()
        for img in all_images:
            writer.writerow(img)
    
    # Create a crawler script to download these images
    create_image_crawler(all_images)
    
    return all_images

def create_image_crawler(images):
    """Create a Python script to download the images"""
    crawler_script = os.path.join(OUTPUT_DIR, "image_crawler.py")
    
    script_content = f"""#!/usr/bin/env python3
import os
import csv
import requests
import time
from concurrent.futures import ThreadPoolExecutor

# Configuration
CSV_FILE = "{OUTPUT_CSV}"
OUTPUT_DIR = "{OUTPUT_DIR}/images"
MAX_WORKERS = 5  # Number of parallel downloads
DELAY = 0.5  # Delay between downloads in seconds

def download_image(url, filename):
    '''Download an image from URL and save to filename'''
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Don't re-download existing files
        if os.path.exists(filename):
            print(f"Skipping existing file: {{filename}}")
            return True
            
        # Download the image
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded: {{filename}}")
            return True
        else:
            print(f"Failed to download {{url}}: HTTP {{response.status_code}}")
            return False
    except Exception as e:
        print(f"Error downloading {{url}}: {{e}}")
        return False

def main():
    # Create output directory
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Read image CSV
    images = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            images.append(row)
    
    print(f"Found {{len(images)}} images to download")
    
    # Create a list of download tasks
    download_tasks = []
    for img in images:
        url = img['url']
        filename = os.path.join(OUTPUT_DIR, img['image_name'] + img['extension'])
        download_tasks.append((url, filename))
    
    # Download images with a thread pool
    success_count = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for i, (url, filename) in enumerate(download_tasks):
            future = executor.submit(download_image, url, filename)
            if future.result():
                success_count += 1
            
            # Add delay between submissions to be nice to the server
            if i < len(download_tasks) - 1:  # Don't delay after the last one
                time.sleep(DELAY)
    
    print(f"Download complete. Successfully downloaded {{success_count}} of {{len(images)}} images.")

if __name__ == "__main__":
    main()
"""
    
    with open(crawler_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Make the crawler script executable
    os.chmod(crawler_script, 0o755)
    
    print(f"Image crawler script created at: {crawler_script}")
    print(f"Run the crawler to download images with: python3 {crawler_script}")

if __name__ == "__main__":
    print(f"Starting image parser...")
    print(f"Input: {ZIP_FILE_PATH}")
    print(f"Output CSV: {OUTPUT_CSV}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    images = process_wiki_files()
    
    print(f"Parsing complete! Found {len(images)} images.")
    print(f"Image data saved to: {OUTPUT_CSV}")