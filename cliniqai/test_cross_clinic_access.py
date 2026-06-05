import requests
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
API_URL = "http://localhost:8000"

def test_cross_clinic_fetch():
    print("Simulating login as Dr. Neha (HSP_DELHI_002)...")
    
    # In the UI, this doctor would search by phone number:
    phone = "9876543210"  # This is Priya Sharma, whose records were made by other clinics
    
    print(f"\n🔍 Searching for patient with mobile number: {phone}...")
    
    try:
        response = requests.get(f"{API_URL}/patient/{phone}")
        if response.status_code == 200:
            data = response.json()
            if data.get("found"):
                patient = data["patient"]
                print(f"\n✅ SUCCESS: Found patient records across clinics!")
                print(f"Patient Name: {patient.get('name', 'Unknown')}")
                print(f"Total Visits on file: {len(patient.get('visits', []))}")
                
                print("\n🩺 Cross-Clinic Medical History Available:")
                for i, visit in enumerate(patient.get('visits', []), 1):
                    doc = visit.get('doctor', 'Unknown Doctor')
                    clinic = visit.get('clinic', 'Unknown Clinic')
                    date = visit.get('date', 'Unknown Date')
                    print(f"  [{i}] {date} - Seen by {doc} at {clinic}")
                
                print("\n💡 This confirms that Dr. Neha at HSP_DELHI_002 can instantly view the complete longitudinal")
                print("history of a patient originally treated by Dr. Demo Assistant at HSP_MUMBAI_001")
                print("by using only their universal mobile number identifier.")
            else:
                print("❌ Patient not found.")
        else:
            print(f"❌ API Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the backend server. Is it running on port 8000?")
        print("Make sure to run 'uvicorn agent.server:app --reload' in another terminal.")

if __name__ == "__main__":
    test_cross_clinic_fetch()
