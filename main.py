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
        from config.settings import GEMINI_API_KEY
        from src.models import Article, validate_article  # Import new models
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

    # --- Content Generation (StrictMode) ---
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY missing — cannot generate content.")
        return

    raw_article_data = generate_blog_post(topic, context)
    if not raw_article_data:
        print("❌ Content generation failed (No data returned).")
        return

    # --- Validate Structure (Integrity Gate) ---
    try:
        print("🔍 Validating Article Structure...")
        # Populate Category manually since it's outside the generation scope
        # (Model doesn't have category currently, pass it separately or add to model)
        # We'll stick to model validation.
        
        article = Article(**raw_article_data)
        
        if not validate_article(article):
            print("❌ Article failed integrity check. Aborting.")
            return

    except Exception as e:
        print(f"❌ Validation Error: {e}")
        return

    print("✅ Article Structure Validated. Proceeding to Imagery.")

    # --- Parallel Image Generation ---
    if article.hero_image or any(section.image for section in article.sections):
        print("🖼️ Preparing image generation jobs...")
        
        # Import the parallel image generation functions
        from src.image_gen import prepare_jobs_from_article, generate_all_blog_images
        
        # Prepare all image jobs
        image_jobs = prepare_jobs_from_article(article)
        
        if image_jobs:
            # Generate all images in parallel
            print(f"🚀 Starting parallel generation for {len(image_jobs)} images...")
            image_results = generate_all_blog_images(
                image_jobs=image_jobs,
                max_workers=int(os.getenv("MAX_PARALLEL_IMAGES", "3")),
                output_dir="generated_images"
            )
            
            # Update article with generated image paths
            if article.hero_image and 'hero' in image_results:
                hero_path = image_results['hero']
                if hero_path:
                    article.hero_image.asset_id = hero_path # Storing path temporarily
                else:
                    print("⚠️ Hero image generation failed.")
            
            # Update section images
            for i, section in enumerate(article.sections):
                job_id = f'section_{i}'
                if section.image and job_id in image_results:
                    sec_path = image_results[job_id]
                    if sec_path:
                        section.image.asset_id = sec_path # Storing path temporarily
                    else:
                        print(f"      ⚠️ Failed to generate image for section {i}")
        else:
            print("ℹ️ No image generation jobs found.")

    # --- Publish (Strict Only) ---
    try:
        # We pass the full article object now. 
        # Publisher needs to be refactored to accept this object.
        success = publish_to_sanity(article, category=category)
    except TypeError as e:
        print(f"❌ Publisher error (Signature Mismatch?): {e}") 
        # Fallback for legacy publisher (will break with new object, so likely needs update first)
        return

    if success:
        print("==============================================")
        print(f"== 🎉 Cycle Complete! Blog '{article.title}' published ==")
        print("==============================================")
    else:
        print("==============================================")
        print("== ❌ Cycle Failed during Publishing ==")
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

