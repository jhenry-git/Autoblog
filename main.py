import sys
import argparse

def run_autoblog_workflow(manual_topic=None, manual_context=None):
    """
    The main workflow for the Autonomous AI Blog.
    1. Scrape a trending topic OR use a manual one.
    2. Generate content using an LLM.
    3. Publish the content to Sanity.io and trigger a deploy.
    """
    # Move imports inside the function to avoid Cloud Run startup issues
    from src.data_scraper import get_trending_topic
    from src.content_generator import generate_blog_post
    from src.publisher import publish_to_sanity
    from config.sanity_config import GEMINI_API_KEY

    print("==============================================")
    print("== Starting Autonomous AI Blog Generation Cycle ==")
    print("==============================================")

    # 1. Data Sourcing (Manual Override vs. Scraper)
    if manual_topic:
        topic = manual_topic
        context = manual_context if manual_context else [
            f"benefits of {manual_topic}",
            "implementation challenges",
            "future impact"
        ]
        print(f"--- 1. Using Manual Topic: {topic} ---")
    else:
        topic, context = get_trending_topic()

    if not topic:
        print("Cycle aborted: Could not find a suitable trending topic.")
        return

    # 2. Content Generation
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is missing. Cannot generate content.")
        return

    generated_content = generate_blog_post(topic, context)

    if not generated_content:
        print("Cycle aborted: Content generation failed.")
        return

    # 3. Publishing
    success = publish_to_sanity(generated_content)

    if success:
        print("==============================================")
        print("== Cycle Complete! New blog post is publishing. ==")
        print("==============================================")
    else:
        print("==============================================")
        print("== Cycle Failed: Check logs for errors. ==")
        print("==============================================")


# ========================================================
# CLI mode for local testing (does NOT run in GCF)
# ========================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous AI Blog Content Generator.")
    parser.add_argument(
        '--topic',
        type=str,
        help="Manually override the scraper with a specific blog topic."
    )
    parser.add_argument(
        '--context',
        type=str,
        nargs='*',
        help="Optional sub-points or context for the manual topic (comma-separated if using quotes)."
    )
    args = parser.parse_args()

    # Ensure all required modules are accessible via the Python path
    sys.path.append('src')
    sys.path.append('config')

    # Run the workflow with or without manual arguments
    run_autoblog_workflow(manual_topic=args.topic, manual_context=args.context)
