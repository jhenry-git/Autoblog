import requests
import json
import time
from config.sanity_config import (
    SANITY_API_URL,
    SANITY_WRITE_TOKEN,
    DEPLOYMENT_WEBHOOK_URL,
    get_post_document_template
)

# Constant for the author ID used by the bot
AI_AUTHOR_ID = "ai-bot"
AI_AUTHOR_NAME = "Autoblog AI Agent"

def ensure_author_document_exists():
    """
    Checks for the existence of the AI author document (ID: ai-bot) in Sanity.
    If it does not exist, it creates it.
    """
    
    # We must use the 'createIfNotExists' mutation type to avoid conflicts
    # if the document already exists, and create it if it doesn't.
    mutation = {
        "mutations": [
            {
                "createIfNotExists": {
                    "_id": AI_AUTHOR_ID,
                    "_type": "author",
                    "name": AI_AUTHOR_NAME,
                    # Add any other required author fields here (e.g., slug, image)
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
        # Use the 'dryRun' parameter to test if a mutation would succeed without actually applying it.
        # However, for simplicity and ensuring creation, we just attempt the createIfNotExists mutation.
        response = requests.post(SANITY_API_URL, headers=headers, data=json.dumps(mutation))
        response.raise_for_status()
        
        # Sanity returns a 200 OK even if the document already existed.
        print(f"  -> Successfully ensured author document '{AI_AUTHOR_ID}' exists.")
        return True
    
    except requests.exceptions.RequestException as e:
        print(f"Error ensuring AI author document exists: {e}")
        return False


def publish_to_sanity(generated_content):
    """
    Creates a new document in Sanity and triggers the frontend deployment.
    
    Args:
        generated_content (dict): The structured content from the AI generator.
        
    Returns:
        bool: True if publishing and deployment were successful, False otherwise.
    """
    print("--- 3. Publishing content to Sanity.io ---")
    
    if not generated_content:
        print("Error: No content provided for publishing.")
        return False

    # 1. Ensure the required Author Document exists
    if not ensure_author_document_exists():
        print("Publishing aborted: Could not create/verify AI author document.")
        return False

    # 2. Prepare the Sanity Document Structure (using the verified author ID)
    document = get_post_document_template(
        title=generated_content['title'],
        slug=generated_content['slug'],
        body_portable_text=generated_content['portable_text_body'],
        author_id=AI_AUTHOR_ID # Use the constant AI_AUTHOR_ID
    )
    
    # The mutation structure for Sanity API (creates a new document)
    mutation = {
        "mutations": [
            {
                # Use 'create' here since we know the post document is new
                "create": document
            }
        ]
    }
    
    # 3. Send the Post Mutation to Sanity
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SANITY_WRITE_TOKEN}"
    }

    # Retry logic for publishing the main post
    max_retries = 3
    for attempt in range(max_retries):
        try:
            sanity_response = requests.post(SANITY_API_URL, headers=headers, data=json.dumps(mutation))
            sanity_response.raise_for_status()
            
            # --- FIX: Robust ID Extraction ---
            result_data = sanity_response.json()['results'][0]
            # Safely try to get the ID from the created document object (the most reliable path)
            document_id = result_data.get('document', {}).get('_id', result_data.get('id', 'UNKNOWN_ID'))
            
            print(f"-> Successfully created document: {generated_content['title']} (ID: {document_id})")
            
            # If successful, break retry loop and proceed to deployment
            break
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"Sanity publishing attempt {attempt + 1} failed: {e}. Retrying in 2s...")
                time.sleep(2)
            else:
                print(f"Final error publishing to Sanity.io: {e}")
                print(f"Sanity API Response Text: {sanity_response.text if 'sanity_response' in locals() else 'N/A'}")
                return False
        
    # 4. Trigger Frontend Deployment (Vercel/Netlify/etc.)
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
