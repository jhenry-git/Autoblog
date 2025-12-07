import requests
import json
import time
import os

from config.sanity_config import (
    SANITY_API_URL,
    SANITY_WRITE_TOKEN,
    DEPLOYMENT_WEBHOOK_URL,
    get_post_document_template
)

# --- SEO Enhancer Integration ---
from seo_enhancer import enhance_post, load_index, save_index

# Constant for the author ID used by the bot
AI_AUTHOR_ID = "ai-bot"
AI_AUTHOR_NAME = "Autoblog AI Agent"


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


def publish_to_sanity(generated_content, image_path=None):
    """
    Creates a new document in Sanity and triggers the frontend deployment.
    
    Args:
        generated_content (dict): Content structure from the AI generator.
        image_path (str, optional): Local path to the generated image.
    """
    print("--- 3. Publishing content to Sanity.io ---")
    
    if not generated_content:
        print("Error: No content provided for publishing.")
        return False

    # --- Ensure AI Author Exists ---
    if not ensure_author_document_exists():
        print("Publishing aborted: Could not create/verify AI author document.")
        return False

    # --- Upload Main Blog Image ---
    image_asset_id = None
    if image_path:
        image_asset_id = upload_image_to_sanity(image_path)

    # ============================================================
    # 🚀 SEO Enhancer Integration
    # ============================================================
    print("🔍 Enhancing SEO metadata...")

    # Load the index of all previous posts
    index = load_index()

    # Enhance SEO using the full SEO engine
    enhanced = enhance_post(
        post={
            "title": generated_content.get("title", "Untitled"),
            "slug": generated_content.get("slug", ""),
            "content": generated_content.get("plain_text_body", ""),
            "images": [image_path] if image_path else [],
            "date": generated_content.get("date"),
            "category": generated_content.get("category", "general")
        },
        index=index
    )

    seo_meta = enhanced.get("meta", {})

    # Update index and save
    index.append(seo_meta)
    save_index(index)

    print("✅ SEO enhancement complete.")

    # --- Prepare the Sanity Document ---
    document = get_post_document_template(
        title=generated_content.get('title', 'Untitled'),
        slug=seo_meta.get("slug", generated_content.get('slug', '')),
        body_portable_text=generated_content.get('portable_text_body', []),
        author_id=AI_AUTHOR_ID
    )

    # --- Attach Main Image ---
    if image_asset_id:
        document['mainImage'] = {
            '_type': 'image',
            'asset': {
                '_type': 'reference',
                '_ref': image_asset_id
            },
            'alt': seo_meta.get("image_alt", generated_content.get('title', 'Blog Image'))
        }

    # --- Inject SEO Fields (Safe Defaults) ---
    document["seo"] = {
        "metaTitle": seo_meta.get("meta_title", ""),
        "metaDescription": seo_meta.get("meta_description", ""),
        "canonicalUrl": seo_meta.get("canonical_url", ""),
        "keywords": seo_meta.get("keywords", []),
        "readingTime": seo_meta.get("reading_time", 1),
        "internalLinks": enhanced.get("internal_links", []),
        "faqs": enhanced.get("faqs", []),
        
        # 👇 UPDATED: Convert JSON objects to Strings using json.dumps()
        "jsonldArticle": json.dumps(enhanced.get("jsonld", {}).get("article", {})),
        "jsonldFaq": json.dumps(enhanced.get("jsonld", {}).get("faq", {})),
        
        "ogImage": seo_meta.get("image"),
        "imageAlt": seo_meta.get("image_alt"),
    }

    print("✅ SEO fields successfully attached to Sanity document.")

    # --- Mutation Payload ---
    mutation = {
        "mutations": [
            {
                "create": document
            }
        ]
    }
    
    # --- POST Document to Sanity ---
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SANITY_WRITE_TOKEN}"
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            sanity_response = requests.post(SANITY_API_URL, headers=headers, data=json.dumps(mutation))
            sanity_response.raise_for_status()
            
            result_data = sanity_response.json()['results'][0]
            document_id = result_data.get('document', {}).get('_id', result_data.get('id', 'UNKNOWN_ID'))
            
            print(f"-> Successfully created document: {generated_content.get('title', 'Untitled')} (ID: {document_id})")
            break
            
        except requests.exceptions.RequestException as e:
            # 👇 UPDATED: Print detailed Sanity error response for debugging
            if hasattr(e, 'response') and e.response is not None:
                print(f"\n❌ SANITY ERROR DETAILS:\n{e.response.text}\n")
            
            if attempt < max_retries - 1:
                print(f"Sanity publishing attempt {attempt + 1} failed: {e}. Retrying in 2s...")
                time.sleep(2)
            else:
                print(f"Final error publishing to Sanity.io: {e}")
                return False
        
    # --- Trigger Frontend Deployment ---
    print("--- 4. Triggering frontend build ---")
    if not DEPLOYMENT_WEBHOOK_URL:
        print("Warning: DEPLOYMENT_WEBHOOK_URL is not set. Skipping deployment trigger.")
        return True

    try:
        deploy_response = requests.post(DEPLOYMENT_WEBHOOK_URL)
        deploy_response.raise_for_status()
        print("-> Frontend deployment trigger successful!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error triggering deployment webhook: {e}")
        return False
