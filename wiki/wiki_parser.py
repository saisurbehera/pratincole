#!/usr/bin/env python3
import os
import zipfile
import re
from bs4 import BeautifulSoup
import html
import json

# Configuration
ZIP_FILE_PATH = "/home/sai/Desktop/factorio/pratincole/wiki/wiki_xml.zip"
OUTPUT_DIR = "/home/sai/Desktop/factorio/pratincole/wiki/parsed_wiki"
TABLE_FORMAT = "markdown"  # can be "markdown" or "text"

def clean_filename(filename):
    """Clean filename to be safe for file system"""
    # Remove any leading underscores and file extensions
    base_name = os.path.basename(filename)
    if base_name.startswith('_'):
        base_name = base_name[1:]
    # Remove .html extension if present
    if base_name.endswith('.html'):
        base_name = base_name[:-5]
    # Replace problematic characters
    base_name = re.sub(r'[\\/*?:"<>|]', '_', base_name)
    return base_name + '.txt'

def extract_text_from_html(html_content):
    """Extract clean text from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()
    
    # Process tables first, before extracting text
    tables_data = []
    for table in soup.find_all('table'):
        tables_data.append(process_table(table))
        # Replace the table with a placeholder
        table_placeholder = soup.new_tag('div')
        table_placeholder.string = f"[[TABLE_{len(tables_data)}]]"
        table.replace_with(table_placeholder)
    
    # Get text and clean it up
    text = soup.get_text(separator='\n')
    
    # Clean up text: remove excessive whitespace, decode HTML entities
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r' +', ' ', text)
    text = html.unescape(text)
    
    # Add back tables where the placeholders are
    for i, table_data in enumerate(tables_data, 1):
        if table_data.strip():
            text = text.replace(f"[[TABLE_{i}]]", f"\n\n{table_data}\n\n")
    
    return text.strip()

def process_table(table):
    """Process an HTML table into a text format"""
    rows = table.find_all('tr')
    if not rows:
        return ""
    
    table_data = []
    max_cols = 0
    
    # Extract all cell data
    for row in rows:
        row_data = []
        # Handle both header and data cells
        cells = row.find_all(['th', 'td'])
        for cell in cells:
            # Get colspan to repeat the cell content
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))
            
            # Get cell text
            cell_text = cell.get_text(strip=True).replace('\n', ' ')
            
            # Add the cell data according to colspan
            for _ in range(colspan):
                row_data.append(cell_text)
                
            # TODO: Handle rowspan properly in a more sophisticated implementation
        
        table_data.append(row_data)
        max_cols = max(max_cols, len(row_data))
    
    # Pad rows to have equal columns
    for i, row in enumerate(table_data):
        if len(row) < max_cols:
            table_data[i] = row + [''] * (max_cols - len(row))
    
    # Format the table according to the chosen format
    if TABLE_FORMAT == "markdown":
        return format_table_markdown(table_data)
    else:
        return format_table_text(table_data)

def format_table_markdown(table_data):
    """Format table data as a markdown table"""
    if not table_data or not table_data[0]:
        return ""
    
    # Calculate column widths
    col_widths = [0] * len(table_data[0])
    for row in table_data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Build the table
    result = []
    
    # Header row
    header = "| " + " | ".join(str(cell).ljust(width) for cell, width in zip(table_data[0], col_widths)) + " |"
    result.append(header)
    
    # Separator row
    separator = "| " + " | ".join("-" * width for width in col_widths) + " |"
    result.append(separator)
    
    # Data rows
    for row in table_data[1:]:
        data_row = "| " + " | ".join(str(cell).ljust(width) for cell, width in zip(row, col_widths)) + " |"
        result.append(data_row)
    
    return "\n".join(result)

def format_table_text(table_data):
    """Format table data as simple text"""
    if not table_data:
        return ""
    
    result = []
    result.append("TABLE START")
    
    # Add rows
    for i, row in enumerate(table_data):
        result.append(f"ROW {i+1}: {' | '.join(str(cell) for cell in row)}")
    
    result.append("TABLE END")
    return "\n".join(result)

def extract_metadata(html_content):
    """Extract metadata from the HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    metadata = {
        "title": "",
        "categories": [],
        "links": []
    }
    
    # Extract title
    title_tag = soup.find('title')
    if title_tag:
        metadata["title"] = title_tag.get_text(strip=True)
    
    # Extract categories
    category_links = soup.find_all('a', href=re.compile(r'Category:'))
    for link in category_links:
        category = link.get_text(strip=True)
        if category:
            metadata["categories"].append(category)
    
    # Extract internal links
    internal_links = soup.find_all('a', href=re.compile(r'^[^http]'))
    for link in internal_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        if href and text and not href.startswith('#') and not 'Category:' in href:
            metadata["links"].append({"text": text, "href": href})
    
    return metadata

def process_wiki_files():
    """Process all HTML files in the ZIP archive"""
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Extract and process files
    with zipfile.ZipFile(ZIP_FILE_PATH, 'r') as zip_ref:
        file_list = [f for f in zip_ref.namelist() if f.endswith('.html')]
        
        print(f"Found {len(file_list)} HTML files to process")
        
        for i, filename in enumerate(file_list):
            if i % 100 == 0:
                print(f"Processing file {i+1}/{len(file_list)}: {filename}")
            
            # Read file content
            with zip_ref.open(filename) as file:
                html_content = file.read().decode('utf-8', errors='replace')
            
            # Extract text and metadata
            clean_text = extract_text_from_html(html_content)
            metadata = extract_metadata(html_content)
            
            # Create output data
            output_data = {
                "metadata": metadata,
                "content": clean_text
            }
            
            # Save to file
            output_filename = clean_filename(filename)
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as out_file:
                # Write metadata as JSON at the top
                out_file.write("---\n")
                out_file.write(json.dumps(metadata, indent=2, ensure_ascii=False))
                out_file.write("\n---\n\n")
                # Write content
                out_file.write(clean_text)

if __name__ == "__main__":
    print(f"Starting wiki parser...")
    print(f"Input: {ZIP_FILE_PATH}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Table format: {TABLE_FORMAT}")
    
    process_wiki_files()
    
    print("Parsing complete!")