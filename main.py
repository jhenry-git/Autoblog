import sys
import argparse
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def run_autoblog_workflow(manual_topic=None, manual_context=None):
    """
    Main Autonomous Blog Workflow
    Enhanced for SEO metadata, portable text safety, and robust image handling.
    """

    # --- Niche Definitions ---
    NICHE_DETAILS = {
        "Medical Virtual Assistants": [
            "Appointment Scheduling & Calendar Management",
            "Medical Coding and Billing Support",
            "Patient Intake and Triage",
            "EMR/EHR Management for Private Practices",
            "Handling Insurance Verifications"
        ],
        "Voice Automation AI": [
            "Handling Inbound Customer Support 24/7",
            "Automating Appointment Reminders",
            "Lead Qualification via Voice AI",
            "Replacing Traditional Call Centers"
        ],
        "Real Estate Virtual Assistants": [
            "Cold Calling and Lead Generation",
            "Managing Property Listings",
            "CRM Data Entry and Maintenance",
            "Coordinating Showings for Realtors"
        ],
        "Executive Virtual Assistants": [
            "Inbox Zero and Email Management",
            "Travel Planning and Itinerary Management",
            "Meeting Minute Taking and Organization",
            "Personal Lifestyle Management for CEOs"
        ]
    }

    # Lazy imports
    try:
        from src.data_scraper import get_trending_topic
        from src.content_generator import generate_blog_post
        from src.image_gen import generate_blog_image
        from src.publisher import publish_to_sanity
        from src.seo_enhancer import slugify
        from config.sanity_config import GEMINI_API_KEY
    except ImportError as e:
        logger.error(f"Import Error: {e}")
        print("CRITICAL: Failed imports in main.py.")
        return

    print("==============================================")
    print("== Starting Autonomous AI Blog Generation 🏁 ==")
    print("==============================================")

    # --- Topic Selection ---
    if manual_topic:
        topic = manual_topic
        context = manual_context or [
            f"Key benefits of {manual_topic}",
            "Implementation guide",
            "Future outlook"
        ]
        category = "manual"
        print(f"--- [MANUAL MODE] Topic: {topic} ---")
    else:
        selected_niche_name = random.choice(list(NICHE_DETAILS.keys()))
        category = selected_niche_name.lower().replace(" ", "-")
        print(f"--- [AUTO MODE] Niche: {selected_niche_name} ---")
        try:
            topic, context = get_trending_topic(query=selected_niche_name)
        except Exception:
            topic = None

        if not topic:
            print(f"⚠️ No trending news found. Using fallback topic...")
            specific_point = random.choice(NICHE_DETAILS[selected_niche_name])
            topic = f"How {selected_niche_name} Streamline {specific_point}"
            context = [
                f"The challenges of {specific_point} without assistance",
                f"Step-by-step: How a VA handles {specific_point}",
                "Tools typically used",
                "Cost comparison: In-house vs outsourced",
                f"Why GlideX Outsourcing is the best solution for {specific_point}"
            ]

    # --- Content Generation ---
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY missing — cannot generate content.")
        return

    generated_content = generate_blog_post(topic, context)
    if not generated_content:
        print("❌ Content generation failed.")
        return

    # --- Assign Missing Fields for SEO ---
    generated_content["slug"] = generated_content.get("slug") or slugify(topic)
    generated_content["category"] = category
    generated_content["plain_text_body"] = (
        generated_content.get("body_text") or
        generated_content.get("text_only") or
        generated_content.get("raw_text") or
        generated_content.get("plain_text") or
        ""
    )

    # Safety fallback for portable text
    if "portable_text_body" not in generated_content:
        # Ensure it is always a list of blocks
        generated_content["portable_text_body"] = (
            generated_content.get("body_html") or
            [{"_type": "block", "style": "normal", "children":[{"_key":"fallback","_type":"span","text":generated_content["plain_text_body"],"marks":[]}]}]
        )

    print(f"SEO: plain_text_body length = {len(generated_content['plain_text_body'])}")

    # --- Image Generation ---
    print(f"🖼️ Generating featured image for '{topic}'...")
    image_path = generate_blog_image(topic)
    if image_path:
        print(f"✅ Image generated at: {image_path}")
    else:
        print("⚠️ No image generated.")

    # --- Publish ---
    try:
        success = publish_to_sanity(generated_content, image_path)
    except TypeError:
        print("⚠️ Publisher not updated to handle images — sending text only.")
        success = publish_to_sanity(generated_content)

    if success:
        print("==============================================")
        print(f"== 🎉 Cycle Complete! Blog '{topic}' published ==")
        print("==============================================")
    else:
        print("==============================================")
        print("== ❌ Cycle Failed: Check logs ==")
        print("==============================================")

# --- CLI Entrypoint ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str)
    parser.add_argument("--context", type=str, nargs="*")
    args = parser.parse_args()

    sys.path.append("src")
    sys.path.append("config")

    run_autoblog_workflow(args.topic, args.context)
