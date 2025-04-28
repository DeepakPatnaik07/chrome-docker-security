import docker
import uuid
import os
import json
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai # Import Gemini library
import sys # Make sure sys is imported if needed elsewhere, or remove if not

# --- Direct Environment Check ---
print(f"*** Python Check: os.environ.get('GOOGLE_API_KEY') = {os.environ.get('GOOGLE_API_KEY')}")
# --- End Direct Check ---

# --- Load API Key ---
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY environment variable not set. AI analysis will be skipped.")
    # Depending on your needs, you might want to raise an error instead:
    # raise ValueError("GOOGLE_API_KEY environment variable not set.") 
genai.configure(api_key=GOOGLE_API_KEY)
# --- End API Key Load ---

app = FastAPI()

# Add CORS middleware
origins = [
    "*" # Allow all origins for local testing
    # "chrome-extension://YOUR_EXTENSION_ID_HERE" # TODO: Replace * with your production Extension ID when published
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)

class Link(BaseModel):
    url: str

# --- Gemini Analysis Function ---
async def analyze_with_gemini(local_analysis: dict) -> dict:
    if not GOOGLE_API_KEY:
        return {"ai_skipped": True, "ai_reason": "API key not configured"}

    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # --- Revised Prompt for Simpler Output ---
        prompt = f"You are a security assistant evaluating a URL for a non-technical user.\n"
        prompt += f"Analyze the following web page data for potential phishing or security risks.\n"
        prompt += f"URL: {local_analysis.get('url', 'N/A')}\n"
        # prompt += f"Page Title: {local_analysis.get('title', 'N/A')}\n" # Title might add noise, let's remove for simplicity
        if local_analysis.get("analysis", {}).get("suspicious"): 
             prompt += f"Local analysis flagged these potential issues: {local_analysis.get('analysis', {}).get('reasons', [])}\n"
        else:
            prompt += "Local analysis did not find obvious suspicious indicators.\n"
        prompt += f"Number of redirects: {len(local_analysis.get('redirects', []))}\n"
        # prompt += f"Number of external iframes: {len([f for f in local_analysis.get('iframes', []) if 'External domain' in f])}\n" # Less critical detail
        
        prompt += "\nBased ONLY on the provided data, give a simple verdict: 'Looks Safe', 'Potentially Risky', or 'Suspicious'. "
        prompt += "Followed by a single, very brief sentence explaining the main reason in plain language suitable for a regular computer user."
        # --- End Revised Prompt ---
        
        print("--- Sending prompt to Gemini (Revised) --- ")
        # print(prompt) # Uncomment to debug prompt

        response = await model.generate_content_async(
             prompt,
             safety_settings=[ 
                 {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                 {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                 {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                 {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
             ]
             )
        
        print("--- Received response from Gemini --- ")
        ai_response_text = response.text

        return {
            "ai_skipped": False,
            "ai_assessment": ai_response_text 
        }

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return {"ai_skipped": True, "ai_reason": f"API call failed: {e}"}
# --- End Gemini Function ---

@app.post("/analyze_link")
async def analyze_link(link: Link):
    client = docker.from_env()
    container_name = f"urlscanner-{uuid.uuid4()}"
    local_analysis_result = {} # Initialize result dict

    # --- Step 1: Run Docker Analysis --- 
    try:
        command_to_run = ["python3", "/app/analyze_url.py", link.url]
        container = client.containers.run(
            image="safe-link-scanner",
            command=command_to_run,
            name=container_name,
            detach=True,
        )
        container.wait()
        logs = container.logs(stream=False, stdout=True, stderr=True).decode('utf-8', errors='ignore')
        container.remove(force=True)
        print("--- Container Logs ---")
        print(logs)
        
        # Parse logs from container
        try:
            start_marker = "---JSON_START---"
            end_marker = "---JSON_END---"
            start_index = logs.find(start_marker)
            end_index = logs.find(end_marker)
            if start_index != -1 and end_index != -1:
                json_string = logs[start_index + len(start_marker) : end_index].strip()
                if json_string:
                    local_analysis_result = json.loads(json_string)
                else:
                     local_analysis_result = {"status": "error", "error": "Empty JSON string found in logs", "details_raw": logs}
            else:
                 local_analysis_result = {"status": "error", "error": "Could not find JSON delimiters in logs", "details_raw": logs}
        except Exception as e:
            local_analysis_result = {"status": "error", "error": f"Failed to process container logs: {e}", "details_raw": logs}

    except Exception as e:
        local_analysis_result = {"status": "error", "error": f"Docker execution failed: {e}", "details_raw": None}
    # --- End Docker Analysis --- 

    # --- Step 2: Run AI Analysis (if local analysis didn't fail badly) ---
    ai_analysis_result = {}
    if local_analysis_result.get("status") != "error" or local_analysis_result.get("url"): # Proceed if we have a URL
        ai_analysis_result = await analyze_with_gemini(local_analysis_result)
    else:
        ai_analysis_result = {"ai_skipped": True, "ai_reason": "Local analysis failed before AI step."}
    # --- End AI Analysis ---

    # --- Step 3: Merge Results --- 
    # Ensure 'analysis' key exists
    if "analysis" not in local_analysis_result:
        local_analysis_result["analysis"] = {}
    # Merge AI results into the analysis section
    local_analysis_result["analysis"].update(ai_analysis_result)
    # --- End Merge Results ---

    # Return the final combined result
    return local_analysis_result