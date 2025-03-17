#!/usr/bin/env python3
import os
import json
import glob
import pandas as pd
from datasets import Dataset, DatasetDict
import argparse

# Configure paths
CLEANED_FORUM_DIR = "/home/sai/Desktop/factorio/pratincole/wiki/cleaned_forum_all"
OUTPUT_DIR = "/home/sai/Desktop/factorio/pratincole/wiki/huggingface_dataset"
DATASET_NAME = "factorio-forum"

def load_forum_files():
    """Load and process cleaned forum files"""
    print("Loading forum files...")
    forum_data = []
    
    # Get all forum JSON files - focusing only on topic_*.json files 
    # (better structured data than forum_* files)
    forum_files = glob.glob(os.path.join(CLEANED_FORUM_DIR, "topic_*.json"))
    total_files = len(forum_files)
    print(f"Found {total_files} forum topic files")
    
    for i, file_path in enumerate(forum_files):
        if i % 500 == 0:
            print(f"Processing forum file {i+1}/{total_files}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                forum_json = json.load(f)
                
                # Extract topic info
                topic_info = forum_json.get("topic_info", {})
                posts = forum_json.get("posts", [])
                
                # Skip empty topics (sometimes there are redirects that have no content)
                if len(posts) == 0:
                    continue
                
                # Create content from posts
                content_parts = []
                
                # Get first post (original question/topic)
                first_post = None
                remaining_posts = []
                
                if posts:
                    first_post = posts[0]
                    remaining_posts = posts[1:]
                
                # Create dataset entry
                topic_id = os.path.basename(file_path).replace("topic_", "").replace(".json", "")
                
                # Extract the first post content (often the question or main topic)
                first_post_content = ""
                first_post_author = ""
                if first_post:
                    first_post_author = first_post.get("author", "")
                    first_post_content = first_post.get("content", "")
                
                # Extract responses
                responses = []
                for post in remaining_posts:
                    author = post.get("author", "")
                    content = post.get("content", "")
                    date = post.get("date", "")
                    quotes = post.get("quotes", [])
                    
                    response = {
                        "author": author,
                        "date": date,
                        "content": content,
                        "quotes": quotes
                    }
                    responses.append(response)
                
                # Create dataset entry
                entry = {
                    "id": f"forum-topic-{topic_id}",
                    "topic_id": topic_id,
                    "title": topic_info.get("title", ""),
                    "section": topic_info.get("section", ""),
                    "url": topic_info.get("url", ""),
                    "author": first_post_author,
                    "question": first_post_content,
                    "responses": responses,
                    "response_count": len(responses),
                    "timestamp": topic_info.get("timestamp", "")
                }
                
                forum_data.append(entry)
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return forum_data

def create_huggingface_dataset():
    """Create Hugging Face dataset from forum data"""
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load data
    forum_data = load_forum_files()
    print(f"Total entries: {len(forum_data)}")
    
    # Convert to pandas DataFrame first
    df = pd.DataFrame(forum_data)
    
    # Create Hugging Face Dataset - all in one split
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
    readme_content = f"""# Factorio Forum Dataset

This dataset contains discussions from the Factorio Forums, processed and cleaned for use in NLP applications.

## Dataset Structure

The dataset contains {len(forum_data)} forum topics with their responses.

Each entry has the following fields:
- `id`: Unique identifier for the forum topic
- `topic_id`: Original forum topic ID
- `title`: Title of the forum topic
- `section`: Forum section (e.g., "Modding", "Troubleshooting")
- `url`: URL to the original topic
- `author`: Author of the original post
- `question`: Content of the first post (typically the question or topic starter)
- `responses`: List of response posts, each with:
  - `author`: Responder's username
  - `date`: Timestamp of the response
  - `content`: Text content of the response
  - `quotes`: List of quotes from other posts
- `response_count`: Number of responses
- `timestamp`: Original posting date

## Usage Examples

### Loading the dataset
```python
from datasets import load_dataset

# Load from Hugging Face Hub
dataset = load_dataset("YOUR_USERNAME/{DATASET_NAME}")

# Access entries
for item in dataset['data']:
    print(f"Title: {{item['title']}}")
    print(f"Question: {{item['question'][:100]}}...")
    print(f"Response count: {{item['response_count']}}")
```

### Example for topic search
```python
# Find all entries discussing belts
belt_topics = [item for item in dataset['data'] 
              if "belt" in item['title'].lower() 
              or "belt" in item['question'].lower()]
print(f"Found {{len(belt_topics)}} topics about belts")
```

## License

This dataset is derived from Factorio Forum content which is copyrighted by Wube Software.
The data is shared for research and educational purposes.

## Citation

If you use this dataset in your research, please cite:
```
@dataset{{factorio_forum,
  author    = {{Factorio Community}},
  title     = {{Factorio Forum Dataset}},
  year      = {{2025}},
  publisher = {{Hugging Face}},
  howpublished = {{https://huggingface.co/datasets/[your-username]/{DATASET_NAME}}}
}}
```
"""
    
    # Save README
    with open(os.path.join(OUTPUT_DIR, "README_FORUM.md"), 'w', encoding='utf-8') as f:
        f.write(readme_content)
        
    print("README_FORUM.md created")
    
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
    print(f"Creating Hugging Face dataset from Factorio forum data...")
    create_huggingface_dataset()
    print("Done!")