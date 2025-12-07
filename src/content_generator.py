import json
import requests
import time
import re
from config.sanity_config import GEMINI_API_KEY

# Base API for Gemini
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"


# -----------------------------------------------------------
# Portable Text Conversion (Markdown-Free + Table Support)
# -----------------------------------------------------------
def markdown_to_portable_text(markdown_text):
    """
    Converts Markdown-like text to Sanity Portable Text.
    Features:
    - Numbered headings (e.g., "1. Preliminary Triage") become H2
    - Removes all hashes (#) and M-dashes (—)
    - Converts simple tables (lines with '|') into structured table objects
    - Strips bold (**), italics (*), and extra spaces
    """
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

        # --- Heading Detection (Numbered) ---
        # Detects "1. Title", "2. Title", etc.
        if re.match(r"^\d+\.\s+", text_content):
            style = "h2"
            # Remove the number prefix (optional, keep if you want numbers in H2)
            # text_content = re.sub(r"^\d+\.\s+", "", text_content)

        # --- Heading Detection (Legacy/Safety) ---
        # Just in case Gemini slips up and uses #
        elif text_content.startswith("## "):
            style = "h2"
            text_content = text_content[3:].strip()
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


# -----------------------------------------------------------
# Blog Post Generation via Gemini
# -----------------------------------------------------------
def generate_blog_post(topic, context):
    """
    Generates a structured, SEO-optimized blog post.
    Returns:
    - title
    - slug
    - seo_title
    - meta_description
    - keywords
    - excerpt
    - reading_time_minutes
    - portable_text_body
    """

    print("--- 2. Generating SEO-optimized content via Gemini ---")

    # -----------------------------------------------------------
    # SYSTEM INSTRUCTION (SEO + Markdown-Free + Table Handling)
    # -----------------------------------------------------------
    system_instruction = (
        "You are an expert SEO content strategist and senior blog writer. "
        "You write long-form, human-sounding, fully SEO-optimized articles.\n\n"
        "SEO RULES YOU MUST FOLLOW:\n"
        "1. Create an SEO title separate from the H1.\n"
        "2. Add a meta description (155–170 characters).\n"
        "3. Add a clear H1 title.\n"
        "4. Use 3–5 rich H2 sections.\n"
        "5. Add a list of 5–12 SEO keywords.\n"
        "6. Provide a 40–60 word excerpt.\n"
        "7. Include an internal link to another GlideX blog (https://www.glidexoutsourcing.com/blog/real-estate-virtual-assistants-coordinating-showings or any other article available in the blog.) (fake link not OK).\n"
        "8. Include 1–2 authoritative outbound links (.gov, .edu, or credible sources).\n"
        "9. Avoid M-dashes (—), bold (**), italics (*), and hashes (#).\n"
        "10. Number all headings using '1.', '2.', '3.' format instead of hashes.\n"
        "11. If a table is needed, use standard pipe syntax (| Col 1 | Col 2 |).\n"
        "12. Content must sound human, helpful, authoritative, and non-repetitive.\n"
    )

    # -----------------------------------------------------------
    # USER QUERY
    # -----------------------------------------------------------
    user_query = (
        f"Generate a fully SEO-optimized long-form blog post about: '{topic}'. "
        "Use the following subtopics as H2 sections: "
        f"{', '.join(context)}.\n\n"
        "Return JSON with the following fields:\n"
        "- title (H1)\n"
        "- slug (URL-friendly)\n"
        "- seo_title\n"
        "- meta_description\n"
        "- keywords (list)\n"
        "- excerpt (40–60 words)\n"
        "- reading_time_minutes\n"
        "- body_markdown (full article, avoid # for headings, use 1. 2. 3.)\n\n"
        "Ensure the structure is clean, readable, unique, and SEO optimized."
    )

    # -----------------------------------------------------------
    # JSON SCHEMA
    # -----------------------------------------------------------
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "slug": {"type": "STRING"},
            "seo_title": {"type": "STRING"},
            "meta_description": {"type": "STRING"},
            "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
            "excerpt": {"type": "STRING"},
            "reading_time_minutes": {"type": "INTEGER"},
            "body_markdown": {"type": "STRING"}
        },
        "required": [
            "title",
            "slug",
            "seo_title",
            "meta_description",
            "keywords",
            "excerpt",
            "reading_time_minutes",
            "body_markdown"
        ]
    }

    # -----------------------------------------------------------
    # API PAYLOAD
    # -----------------------------------------------------------
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema
        }
    }

    headers = {"Content-Type": "application/json"}

    # -----------------------------------------------------------
    # RETRY LOGIC
    # -----------------------------------------------------------
    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{API_URL}?key={GEMINI_API_KEY}",
                headers=headers,
                json=payload
            )

            response.raise_for_status()

            result = response.json()
            if "candidates" not in result or not result["candidates"]:
                raise ValueError("No candidates returned from Gemini.")

            json_text = result["candidates"][0]["content"]["parts"][0]["text"]
            generated_data = json.loads(json_text)

            # ---------------------------------------------------
            # CLEANUP — ENFORCE URL SLUG FORMAT
            # ---------------------------------------------------
            generated_data["slug"] = (
                generated_data["slug"]
                .strip()
                .lower()
                .replace(" ", "-")
                .replace("--", "-")
            )

            # ---------------------------------------------------
            # CONVERT MARKDOWN TO PORTABLE TEXT (Sanity)
            # ---------------------------------------------------
            generated_data["portable_text_body"] = markdown_to_portable_text(
                generated_data["body_markdown"]
            )

            del generated_data["body_markdown"]

            print(f"-> Content generated successfully: {generated_data['title']}")
            return generated_data

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if "response" in locals():
                print("DEBUG RAW RESPONSE:", response.text[:500])
            time.sleep(2 ** attempt)

    print("❌ Failed: Could not generate content after retries.")
    return None
