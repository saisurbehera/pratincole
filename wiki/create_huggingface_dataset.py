#!/usr/bin/env python3
import os
import json
import glob
import pandas as pd
from datasets import Dataset, DatasetDict, Features, Value, Sequence, load_dataset
import argparse

# Configure paths
PARSED_WIKI_DIR = "/home/sai/Desktop/factorio/pratincole/wiki/parsed_wiki"
CLEANED_FORUM_DIR = "/home/sai/Desktop/factorio/pratincole/wiki/cleaned_forum"
OUTPUT_DIR = "/home/sai/Desktop/factorio/pratincole/wiki/huggingface_dataset"
DATASET_NAME = "factorio-knowledge"

def load_wiki_files():
    """Load and process parsed wiki files"""
    print("Loading wiki files...")
    wiki_data = []
    
    # Get all wiki text files
    wiki_files = glob.glob(os.path.join(PARSED_WIKI_DIR, "*.txt"))
    total_files = len(wiki_files)
    print(f"Found {total_files} wiki files")
    
    for i, file_path in enumerate(wiki_files):
        if i % 100 == 0:
            print(f"Processing wiki file {i+1}/{total_files}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Split content into metadata and text
                parts = content.split("---\n", 2)
                
                if len(parts) >= 3:
                    metadata_str = parts[1].strip()
                    text_content = parts[2].strip()
                    
                    # Parse metadata
                    try:
                        metadata = json.loads(metadata_str)
                    except json.JSONDecodeError:
                        metadata = {"title": os.path.basename(file_path), "categories": []}
                    
                    # Create dataset entry
                    entry = {
                        "id": os.path.basename(file_path).replace(".txt", ""),
                        "title": metadata.get("title", ""),
                        "categories": metadata.get("categories", []),
                        "content": text_content,
                        "source": "wiki",
                        "url": f"https://wiki.factorio.com/{metadata.get('title', '').replace(' ', '_')}"
                    }
                    
                    wiki_data.append(entry)
                else:
                    # Handle files without proper metadata separators
                    entry = {
                        "id": os.path.basename(file_path).replace(".txt", ""),
                        "title": os.path.basename(file_path).replace(".txt", "").replace("_", " "),
                        "categories": [],
                        "content": content,
                        "source": "wiki",
                        "url": ""
                    }
                    wiki_data.append(entry)
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return wiki_data

def load_forum_files():
    """Load and process cleaned forum files"""
    print("Loading forum files...")
    forum_data = []
    
    # Get all forum JSON files
    forum_files = glob.glob(os.path.join(CLEANED_FORUM_DIR, "*.json"))
    total_files = len(forum_files)
    print(f"Found {total_files} forum files")
    
    for i, file_path in enumerate(forum_files):
        if i % 50 == 0:
            print(f"Processing forum file {i+1}/{total_files}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                forum_json = json.load(f)
                
                # Extract topic info
                topic_info = forum_json.get("topic_info", {})
                posts = forum_json.get("posts", [])
                
                # Create content from posts
                content_parts = []
                
                for post in posts:
                    author = post.get("author", "")
                    date = post.get("date", "")
                    post_content = post.get("content", "")
                    
                    # Format post with author and date
                    post_text = f"Author: {author}\nDate: {date}\n\n{post_content}"
                    
                    # Add quotes if any
                    quotes = post.get("quotes", [])
                    if quotes:
                        quote_texts = []
                        for quote in quotes:
                            quote_author = quote.get("author", "")
                            quote_content = quote.get("content", "")
                            quote_texts.append(f"Quote from {quote_author}:\n{quote_content}")
                        
                        post_text += "\n\nQuotes:\n" + "\n\n".join(quote_texts)
                    
                    content_parts.append(post_text)
                
                # Combine all posts
                combined_content = "\n\n---\n\n".join(content_parts)
                
                # Create dataset entry
                entry = {
                    "id": os.path.basename(file_path).replace(".json", ""),
                    "title": topic_info.get("title", ""),
                    "categories": [topic_info.get("section", "")],
                    "content": combined_content,
                    "source": "forum",
                    "url": topic_info.get("url", "")
                }
                
                forum_data.append(entry)
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return forum_data

def create_huggingface_dataset():
    """Create Hugging Face dataset from wiki and forum data"""
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load data
    wiki_data = load_wiki_files()
    forum_data = load_forum_files()
    
    # Create combined dataset
    all_data = wiki_data + forum_data
    print(f"Total entries: {len(all_data)} (Wiki: {len(wiki_data)}, Forum: {len(forum_data)})")
    
    # Convert to pandas DataFrame first (easier to handle)
    df = pd.DataFrame(all_data)
    
    # No train/test split, keeping all data in a single set
    # This is more appropriate for a knowledge dataset
    
    # Convert to Hugging Face Dataset
    full_dataset = Dataset.from_pandas(df)
    
    # Create dataset dictionary with a single split
    dataset_dict = DatasetDict({
        'data': full_dataset
    })
    
    # Save locally
    local_path = os.path.join(OUTPUT_DIR, DATASET_NAME)
    dataset_dict.save_to_disk(local_path)
    print(f"Dataset saved locally to {local_path}")
    
    # Create README content
    readme_content = f"""# Factorio Knowledge Dataset

This dataset contains information from the Factorio Wiki and Factorio Forums, processed and cleaned for use in NLP applications.

## Dataset Structure

The dataset contains {len(all_data)} entries in total:
- {len(wiki_data)} wiki articles
- {len(forum_data)} forum posts

All entries are contained in a single 'data' split, making it easy to use for knowledge retrieval and reference purposes.

Each entry has the following fields:
- `id`: Unique identifier for the document
- `title`: Title of the article or forum topic
- `categories`: List of categories or sections
- `content`: The main text content
- `source`: Whether the content is from "wiki" or "forum"
- `url`: URL to the original content (when available)

## Usage Examples

### Loading the dataset
```python
from datasets import load_dataset

# Load from Hugging Face Hub
dataset = load_dataset("YOUR_USERNAME/{DATASET_NAME}")

# Access entries
for item in dataset['data']:
    print(f"Title: {{item['title']}}")
    print(f"Source: {{item['source']}}")
```

### Example for retrieval
```python
# Find all entries about "belts"
belt_entries = [item for item in dataset['data'] 
                if "belt" in item['title'].lower() 
                or "belt" in item['content'].lower()]
```

## License

This dataset is derived from Factorio content which is copyrighted by Wube Software.
The data is shared for research and educational purposes.

## Citation

If you use this dataset in your research, please cite:
```
@dataset{{factorio_knowledge,
  author    = {{Factorio Community}},
  title     = {{Factorio Knowledge Dataset}},
  year      = {{2025}},
  publisher = {{Hugging Face}},
  howpublished = {{https://huggingface.co/datasets/[your-username]/{DATASET_NAME}}}
}}
```
"""
    
    # Save README
    with open(os.path.join(OUTPUT_DIR, "README.md"), 'w', encoding='utf-8') as f:
        f.write(readme_content)
        
    print("README.md created")
    
    # Export instructions
    print("\nTo push this dataset to Hugging Face Hub:")
    print("1. Install huggingface_hub: pip install huggingface_hub")
    print("2. Login to Hugging Face: huggingface-cli login")
    print(f"3. Use the following Python code to upload:")
    print(f"""
    from huggingface_hub import HfApi
    
    # Initialize the API
    api = HfApi()
    
    # Upload the dataset (replace YOUR_USERNAME with your Hugging Face username)
    api.create_repo(
        repo_id=f"YOUR_USERNAME/{DATASET_NAME}",
        repo_type="dataset",
        exist_ok=True
    )
    api.upload_folder(
        folder_path="{local_path}",
        repo_id=f"YOUR_USERNAME/{DATASET_NAME}",
        repo_type="dataset"
    )
    """)

if __name__ == "__main__":
    print(f"Creating Hugging Face dataset from Factorio wiki and forum data...")
    create_huggingface_dataset()
    print("Done!")