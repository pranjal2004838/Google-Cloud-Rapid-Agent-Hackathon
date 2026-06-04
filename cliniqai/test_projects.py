import sys
from google import genai

projects = ["potent-catwalk-323501", "soy-reporter-469303-d6", "tough-messenger-474203-a8"]
for proj in projects:
    print(f"Testing project: {proj}")
    try:
        client = genai.Client(vertexai=True, project=proj, location='us-central1')
        r = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Respond with EXACTLY the word SUCCESS'
        )
        print(f"-> SUCCESS for {proj}! Response: {r.text.strip()}")
    except Exception as e:
        print(f"-> FAILED for {proj}: {e}")
    print("-" * 50)
