import requests
import json
import time
import os
import re

from config.settings import (
    SANITY_API_URL,
    SANITY_WRITE_TOKEN,
    DEPLOYMENT_WEBHOOK_URL,
    get_post_document_template
)

# --- SEO Enhancer Integration ---
from seo_enhancer import enhance_post, load_index, save_index

# --- Models ---
# Ideally import Article type for hinting, but duck typing is fine
# from src.models import Article 

# Constant for the author ID used by the bot
AI_AUTHOR_ID = "ai-bot"
AI_AUTHOR_NAME = "Autoblog AI Agent"


# -----------------------------------------------------------
# Sanity Helpers
# -----------------------------------------------------------
def ensure_author_document_exists():
    """
    Checks for the existence of the AI author document (ID: ai-bot) in Sanity.
    If it does not exist, it creates it.
    """
    mutation = {
        "mutations": [
            {
                "createIfNotExists": {
                    "_id": AI_AUTHOR_ID,
                    "_type": "author",
                    "name": AI_AUTHOR_NAME,
                    "slug": {"_type": "slug", "current": "autoblog-ai"},
                }
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SANITY_WRITE_TOKEN}"
    }

    try:
        response = requests.post(SANITY_API_URL, headers=headers, data=json.dumps(mutation))
        response.raise_for_status()
        print(f"  -> Successfully ensured author document '{AI_AUTHOR_ID}' exists.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error ensuring AI author document exists: {e}")
        return False


def upload_image_to_sanity(image_path):
    """
    Uploads a local image file to Sanity and returns the Asset ID.
    """
    if not image_path or not os.path.exists(image_path):
        print(f"⚠️ Image path not found or empty: {image_path}")
        return None

    print(f"📤 Uploading image to Sanity: {image_path}")

    asset_url = SANITY_API_URL.replace("/data/mutate/", "/assets/images/")

    headers = {
        "Authorization": f"Bearer {SANITY_WRITE_TOKEN}",
        "Content-Type": "image/png"
    }

    try:
        with open(image_path, "rb") as img_file:
            response = requests.post(asset_url, headers=headers, data=img_file)
            response.raise_for_status()
            
            asset_document = response.json().get('document', {})
            asset_id = asset_document.get('_id')
            
            if asset_id:
                print(f"✅ Image uploaded successfully. Asset ID: {asset_id}")
                return asset_id
            else:
                print("❌ Image uploaded, but no Asset ID returned.")
                return None

    except Exception as e:
        print(f"❌ Error uploading image to Sanity: {e}")
        return None


# -----------------------------------------------------------
# Portable Text Logic
# -----------------------------------------------------------
def markdown_to_portable_text(markdown_text):
    """
    Converts strictly CLEAN SECTION BODY markdown to Portable Text.
    Assumes no # H1/H2 (since headers are structural now).
    Supports bold, lists, and tables.
    """
    blocks = []
    lines = markdown_text.split("\n")
    table_rows = []

    def flush_table():
        if table_rows:
            # Format for @sanity/table plugin: rows must be objects with cells arrays
            formatted_rows = []
            for row in table_rows:
                formatted_rows.append({
                    "_type": "tableRow",
                    "_key": str(hash(str(row) + str(time.time()))),
                    "cells": row
                })
            table_block = {
                "_type": "table",
                "rows": formatted_rows, 
                "_key": str(hash(str(table_rows) + str(time.time())))
            }
            blocks.append(table_block)
            table_rows.clear()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # --- Table Detection ---
        if "|" in line:
            row_cells = [c.strip() for c in line.strip("|").split("|")]
            table_rows.append(row_cells)
            continue
        flush_table()

        # --- Basic Formatting ---
        # Note: A real parser might use regex for bold **text**, 
        # but for simplicity we treat paragraphs as spans.
        # We assume section bodies don't have H1/H2.
        
        style = "normal"
        # Lists
        if line.startswith("- "):
            style = "normal" 
            line = line[2:] 
            # Ideally Sanity lists are block properties 'listItem': 'bullet'.
            # For this 'quick' implementation, we'll just treat them as lines.
            
        block = {
            "_type": "block",
            "style": style,
            "children": [
                {
                    "_key": str(hash(line + str(time.time()))),
                    "_type": "span",
                    "text": line,
                    "marks": []
                }
            ]
        }
        blocks.append(block)

    flush_table()
    return blocks


# -----------------------------------------------------------
# Main Publisher
# -----------------------------------------------------------
def publish_to_sanity(article, category="general"):
    """
    Publishes the Article object to Sanity.
    Handles image uploads and full body assembly.
    """
    print("--- 3. Publishing content to Sanity.io ---")

    if not ensure_author_document_exists():
        return False

    # 1. Upload Hero Image
    hero_asset_id = None
    if article.hero_image and article.hero_image.asset_id:
        # Note: logic hack, we stored the path in asset_id temporarily
        hero_asset_id = upload_image_to_sanity(article.hero_image.asset_id)
        article.hero_image.asset_id = hero_asset_id # Update with real ID

    # 2. Upload Section Images
    # Loop sections, verify if image exists and is a path (not None/empty)
    for section in article.sections:
        if section.image and section.image.asset_id:
             # Check if it looks like a path (contains slashes)
            if "/" in section.image.asset_id:
                 real_id = upload_image_to_sanity(section.image.asset_id)
                 section.image.asset_id = real_id

    # 3. Assemble Portable Text Body
    print("🏗️ Assembling Portable Text Body with In-Article Images...")
    full_body_blocks = []
    
    for section in article.sections:
        # A. Section Heading (H2)
        h2_block = {
            "_type": "block",
            "style": "h2",
            "children": [{
                "_type": "span",
                "text": section.heading,
                "marks": []
            }]
        }
        full_body_blocks.append(h2_block)
        
        # B. Section Body
        body_blocks = markdown_to_portable_text(section.body)
        full_body_blocks.extend(body_blocks)
        
        # C. Section Image (if valid asset exists)
        if section.image and section.image.asset_id and not "/" in section.image.asset_id:
            # It's a real Sanity ID now
            image_block = {
                "_type": "image",
                "asset": {
                    "_type": "reference",
                    "_ref": section.image.asset_id
                },
                "alt": section.image.alt_text or section.heading
            }
            full_body_blocks.append(image_block)

    # 4. SEO Enhancement
    print("🔍 Enhancing SEO metadata...")
    index = load_index()
    
    # Construct a dict for the enhancer since it expects dict
    post_dict_for_seo = {
        "title": article.title,
        "slug": article.slug,
        "content": " ".join([s.body for s in article.sections]), # Plain text approximation
        "images": [], # Paths are gone, IDs are here. We can skip logic reliant on local paths
        "date": None,
        "category": category
    }
    
    enhanced = enhance_post(post=post_dict_for_seo, index=index)
    seo_meta = enhanced.get("meta", {})
    index.append(seo_meta)
    save_index(index)

    # 5. Create Document
    document = get_post_document_template(
        title=article.title,
        slug=article.slug,
        body_portable_text=full_body_blocks,
        author_id=AI_AUTHOR_ID
    )

    # Attach Hero
    if hero_asset_id:
        document['mainImage'] = {
            '_type': 'image',
            'asset': {
                '_type': 'reference',
                '_ref': hero_asset_id
            },
            'alt': article.hero_image.alt_text or article.title
        }

    # Attach SEO
    document["seo"] = {
        "metaTitle": article.seo_title,
        "metaDescription": article.meta_description,
        "keywords": article.keywords,
        "readingTime": article.reading_time_minutes,
        "internalLinks": enhanced.get("internal_links", []),
        "faqs": enhanced.get("faqs", []),
        "jsonldArticle": json.dumps(enhanced.get("jsonld", {}).get("article", {})),
        "jsonldFaq": json.dumps(enhanced.get("jsonld", {}).get("faq", {})),
        "imageAlt": article.hero_image.alt_text or article.title
    }

    # 6. Publish
    mutation = {"mutations": [{"create": document}]}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SANITY_WRITE_TOKEN}"
    }

    try:
        resp = requests.post(SANITY_API_URL, headers=headers, data=json.dumps(mutation))
        resp.raise_for_status()
        res_data = resp.json()['results'][0]
        doc_id = res_data.get('document', {}).get('_id', res_data.get('id', 'UNKNOWN'))
        print(f"-> Published successfully! ID: {doc_id}")
    except Exception as e:
        print(f"❌ Failed to publish: {e}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)
        return False
        
    return True
