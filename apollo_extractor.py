import requests
import pandas as pd
import os
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

# --- Configuration & Authentication (Compliance: Using official API) ---

# Load API Key from environment variable or .env file (preferred for security)
# Note: In a real-world scenario, you'd use a library like python-dotenv
# For simplicity, we assume the environment variable is set.
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY")
if not APOLLO_API_KEY:
    raise ValueError("APOLLO_API_KEY environment variable not set.")

BASE_URL = "https://api.apollo.io/v1/"
INPUT_FILE = "input_linkedin.txt"
OUTPUT_FILE = "apollo_contact_data.csv"
MOBILE_CREDITS_SIMULATED_COST = 1 # Each successful mobile unlock costs 1 credit (simulated)

def get_linkedin_identifier(url: str) -> Optional[str]:
    """Extracts the unique identifier (e.g., 'john-doe-example') from a LinkedIn URL."""
    try:
        path = urlparse(url).path
        # Clean up the path (e.g., /in/john-doe-example/ -> john-doe-example)
        parts = [p for p in path.split('/') if p]
        if 'in' in parts and len(parts) > parts.index('in') + 1:
            return parts[parts.index('in') + 1]
    except Exception:
        # Handle malformed URLs gracefully
        return None
    return None

def read_inputs(file_path: str) -> List[str]:
    """Reads LinkedIn URLs from the input file."""
    try:
        with open(file_path, 'r') as f:
            # Filter out empty lines and strip whitespace
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Input file '{file_path}' not found.")
        return []

def api_call(endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generic function to handle Apollo API calls."""
    headers = {'Content-Type': 'application/json'}
    payload['api_key'] = APOLLO_API_KEY
    
    url = BASE_URL + endpoint
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error at {endpoint} for payload {payload}: {e}")
        return None

def extract_person_data(person: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts the required fields from the Apollo Person object."""
    
    # Safely extract company data
    company = person.get('organization', {})
    
    # Get the mobile phone number if available and verified
    # Key Priority: Check 'mobile_phone_number' and 'mobile_phone_status'
    mobile_status = person.get('mobile_phone_status', 'unavailable')
    mobile_number = person.get('mobile_phone_number', '')

    # Apollo only returns verified corporate emails by default
    corporate_email = person.get('email', '')
    
    return {
        "First Name": person.get('first_name', ''),
        "Last Name": person.get('last_name', ''),
        "Job Title": person.get('title', ''),
        
        # Company Data
        "Company Name": company.get('name', ''),
        "Company Website": company.get('website_url', ''),
        "Company Industry": company.get('industry', ''),
        
        # Contact Data
        "Verified Corporate Email": corporate_email,
        "LinkedIn URL": person.get('linkedin_url', ''),

        # Mobile Optimization Fields (Key Priority)
        "Verified Mobile Phone Number": mobile_number if mobile_status == 'verified' else '',
        "Mobile Phone Status (Raw)": mobile_status, # Useful for debugging/tracking
        "Apollo Person ID": person.get('id', '')
    }

def lookup_and_enrich(linkedin_url: str, total_credits_spent: int) -> tuple[Dict[str, Any], int]:
    """
    Implements the two-stage lookup logic for data and mobile enrichment.
    
    Returns: A tuple of (extracted_data_dict, updated_credit_count)
    """
    
    # 1. Initial Lookup/Match (Endpoint: v1/people/match)
    print(f"\n-> Stage 1: Matching LinkedIn: {linkedin_url}...")
    
    linkedin_identifier = get_linkedin_identifier(linkedin_url)
    if not linkedin_identifier:
        print(f"   Skipping: Could not parse identifier from URL.")
        return {"LinkedIn URL": linkedin_url, "Status": "Invalid URL"}, total_credits_spent

    match_payload = {
        "linkedin_url": linkedin_url,
        "match_on_website": True # To help match company
    }
    match_result = api_call("people/match", match_payload)

    if not match_result or not match_result.get('person'):
        print("   Status: No match found on Apollo.io.")
        return {"LinkedIn URL": linkedin_url, "Status": "No Match"}, total_credits_spent

    person_data = match_result['person']
    extracted_data = extract_person_data(person_data)
    
    # 2. Mobile Optimization/Enrichment (Endpoint: v1/people/mobile/search)
    mobile_status = extracted_data['Mobile Phone Status (Raw)']
    person_id = extracted_data['Apollo Person ID']
    
    # Lookup Logic: Only proceed if a person ID is found AND the mobile is not already verified
    if person_id and mobile_status not in ['verified', 'unlocked']:
        print(f"   -> Stage 2: Mobile status is '{mobile_status}'. Attempting credit-consuming unlock for ID: {person_id}...")
        
        mobile_payload = {
            "id": person_id,
            "mobile_phone_only": True # Focus on mobile retrieval
        }
        mobile_result = api_call("people/mobile/search", mobile_payload)
        
        if mobile_result and mobile_result.get('person'):
            # Update the extracted data with the (hopefully) newly unlocked mobile info
            enriched_person = mobile_result['person']
            
            # **Credit Management Simulation**
            # If the mobile number is successfully returned, we simulate a credit consumption.
            if enriched_person.get('mobile_phone_number'):
                total_credits_spent += MOBILE_CREDITS_SIMULATED_COST
                extracted_data.update(extract_person_data(enriched_person)) # Re-run extraction for updated fields
                print(f"   ✅ SUCCESS: Mobile number unlocked and retrieved! New total credits spent (simulated): {total_credits_spent}")
            else:
                print("   ❌ FAIL: Mobile unlock attempted, but no number was returned.")
        else:
            print("   ⚠️ WARNING: Mobile unlock request failed or returned no person data.")
            
    elif mobile_status == 'verified':
        print("   Status: Mobile number already verified in Stage 1 data. Skipping Stage 2 unlock.")
    else:
        print(f"   Status: Mobile lookup not attempted (Status: {mobile_status}).")

    extracted_data['Simulated Credits Used'] = total_credits_spent # Track total
    return extracted_data, total_credits_spent


def main():
    """Main execution function."""
    print("--- Apollo.io Data Extraction (Intern Project) ---")
    
    linkedin_urls = read_inputs(INPUT_FILE)
    if not linkedin_urls:
        return

    results = []
    total_credits_spent = 0
    
    for url in linkedin_urls:
        data, total_credits_spent = lookup_and_enrich(url, total_credits_spent)
        results.append(data)

    # --- Export (Functional Requirement) ---
    df = pd.DataFrame(results)
    
    # Reorder columns to match the requirement priority (Mobile is key priority)
    required_fields = [
        "First Name", "Last Name", "Job Title", 
        "Company Name", "Company Website", "Company Industry", 
        "Verified Corporate Email", 
        "Verified Mobile Phone Number", # Key Priority
        "LinkedIn URL", 
        "Mobile Phone Status (Raw)",
        "Apollo Person ID",
        "Simulated Credits Used" # Tracking credit consumption
    ]
    
    # Ensure all required fields exist (filling missing ones)
    for field in required_fields:
        if field not in df.columns:
            df[field] = ""
            
    df = df[required_fields]
    df.to_csv(OUTPUT_FILE, index=False)
    
    print("\n--- Process Complete ---")
    print(f"Total Profiles Processed: {len(linkedin_urls)}")
    print(f"Final Simulated Mobile Credits Used: {total_credits_spent}")
    print(f"Results exported successfully to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
