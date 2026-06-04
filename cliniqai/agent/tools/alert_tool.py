"""
Drug Conflict Checker for CliniqAI

Checks three layers:
1. Direct allergy — new medicine belongs to a known allergenic drug family
2. Cross-allergy — related family with known cross-reactivity
3. Drug-drug interaction — dangerous combinations
"""

# ─── Drug Family Definitions ───────────────────────────────────────────────────
# Each family maps to a list of medicines that belong to it.
# Focused on drugs commonly prescribed in Indian primary care.

ALLERGY_FAMILIES = {
    "penicillin": [
        "amoxicillin", "ampicillin", "augmentin", "amoxyclav",
        "cloxacillin", "flucloxacillin", "piperacillin", "co-amoxiclav"
    ],
    "cephalosporin": [
        "cefalexin", "cefuroxime", "cefixime", "ceftriaxone",
        "cefpodoxime", "cefdinir", "cefadroxil"
    ],
    "sulfonamide": [
        "cotrimoxazole", "bactrim", "septran", "sulfamethoxazole",
        "trimethoprim-sulfamethoxazole"
    ],
    "fluoroquinolone": [
        "ciprofloxacin", "ofloxacin", "levofloxacin", "norfloxacin",
        "moxifloxacin", "gatifloxacin"
    ],
    "macrolide": [
        "azithromycin", "erythromycin", "clarithromycin", "roxithromycin"
    ],
    "nsaid": [
        "ibuprofen", "diclofenac", "naproxen", "nimesulide",
        "aceclofenac", "piroxicam", "mefenamic acid", "ketorolac",
        "indomethacin", "combiflam"
    ],
    "aspirin": [
        "aspirin", "ecosprin", "disprin", "salicylate"
    ],
    "ace_inhibitor": [
        "ramipril", "enalapril", "lisinopril", "perindopril",
        "captopril", "trandolapril"
    ],
    "statin": [
        "atorvastatin", "rosuvastatin", "simvastatin",
        "lovastatin", "pitavastatin"
    ],
}

# ─── Cross-Allergy Rules ──────────────────────────────────────────────────────
CROSS_ALLERGY_WARNINGS = {
    "penicillin": {
        "families": ["cephalosporin"],
        "message": "Possible cross-reactivity (~10%). Use with caution."
    },
    "nsaid": {
        "families": ["aspirin"],
        "message": "Aspirin belongs to the same anti-inflammatory group."
    }
}

# ─── Drug-Drug Interactions ───────────────────────────────────────────────────
# Format: (drug_a, drug_b): (severity, message)
DANGEROUS_COMBOS = {
    ("warfarin", "aspirin"): ("HIGH", "Serious bleeding risk — combined anticoagulation"),
    ("warfarin", "nsaid"): ("HIGH", "NSAIDs increase bleeding risk with warfarin"),
    ("warfarin", "ciprofloxacin"): ("HIGH", "Fluoroquinolones potentiate warfarin — monitor INR"),
    ("warfarin", "metronidazole"): ("HIGH", "Metronidazole strongly potentiates warfarin"),
    ("metformin", "contrast"): ("HIGH", "Hold metformin before contrast procedures — lactic acidosis risk"),
    ("ssri", "tramadol"): ("HIGH", "Serotonin syndrome risk"),
    ("digoxin", "amiodarone"): ("HIGH", "Amiodarone raises digoxin levels — toxicity risk"),
    ("lithium", "nsaid"): ("HIGH", "NSAIDs raise lithium levels — toxicity risk"),
    ("lithium", "ace_inhibitor"): ("HIGH", "ACE inhibitors raise lithium levels"),
    ("methotrexate", "nsaid"): ("HIGH", "NSAIDs reduce methotrexate clearance — toxicity"),
    ("methotrexate", "cotrimoxazole"): ("HIGH", "Combined folate antagonism — severe toxicity"),
    ("aspirin", "nsaid"): ("HIGH", "Double NSAID use — Aspirin + NSAID increases GI bleeding risk significantly"),
    ("ibuprofen", "aspirin"): ("HIGH", "Ibuprofen and Aspirin together — severe GI bleeding and renal risk"),
    ("ibuprofen", "ace_inhibitor"): ("HIGH", "NSAIDs reduce ACE inhibitor efficacy and increase renal failure risk"),
    ("nsaid", "ace_inhibitor"): ("HIGH", "NSAIDs + ACE inhibitors — acute kidney injury risk (triple whammy)"),
    ("nsaid", "aspirin"): ("HIGH", "NSAID + Aspirin combination — high GI bleeding risk"),
    ("diclofenac", "aspirin"): ("HIGH", "Diclofenac + Aspirin — double NSAID risk: GI bleed, ulcer, renal failure"),
    ("amlodipine", "simvastatin"): ("MEDIUM", "Simvastatin dose should not exceed 20mg with amlodipine"),
    ("ace_inhibitor", "potassium"): ("MEDIUM", "Hyperkalaemia risk — monitor potassium levels"),
    ("digoxin", "clarithromycin"): ("MEDIUM", "Macrolides raise digoxin levels"),
    ("clopidogrel", "omeprazole"): ("MEDIUM", "Omeprazole reduces clopidogrel effectiveness"),
    ("theophylline", "ciprofloxacin"): ("MEDIUM", "Ciprofloxacin raises theophylline — toxicity risk"),
}

# ─── AI-Powered Drug Checking ───────────────────────────────────────────────

import os
import google.generativeai as genai
import json

# Load API key at module level
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def check_drug_conflicts_ai(patient_allergies: list, current_medicines: list, new_medicines: list) -> dict:
    """
    AI-powered drug conflict checker using Gemini.
    Handles ANY drug combination, not just hardcoded ones.
    """
    if not GOOGLE_API_KEY or "your_google" in GOOGLE_API_KEY:
        # Fall back to rule-based if no API key
        return check_drug_conflicts(patient_allergies, current_medicines, new_medicines)
    
    # Configure Gemini
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Build the prompt
    current_med_names = [m.get("name", "") for m in current_medicines]
    new_med_names = [m.get("name", "") for m in new_medicines]
    
    prompt = f"""
You are a medical drug interaction expert. Check for conflicts between medicines.

Patient allergies: {patient_allergies if patient_allergies else "None"}
Current medicines (already taking): {current_med_names if current_med_names else "None"}
New medicines (prescribed today): {new_med_names}

Check for:
1. Drug allergies - any new medicine from a family patient is allergic to
2. Drug-drug interactions - any dangerous combination between current and new medicines
3. Cross-reactivity - any chemically similar drugs that might cause issues

Return ONLY a JSON object in this exact format:
{{
    "has_alerts": true/false,
    "alerts": [
        {{
            "severity": "HIGH" or "MEDIUM" or "LOW",
            "type": "ALLERGY" or "INTERACTION" or "CROSS_REACTIVITY",
            "message": "Detailed explanation for the doctor"
        }}
    ]
}}

If no conflicts found, return has_alerts: false and empty alerts array.
Be specific about which drugs interact and what the risk is.
"""
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Strip markdown if present
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
        
        # Parse JSON
        result = json.loads(text)
        
        # Ensure required fields
        return {
            "has_alerts": result.get("has_alerts", False),
            "alert_count": len(result.get("alerts", [])),
            "high_severity": sum(1 for a in result.get("alerts", []) if a.get("severity") == "HIGH"),
            "alerts": result.get("alerts", [])
        }
    except Exception as e:
        # Fall back to rule-based on error
        print(f"AI drug check failed: {e}, falling back to rule-based")
        return check_drug_conflicts(patient_allergies, current_medicines, new_medicines)


def check_drug_conflicts(patient_allergies: list, current_medicines: list, new_medicines: list) -> dict:
    """
    Main function: checks all three layers of conflict.

    Args:
        patient_allergies: List of allergy strings, e.g. ["penicillin"]
        current_medicines: List of dicts with "name" key, e.g. [{"name": "Metformin"}]
        new_medicines: List of dicts with "name" key, e.g. [{"name": "Amoxicillin"}]

    Returns:
        Dict with has_alerts, alert_count, high_severity count, and alerts list.
    """
    alerts = []

    # Normalize medicine names to lowercase
    new_med_names = [m["name"].lower() for m in new_medicines]
    current_med_names = [m["name"].lower() for m in current_medicines]

    # ── Layer 1: Direct allergy check ──
    for allergy in patient_allergies:
        allergy_lower = allergy.lower()
        for family, drugs in ALLERGY_FAMILIES.items():
            # Check if the allergy matches a family name or a specific drug in the family
            if allergy_lower == family or allergy_lower in drugs:
                for new_name in new_med_names:
                    if any(drug in new_name for drug in drugs):
                        alerts.append({
                            "severity": "HIGH",
                            "type": "ALLERGY",
                            "message": (
                                f"ALLERGY ALERT: Patient is allergic to {allergy}. "
                                f"New prescription includes '{new_name}' "
                                f"which belongs to the {family} family."
                            )
                        })

    # ── Layer 2: Cross-allergy check ──
    for allergy in patient_allergies:
        allergy_lower = allergy.lower()
        if allergy_lower in CROSS_ALLERGY_WARNINGS:
            rule = CROSS_ALLERGY_WARNINGS[allergy_lower]
            for related_family in rule["families"]:
                related_drugs = ALLERGY_FAMILIES.get(related_family, [])
                for new_name in new_med_names:
                    if any(drug in new_name for drug in related_drugs):
                        alerts.append({
                            "severity": "MEDIUM",
                            "type": "CROSS_ALLERGY",
                            "message": (
                                f"CROSS-ALLERGY WARNING: Patient is allergic to {allergy}. "
                                f"'{new_name}' is in a related family ({related_family}). "
                                f"{rule['message']}"
                            )
                        })

    # ── Layer 3: Drug-drug interaction check ──
    all_meds = current_med_names + new_med_names
    for (drug_a, drug_b), (severity, message) in DANGEROUS_COMBOS.items():
        a_present = any(drug_a in med for med in all_meds)
        b_present = any(drug_b in med for med in all_meds)
        if a_present and b_present:
            alerts.append({
                "severity": severity,
                "type": "INTERACTION",
                "message": f"DRUG INTERACTION ({severity}): {message}"
            })

    # Sort: HIGH severity first
    alerts.sort(key=lambda x: 0 if x["severity"] == "HIGH" else 1)

    return {
        "has_alerts": len(alerts) > 0,
        "alert_count": len(alerts),
        "high_severity": sum(1 for a in alerts if a["severity"] == "HIGH"),
        "alerts": alerts
    }

# --- Extra helpers for chatbot -----------------------------------------------

def check_allergy_to_medicine(allergy_list: list, medicine_name: str) -> dict:
    """
    Check whether a specific medicine conflicts with a patient allergy list.
    Returns {has_conflict, severity, message}.
    """
    med_lower = medicine_name.strip().lower()
    for allergy in allergy_list:
        a = allergy.strip().lower()
        for family, drugs in ALLERGY_FAMILIES.items():
            if a == family or a in drugs:
                if any(d in med_lower for d in drugs):
                    return {
                        "has_conflict": True,
                        "severity": "HIGH",
                        "message": f"ALLERGY: {medicine_name} belongs to {family} family — patient is allergic to {allergy}.",
                    }
    return {"has_conflict": False, "severity": "NONE", "message": ""}


def get_drug_interactions_for_patient(current_medicines: list, new_medicine_name: str) -> list:
    """
    Return all known interactions between existing medicines and a new medicine.
    current_medicines: list of dicts with 'name' key.
    Returns list of interaction dicts with severity + message.
    """
    new_lower = new_medicine_name.strip().lower()
    interactions = []
    current_names = [m.get("name", "").strip().lower() for m in current_medicines]

    def _resolve_family(name: str) -> list[str]:
        result = [name]
        for fam, drugs in ALLERGY_FAMILIES.items():
            if any(d in name for d in drugs) or name == fam:
                result.append(fam)
        return result

    new_tokens = _resolve_family(new_lower)

    for cur in current_names:
        cur_tokens = _resolve_family(cur)
        for a in cur_tokens:
            for b in new_tokens:
                key = (a, b) if (a, b) in DANGEROUS_COMBOS else ((b, a) if (b, a) in DANGEROUS_COMBOS else None)
                if key:
                    sev, msg = DANGEROUS_COMBOS[key]
                    interactions.append({"severity": sev, "current_drug": cur, "new_drug": new_lower, "message": msg})
    return interactions
