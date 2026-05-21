import google.generativeai as genai
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
    
    # Check if API key is configured
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or "your_google" in api_key:
        return {"error": "GOOGLE_API_KEY not configured. Set it in .env file."}
    
    # Configure Gemini with your API key
    genai.configure(api_key=api_key)
    
    # We use 'gemini-2.0-flash' because it's fast and good at vision
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Convert raw bytes from the web upload into an image object
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        return {"error": f"Could not read image file: {str(e)}. Please upload a valid JPG or PNG."}
    
    prompt = """
    You are a medical data extraction assistant for Indian clinics. 
    Look at this prescription or medical document carefully.
    It might be handwritten in English or Hindi.
    
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
            "patient_name": 0.0 to 1.0,
            "patient_age": 0.0 to 1.0,
            "patient_gender": 0.0 to 1.0,
            "visit_date": 0.0 to 1.0,
            "doctor_name": 0.0 to 1.0,
            "clinic_name": 0.0 to 1.0,
            "diagnosis": 0.0 to 1.0,
            "medicines": [0.0 to 1.0 for each medicine],
            "tests_ordered": 0.0 to 1.0,
            "allergies_mentioned": 0.0 to 1.0,
            "notes": 0.0 to 1.0
        }
    }
    
    Important:
    1. If the document is in Hindi, translate the content to English.
    2. Return ONLY the JSON. No preamble, no explanation.
    3. Be very precise with medicine names.
    """
    
    # Generate the response
    try:
        response = model.generate_content([prompt, image])
    except Exception as e:
        return {"error": f"Gemini API call failed: {str(e)}"}
    
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
