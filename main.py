import sys
import argparse
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def run_autoblog_workflow(manual_topic=None, manual_context=None):
    """
    The main workflow for the Autonomous AI Blog.
    Features:
    - Checks for Manual Topic Override.
    - If Auto, picks a specific Niche.
    - Tries to find Trending News.
    - FALLBACK: If no news, picks a specific sub-skill to write a detailed educational post.
    - NEW: Generates a featured image using Gemini Nano Banana (Flash).
    """
    
    # --- 1. CONFIGURATION: Detailed Niche Breakdown ---
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

    # Move imports inside to avoid Cloud Run startup issues
    try:
        from src.data_scraper import get_trending_topic
        from src.content_generator import generate_blog_post
        from src.image_gen import generate_blog_image  # <--- NEW IMPORT
        from src.publisher import publish_to_sanity
        from config.sanity_config import GEMINI_API_KEY
    except ImportError as e:
        logger.error(f"Import Error: {e}")
        print("CRITICAL: Could not import modules. Check sys.path or structure.")
        return

    print("==============================================")
    print("== Starting Autonomous AI Blog Generation Cycle ==")
    print("==============================================")

    # --- 2. Topic Selection Strategy ---
    
    # A. Manual Override
    if manual_topic:
        topic = manual_topic
        context = manual_context if manual_context else [
            f"Key benefits of {manual_topic}",
            "Implementation guide",
            "Future outlook"
        ]
        print(f"--- [Mode: MANUAL] Using Topic: {topic} ---")
        
    # B. Autonomous Selection
    else:
        # 1. Pick a Broad Niche
        selected_niche_name = random.choice(list(NICHE_DETAILS.keys()))
        print(f"--- [Mode: AUTO] Targeting Niche: {selected_niche_name} ---")

        try:
            # 2. Try to find trending news
            topic, context = get_trending_topic(query=selected_niche_name)
        except TypeError:
            print("Warning: Scraper does not accept queries yet. Searching general trends...")
            topic, context = get_trending_topic()
        except Exception as e:
            print(f"Scraper encountered an error: {e}")
            topic = None

        # --- C. THE FALLBACK PROTOCOL ---
        if not topic:
            print(f"(!) No trending news found for '{selected_niche_name}'. Engaging FALLBACK.")
            
            specific_sub_topic = random.choice(NICHE_DETAILS[selected_niche_name])
            topic = f"How {selected_niche_name} Streamline {specific_sub_topic}"
            context = [
                f"The challenges of {specific_sub_topic} without help",
                f"Step-by-step: How a VA handles {specific_sub_topic}",
                "Software and tools typically used",
                "Cost comparison: In-house vs. Outsourced VA",
                f"Why GlideX Outsourcing is the best choice for {specific_sub_topic}"
            ]
            print(f"--- [Mode: FALLBACK] Generating Specific Content: {specific_sub_topic} ---")

    # --- 3. Content Generation ---
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is missing. Cannot generate content.")
        return

    generated_content = generate_blog_post(topic, context)

    if not generated_content:
        print("Cycle aborted: Content generation failed.")
        return

    # --- 3.5 NEW: Image Generation ---
    print(f"🖼️ Generating featured image for: '{topic}'...")
    image_path = generate_blog_image(topic)

    if image_path:
        print(f"✅ Image Ready: {image_path}")
    else:
        print("⚠️ Image generation skipped or failed (check logs).")

    # --- 4. Publishing ---
    # NOTE: We are now passing 'image_path' to the publisher.
    # Ensure your src/publisher.py is updated to accept this second argument!
    try:
        success = publish_to_sanity(generated_content, image_path)
    except TypeError:
        # Fallback if publisher isn't updated yet
        print("⚠️ Warning: Publisher script not updated for images. Publishing text only...")
        success = publish_to_sanity(generated_content)

    if success:
        print("==============================================")
        print(f"== Cycle Complete! Blog post '{topic}' is publishing. ==")
        print("==============================================")
    else:
        print("==============================================")
        print("== Cycle Failed: Check logs for errors. ==")
        print("==============================================")

# ========================================================
# CLI mode for local testing
# ========================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=str, help="Manual topic override")
    parser.add_argument('--context', type=str, nargs='*', help="Manual context points")
    args = parser.parse_args()

    sys.path.append('src')
    sys.path.append('config')

    run_autoblog_workflow(manual_topic=args.topic, manual_context=args.context)
