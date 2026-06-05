from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["cliniqai"]
patients_collection = db["patients"]

patients = list(patients_collection.find())
count = 0
for p in patients:
    updated = False
    visits = p.get("visits", [])
    for v in visits:
        if "hosp_id" not in v:
            v["hosp_id"] = "HSP_MUMBAI_001"
            updated = True
    if updated:
        patients_collection.update_one({"_id": p["_id"]}, {"$set": {"visits": visits}})
        count += 1

print(f"Patched {count} patients with hosp_id = HSP_MUMBAI_001")
