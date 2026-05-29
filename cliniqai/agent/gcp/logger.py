import os
import logging
from google.cloud import logging as cloud_logging

# Configure local logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def setup_cloud_logging():
    """
    Initializes Google Cloud Logging.
    If GCP is not configured or fails, it falls back to standard Python logging gracefully.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    if project_id and project_id != "your_project_id_here":
        try:
            client = cloud_logging.Client(project=project_id)
            # Attaches Google Cloud Logging handlers to Python's root logger
            client.setup_logging()
            logging.info(f"✅ Google Cloud Logging initialized for project {project_id}")
        except Exception as e:
            logging.warning(f"⚠️ Failed to initialize Google Cloud Logging: {e}. Falling back to standard logging.")
    else:
        logging.info("ℹ️ GOOGLE_CLOUD_PROJECT not set. Using local standard logging.")

# Initialize immediately when this module is imported
setup_cloud_logging()

# Provide a logger instance that other files can import
def get_logger(name):
    return logging.getLogger(name)
