import json
import requests
import time
from config.sanity_config import GEMINI_API_KEY # Using GEMINI_API_KEY instead of OPENAI_API_KEY

# Base API for Gemini
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"
API_KEY = "" # The main script will handle the API key if the env variable is empty


# --- Portable Text Helper Function ---
def markdown_to_portable_text(markdown_text):
    """
    Converts a simple Markdown string (with paragraphs and headings) 
    into a list of basic Sanity Portable Text block objects.
    This simplifies the model's output requirement, reducing 400 errors.
    """
    blocks = []
    lines = markdown_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        style = 'normal'
        text_content = line
        
        # --- NEW: Content Cleanup ---
        # 1. Remove M-dashes (—)
        text_content = text_content.replace('—', '-')
        # 2. Remove extra asterisks (often used for bolding or lists, which break our simple converter)
        text_content = text_content.replace('**', '')
        text_content = text_content.replace('*', '')

        # Simple heading detection
        if text_content.startswith('## '):
            style = 'h2'
            text_content = text_content[3:].strip()
        elif text_content.startswith('# '):
            style = 'h1'
            text_content = text_content[2:].strip()
        
        # Create a single Portable Text block
        block = {
            "_type": "block",
            "style": style,
            "children": [
                {
                    "_key": str(hash(text_content + style)), # Simple unique key
                    "_type": "span",
                    "text": text_content,
                    "marks": []
                }
            ]
        }
        blocks.append(block)
        
    return blocks


def generate_blog_post(topic, context):
    """
    Generates a blog post draft using an LLM.
    
    Args:
        topic (str): The main keyword/topic from Google Trends.
        context (list): Supporting keywords/subtopics.
        
    Returns:
        dict: Structured content with 'title', 'slug', and 'portable_text_body' (list).
    """
    print("--- 2. Generating content via AI ---")
    
    # 1. Define the System Instruction (Persona & Rules)
    system_instruction = (
        "You are an expert content writer for a popular tech/news blog. "
        "Your task is to write a highly engaging and comprehensive blog post "
        "based on the given trending topic. The output MUST be a single JSON object "
        "that strictly adheres to the provided schema. The 'body_markdown' field "
        "must contain the full article formatted using simple Markdown headings (##) "
        "and paragraphs. "
        "CRITICAL: Avoid using M-dashes (—) and any Markdown artifacts like ** or * in the output. "
        "Write with a clear, authoritative, and friendly tone."
    )

    # 2. Define the User Query (The Task)
    user_query = (
        f"Write a full blog post on the trending topic: '{topic}'. "
        "The post must include a catchy H1 title. Organize the content using three main "
        f"H2 sub-sections based on these sub-topics: {', '.join(context)}. "
        "The post should be ready for publication."
    )
    
    # 3. Define the Simplified Structured Output Schema
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "The engaging title of the blog post."},
            "slug": {"type": "STRING", "description": "A URL-friendly version of the title (lowercase, hyphenated)."},
            "body_markdown": {"type": "STRING", "description": "The full article content formatted in simple Markdown (paragraphs, ## headings)."}
        },
        "required": ["title", "slug", "body_markdown"]
    }

    # 4. Construct the API Payload
    payload = {
        "contents": [{ "parts": [{ "text": user_query }] }],
        "systemInstruction": { "parts": [{ "text": system_instruction }] },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    
    # Simple retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(f"{API_URL}?key={GEMINI_API_KEY}", headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            json_text = result['candidates'][0]['content']['parts'][0]['text']
            generated_data = json.loads(json_text)
            
            # --- Conversion Step ---
            if 'body_markdown' in generated_data:
                generated_data['portable_text_body'] = markdown_to_portable_text(generated_data['body_markdown'])
                del generated_data['body_markdown']
            
            # Final Validation
            if all(k in generated_data for k in ['title', 'slug', 'portable_text_body']):
                print(f"-> Content generated and cleaned successfully: {generated_data['title']}")
                return generated_data
            else:
                raise ValueError("Generated JSON is missing required fields after conversion.")

        except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                print("Failed to generate content after maximum retries.")
                return None
    return None
