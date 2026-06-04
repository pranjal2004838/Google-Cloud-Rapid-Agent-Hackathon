from google import genai
from google.genai import types
import json
import os
from PIL import Image
import io
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

def extract_from_prescription(image_bytes: bytes) -> dict:
    """
    Takes a photo of a prescription or lab report.
    Returns structured patient data as a Python dictionary.
    """
    
    api_key = os.getenv("GOOGLE_API_KEY")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    if api_key and "your_google" not in api_key:
        # Use Google AI Studio Gemini API (API key credentials)
        client = genai.Client(api_key=api_key)
    elif project_id and "your_project" not in project_id:
        # Use Gemini on Vertex AI to match the Google Cloud-native architecture.
        client = genai.Client(vertexai=True, project=project_id, location=location)
    else:
        return {"error": "Neither GOOGLE_API_KEY nor GOOGLE_CLOUD_PROJECT configured in .env file."}
    
    # Convert raw bytes from the web upload into an image object
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        return {"error": f"Could not read image file: {str(e)}. Please upload a valid JPG or PNG."}
    
    prompt = """
    You are a medical data extraction assistant for Indian clinics. 
    Look at this prescription or medical document carefully.
    It might be handwritten in English or any of the 29 regional Indian languages (e.g., Hindi, Bengali, Telugu, Marathi, Tamil, Urdu, Gujarati, Kannada, Odia, Malayalam, Punjabi, Assamese, Maithili, etc.).
    
    Extract the following information and return ONLY a JSON object:
    {
        "patient_name": "full name or 'Unknown' if not visible",
        "patient_age": "age as number or null",
        "patient_gender": "Male/Female/Other or null",
        "visit_date": "date in YYYY-MM-DD format or today's date",
        "doctor_name": "doctor's name or null",
        "clinic_name": "clinic name or null",
        "diagnosis": ["list of conditions mentioned"],
        "medicines": [
            {
                "name": "medicine name",
                "dose": "dosage like 500mg",
                "frequency": "like twice daily",
                "duration": "like 5 days"
            }
        ],
        "tests_ordered": ["list of tests if any"],
        "allergies_mentioned": ["list of allergies if mentioned"],
        "notes": "any other important notes",
        "confidence": {
            "patient_name": 0.0,
            "patient_age": 0.0,
            "patient_gender": 0.0,
            "visit_date": 0.0,
            "doctor_name": 0.0,
            "clinic_name": 0.0,
            "diagnosis": 0.0,
            "medicines": [
                {
                    "name": 0.0,
                    "dose": 0.0,
                    "frequency": 0.0,
                    "duration": 0.0
                }
            ],
            "tests_ordered": 0.0,
            "allergies_mentioned": 0.0,
            "notes": 0.0
        }
    }
    
    Important:
    1. If the document is in a regional Indian language, translate all extracted content to English.
    2. Return ONLY the JSON. No preamble, no explanation.
    3. Be very precise with medicine names.
    4. Confidence scores must be numbers between 0.0 and 1.0.
    """
    
    # Generate the response
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")],
        )
    except Exception as e:
        return {"error": f"Gemini on Vertex AI call failed: {str(e)}"}
    
    # The response text might contain markdown blocks like ```json ... ```
    # We need to clean it to get just the JSON string
    text = response.text.strip()
    if text.startswith("```json"):
        text = text[7:-3].strip()
    elif text.startswith("```"):
        text = text[3:-3].strip()
        
    try:
        data = json.loads(text)
        return data
    except Exception as e:
        return {"error": f"Failed to parse JSON: {str(e)}", "raw_response": response.text}
