import os
import json
from google.cloud import tasks_v2
from google.api_core.exceptions import GoogleAPIError

from agent.gcp.logger import get_logger

logger = get_logger(__name__)

def create_task(payload: dict, endpoint: str = "/process_background"):
    """
    Enqueues a task in Google Cloud Tasks.
    Falls back to a warning/mock if Cloud Tasks is not configured (e.g. localhost).
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    queue_name = os.getenv("TASKS_QUEUE_NAME", "cliniqai-processing-queue")
    service_url = os.getenv("PUBLIC_SERVICE_URL") # E.g. https://cliniqai-xxx.a.run.app
    
    if not project_id or project_id == "your_project_id_here" or not service_url:
        logger.info("ℹ️ Cloud Tasks not configured (missing PUBLIC_SERVICE_URL or PROJECT). Using local async processing.")
        return False # Tells the caller to use FastAPI BackgroundTasks instead
        
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(project_id, location, queue_name)
    
    url = f"{service_url.rstrip('/')}{endpoint}"
    
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-type": "application/json"},
            "body": json.dumps(payload).encode(),
        }
    }
    
    try:
        response = client.create_task(request={"parent": parent, "task": task})
        logger.info(f"✅ Cloud Task created successfully: {response.name}")
        return True
    except GoogleAPIError as e:
        logger.error(f"⚠️ Failed to create Cloud Task: {e}")
        return False
