# Apollo.io_Data_Extraction
Apollo.io Data Extraction Solution

1. Project Overview & Compliance 🛡️
Goal: Develop a compliant Python solution for extracting contact and company data from Apollo.io, prioritizing the retrieval of a Verified Mobile Phone Number.

Compliance Mandate: This script strictly adheres to the Apollo.io Terms of Service (ToS) and global data privacy regulations (GDPR, CCPA) by exclusively using the official Apollo.io API. No unauthorized web scraping is used.

2. Setup and Prerequisites
Python: Requires Python 3.8+

Dependencies:

Bash

pip install requests pandas
API Key: Obtain your Apollo.io API Key from your account settings.

3. Configuration
Create a file named .env (or set environment variables) and store your key:

# .env file
APOLLO_API_KEY="YOUR_APOLLO_API_KEY_HERE"
4. Usage
Input:

Create an input file (e.g., input_linkedin.txt) with one LinkedIn profile URL per line.

# input_linkedin.txt
https://www.linkedin.com/in/john-doe-example
https://www.linkedin.com/in/jane-smith-sample
...
Run the script:

Bash

python apollo_extractor.py
Output: The results will be exported to a file named apollo_contact_data.csv.

5. Technical Logic & Mobile Optimization 📱 (Key Priority)
The script implements a two-stage enrichment strategy to maximize mobile number retrieval while managing costs:

Initial Lookup (API Endpoint: v1/people/match):

This is the primary search method, using the LinkedIn URL to find the person's profile in Apollo.

It returns standard data (Name, Title, Company, Email) and whether a mobile number is available (e.g., in a mobile_phone_status field).

Mobile Enrichment (API Endpoint: v1/people/mobile/search):

Credit Management: The script checks the data from the initial lookup. If the profile is found AND the mobile number is not yet retrieved/verified, it will proceed to the specific, credit-consuming mobile enrichment endpoint.

Optimization: This targeted approach ensures we only spend a mobile credit (/v1/people/mobile/search) when we have a high-confidence match (from /v1/people/match) and a mobile number is explicitly marked as available/unlocked.
