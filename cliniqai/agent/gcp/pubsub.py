import os
import json
from google.cloud import pubsub_v1
from google.api_core.exceptions import GoogleAPIError

from agent.gcp.logger import get_logger

logger = get_logger(__name__)

def publish_alert(alert_type: str, message: str, patient_id: str = None):
    """
    Publishes an alert to Google Cloud Pub/Sub for real-time notifications.
    Falls back to a simple log print if not configured.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    topic_id = os.getenv("PUBSUB_ALERT_TOPIC", "cliniqai-alerts")
    
    payload = {
        "alert_type": alert_type,
        "message": message,
        "patient_id": patient_id
    }
    
    if not project_id or project_id == "your_project_id_here":
        logger.info(f"ℹ️ [Mock Pub/Sub] Alert Published: {alert_type} - {message}")
        return
        
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    
    data = json.dumps(payload).encode("utf-8")
    
    try:
        # Publish the message
        future = publisher.publish(topic_path, data)
        message_id = future.result()
        logger.info(f"✅ Alert published to Pub/Sub (Message ID: {message_id})")
    except GoogleAPIError as e:
        logger.error(f"⚠️ Failed to publish to Pub/Sub: {e}")
    except Exception as e:
        logger.error(f"⚠️ Unexpected error publishing to Pub/Sub: {e}")
