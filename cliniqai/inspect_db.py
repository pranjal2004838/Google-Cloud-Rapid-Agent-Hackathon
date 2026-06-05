import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGODB_URI")
print("Connecting to:", uri)
client = MongoClient(uri)
db = client["cliniqai"]
col = db["patients"]

print("\n--- Patients in DB ---")
for p in col.find():
    print(f"Name: {p.get('name')}, Phone: {p.get('phone')}, Visits count: {len(p.get('visits', []))}")
    for i, v in enumerate(p.get('visits', [])):
        print(f"  Visit {i+1}: Doctor: {v.get('doctor')}, Clinic: {v.get('clinic')}, Source Doc: {v.get('source_document')}")
