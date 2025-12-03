import logging
from functions_framework import http
from main import run_autoblog_workflow

# Set up logging for Cloud Functions
logging.basicConfig(level=logging.INFO)

@http
def autoblog_handler(request):
    """
    HTTP Cloud Function entry point for the Autoblog cron job.
    This function is triggered by Cloud Scheduler via HTTP.
    """
    logging.info("Starting scheduled Autoblog workflow execution.")
    
    try:
        # Optional: parse JSON payload for manual topic/context
        topic = None
        context = None
        if request.is_json:
            data = request.get_json()
            topic = data.get("topic")
            context = data.get("context")
            logging.info(f"Received manual topic: {topic}, context: {context}")

        # Run the main workflow
        run_autoblog_workflow(manual_topic=topic, manual_context=context)

        logging.info("Autoblog workflow completed successfully.")
        return ("Autoblog cycle completed successfully and deployment triggered.", 200)

    except Exception as e:
        logging.error(f"FATAL ERROR during Autoblog execution: {e}", exc_info=True)
        return (f"Autoblog failed with fatal error: {e}", 500)
