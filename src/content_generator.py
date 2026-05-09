"""
src/content_generator.py - Enhanced content generation with improved image support.
Uses centralized config and modern async patterns.
"""

import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any
import requests

from config.settings import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_API_URL

# Default model - can be changed to gpt-4o-mini or gpt-3.5-turbo for cost savings
OPENAI_TEMPERATURE = 0.7
OPENAI_MAX_TOKENS = 4000

# ---------------------------------------------------------------------------
# Portable Text Conversion (Enhanced with Image Block Support)
# ---------------------------------------------------------------------------
def insert_image_block(alt_text: str, asset_id: str = None) -> Dict[str, Any]:
    """
    Create a Portable Text image block.
    
    Args:
        alt_text: Alt text for accessibility
        asset_id: Optional Sanity asset ID reference
    """
    block = {
        "_type": "image",
        "alt": alt_text,
        "_key": str(hash(f"{alt_text}_{time.time()}"))
    }
    
    if asset_id:
        block["asset"] = {
            "_type": "reference",
            "_ref": asset_id
        }
    
    return block


def markdown_to_portable_text(markdown_text, images_map: Dict[str, str] = None):
    """
    Converts Markdown-like text to Sanity Portable Text.
    
    Features:
    - Numbered headings (e.g., "1. Preliminary Triage") become H2
    - Removes all hashes (#) and M-dashes (—)
    - Converts simple tables (lines with '|') into structured table objects
    - Strips bold (**), italics (*), and extra spaces
    - Supports inline image injection via images_map
    
    Args:
        markdown_text: Raw markdown content
        images_map: Optional dict mapping heading text -> Sanity asset ID to insert images
    """
    images_map = images_map or {}
    blocks = []
    lines = markdown_text.split("\n")
    table_rows = []

    def flush_table():
        """Helper to push collected table rows into blocks."""
        if table_rows:
            table_block = {
                "_type": "table",
                "rows": list(table_rows), # Create a copy
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
            # Clean the row and split by pipe
            # Example: "| Col 1 | Col 2 |" -> ["Col 1", "Col 2"]
            row_cells = [c.strip() for c in line.strip("|").split("|")]
            table_rows.append(row_cells)
            continue
        
        # If we hit a non-table line but have table data, flush the table first
        flush_table()

        # --- Text Cleaning ---
        # Replace M-dashes with hyphens, remove bold/italic markers
        text_content = line.replace("—", "-").replace("**", "").replace("*", "")
        # Remove multiple spaces
        text_content = " ".join(text_content.split())

        style = "normal"
        heading_text = None

        # --- Heading Detection (Numbered) ---
        # Detects "1. Title", "2. Title", etc.
        if re.match(r"^\d+\.\s+", text_content):
            style = "h2"
            heading_text = re.sub(r"^\d+\.\s+", "", text_content)
            
            # --- Injected Image Check ---
            if heading_text and heading_text in images_map:
                # Insert image block before the heading
                blocks.append(insert_image_block(
                    f"Illustration for {heading_text}",
                    images_map[heading_text]
                ))

        # --- Heading Detection (Legacy/Safety) ---
        # Just in case the model slips up and uses #
        elif text_content.startswith("## "):
            style = "h2"
            heading_text = text_content[3:].strip()
            
            # --- Injected Image Check ---
            if heading_text and heading_text in images_map:
                blocks.append(insert_image_block(
                    f"Illustration for {heading_text}",
                    images_map[heading_text]
                ))
                
        elif text_content.startswith("# "):
            style = "h1" # Though usually H1 is reserved for title
            text_content = text_content[2:].strip()

        # --- Block Construction ---
        block = {
            "_type": "block",
            "style": style,
            "children": [
                {
                    "_key": str(hash(text_content + style + str(time.time()))),
                    "_type": "span",
                    "text": text_content,
                    "marks": []
                }
            ]
        }
        blocks.append(block)

    # Flush any remaining table at the end of the content
    flush_table()

    return blocks


# ---------------------------------------------------------------------------
# Blog Post Generation via OpenAI
# ---------------------------------------------------------------------------
def generate_blog_post(topic, context):
    """
    Generates a structured, SEO-optimized blog post using the Article Schema.
    Uses OpenAI GPT-4o with JSON mode.
    Returns:
    - Article object (dict) matching the src.models.Article definition.
    """

    print(f"--- 2. Generating structured content via OpenAI ({OPENAI_MODEL}) ---")

    # -----------------------------------------------------------
    # SYSTEM INSTRUCTION (Strict Schema)
    # -----------------------------------------------------------
    system_instruction = """You are an expert SEO content strategist. You do not just write text; you architect high-quality blog posts.

YOUR GOAL: Create a structured JSON object representing a full blog post.

STRUCTURE RULES:
1. 'hero_image': You MUST define a hero image with a descriptive 'prompt' field for image generation.
2. 'sections': You MUST generate at least 4 detailed sections.
3. 'image' in sections: For at least 2 of the sections, you MUST provide an 'image' object with a descriptive prompt.
4. 'body': The body of each section should be rich Markdown (headings, lists, bolding allowed).
5. Content: Professional, authoritative, human-sounding.

OUTPUT FORMAT: Valid JSON only, no markdown code blocks."""

    # -----------------------------------------------------------
    # USER QUERY with JSON Schema
    # -----------------------------------------------------------
    user_query = f"""Generate a blog post about: '{topic}'.
Context/Subtopics: {', '.join(context)}.

Output MUST be valid JSON adhering to this exact schema:
{{
  "title": "The main blog post title",
  "slug": "url-friendly-slug",
  "seo_title": "SEO optimized title (max 60 chars)",
  "meta_description": "Meta description for search engines (max 160 chars)",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "excerpt": "A compelling 2-3 sentence excerpt",
  "reading_time_minutes": 5,
  "hero_image": {{
    "role": "hero",
    "prompt": "Detailed image generation prompt for the hero image",
    "alt_text": "Alt text for accessibility"
  }},
  "sections": [
    {{
      "heading": "Section Heading",
      "body": "Markdown content for this section...",
      "image": {{
        "role": "section",
        "prompt": "Detailed image generation prompt for this section",
        "heading_ref": "Section Heading",
        "alt_text": "Alt text for this image"
      }}
    }}
  ]
}}

IMPORTANT: 
- Generate at least 4 sections
- At least 2 sections must have images
- All prompts should be detailed enough for AI image generation
- Output ONLY valid JSON, no explanations"""

    # -----------------------------------------------------------
    # API PAYLOAD (OpenAI format)
    # -----------------------------------------------------------
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_query}
        ],
        "response_format": {"type": "json_object"},
        "temperature": OPENAI_TEMPERATURE,
        "max_tokens": OPENAI_MAX_TOKENS
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    # -----------------------------------------------------------
    # RETRY LOGIC
    # -----------------------------------------------------------
    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = requests.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload,
                timeout=120  # 2 minute timeout for long content
            )

            response.raise_for_status()

            result = response.json()
            
            if "choices" not in result or not result["choices"]:
                raise ValueError("No choices returned from OpenAI.")

            json_text = result["choices"][0]["message"]["content"]
            generated_data = json.loads(json_text)

            # ---------------------------------------------------
            # CLEANUP & VALIDATION PREP
            # ---------------------------------------------------
            generated_data["slug"] = (
                generated_data["slug"]
                .strip()
                .lower()
                .replace(" ", "-")
                .replace("--", "-")
            )
            
            # Note: We rely on models.validate_article to check deep logic later.
            print(f"-> Content generated successfully: {generated_data['title']}")
            return generated_data

        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = response.json().get("error", {}).get("message", "")
            except:
                error_detail = response.text[:500]
            print(f"Attempt {attempt + 1} failed (HTTP {response.status_code}): {error_detail}")
            time.sleep(2 ** attempt)
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if "response" in locals():
                print("DEBUG RAW RESPONSE:", response.text[:500])
            time.sleep(2 ** attempt)

    print("❌ Failed: Could not generate content after retries.")
    return None