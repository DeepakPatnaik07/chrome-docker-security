import sys
import asyncio
import json
import re # Import re for regex
from urllib.parse import urlparse
from playwright.async_api import async_playwright

url_to_test = sys.argv[1] if len(sys.argv) > 1 else "http://example.com"

# --- Helper Function ---
def get_domain(url):
    try:
        # Handle cases like 'about:blank'
        parsed = urlparse(url)
        if not parsed.netloc:
            return None
        # Simple split, might need refinement for complex TLDs like .co.uk
        parts = parsed.netloc.split('.')
        if len(parts) >= 2:
            # Handle cases like www.google.com -> google.com
            # and login.google.co.uk -> google.co.uk (basic TLD handling)
            is_second_level = len(parts[-2]) <= 3 # co, org, com etc.
            if len(parts) >= 3 and is_second_level:
                 return parts[-3] + '.' + parts[-2] + '.' + parts[-1]
            return parts[-2] + '.' + parts[-1]
        return parsed.netloc # Return full netloc if only one part (e.g., localhost)
    except Exception:
        return None

def is_ip_address(hostname):
    # Simple regex for IPv4, could add IPv6 if needed
    pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    return re.match(pattern, hostname) is not None
# --- End Helper ---

async def run(playwright):
    results = {
        "status": "pending",
        "url": url_to_test,
        "title": "",
        "requests": [],
        "redirects": [],
        "iframes": [],
        "page_content_preview": "", # Add preview field
        "analysis": {
            "suspicious": False,
            "reasons": [],
            "local_checks_passed": 0
        },
        "error": None
    }
    checks_to_run = 0

    browser = None
    try:
        browser = await playwright.chromium.launch(
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu'
            ]
        )
        page = await browser.new_page()

        parsed_url = urlparse(url_to_test)
        original_domain = get_domain(url_to_test)
        original_hostname = parsed_url.netloc
        suspicious_tlds = {'.xyz', '.top', '.info', '.tk', '.ml', '.ga', '.cf', '.gq'} # Example list
        common_brands = {'paypal', 'google', 'amazon', 'microsoft', 'apple', 'facebook', 'netflix', 'ebay'}
        phishing_keywords = {'login', 'password', 'verify', 'confirm', 'account', 'update', 'secure', 'suspended', 'payment', 'credentials'}

        # Capture requests and redirects, perform basic checks
        page.on("request", lambda request: results["requests"].append(request.url))
        page.on("response", lambda response: \
            results["redirects"].append(response.url) if response.status >= 300 and response.status < 400 else None)

        await page.goto(url_to_test, wait_until='domcontentloaded', timeout=30000)
        results["title"] = await page.title()

        # Get page content preview (first 500 chars)
        try:
            content = await page.content()
            results["page_content_preview"] = (content or "")[:500]
        except Exception as e:
            print(f"Error getting page content: {e}")
            results["page_content_preview"] = "[Error fetching content]"

        # --- Local Phishing Analysis --- 
        checks_to_run = 0

        # 1. URL uses IP Address?
        checks_to_run += 1
        if original_hostname and is_ip_address(original_hostname):
            results["analysis"]["suspicious"] = True
            results["analysis"]["reasons"].append(f"URL uses direct IP address: {original_hostname}")
        else:
            results["analysis"]["local_checks_passed"] += 1

        # 2. Immediate Meta Refresh? 
        checks_to_run += 1
        try:
            meta_refresh = await page.query_selector('meta[http-equiv="refresh"]')
            if meta_refresh:
                content_attr = await meta_refresh.get_attribute('content')
                if content_attr and content_attr.strip().startswith('0;'): # Check if refresh is immediate (0 seconds)
                    results["analysis"]["suspicious"] = True
                    results["analysis"]["reasons"].append(f"Immediate meta refresh detected: content='{content_attr}'")
                else:
                     results["analysis"]["local_checks_passed"] += 1 # Count non-immediate refresh as passed
        except Exception as e:
            print(f"Error checking meta refresh: {e}") # Log error but don't fail analysis

        # 3. URL Structure checks (if not IP based)
        if original_domain and not is_ip_address(original_hostname):
            checks_to_run += 2 # Subdomain count + brand check
            # Excessive subdomains?
            subdomain_parts = original_hostname.split('.')
            if len(subdomain_parts) > 5:
                 results["analysis"]["suspicious"] = True
                 results["analysis"]["reasons"].append(f"Excessive subdomains detected ({len(subdomain_parts)} parts)")
            else:
                results["analysis"]["local_checks_passed"] += 1
            # Brand name mismatch?
            found_brand_in_subdomain = False
            for brand in common_brands:
                # Check if brand is in subdomain part but NOT the main domain
                if brand in original_hostname and brand not in original_domain:
                     found_brand_in_subdomain = True
                     results["analysis"]["suspicious"] = True
                     results["analysis"]["reasons"].append(f"Brand mismatch: '{brand}' in subdomain/hostname but not main domain.")
                     break # Only flag first found brand
            if not found_brand_in_subdomain:
                 results["analysis"]["local_checks_passed"] += 1

        # 4. Request Domain/TLD Checks (Existing - slightly modified)
        checks_to_run += 1
        external_domains = set()
        for req_url in results["requests"]:
            req_domain = get_domain(req_url)
            if req_domain and original_domain and req_domain != original_domain:
                 # Basic check to avoid flagging subdomains of the original domain
                 if not req_domain.endswith(original_domain):
                     external_domains.add(req_domain)
            # TLD Check
            try:
                tld = '.' + urlparse(req_url).netloc.split('.')[-1]
                if tld in suspicious_tlds:
                    results["analysis"]["suspicious"] = True
                    results["analysis"]["reasons"].append(f"Request to suspicious TLD ({tld}): {req_url}")
            except Exception:
                pass # Ignore errors parsing request URLs
        
        if len(external_domains) > 10:
             results["analysis"]["suspicious"] = True
             results["analysis"]["reasons"].append(f"High number of unique external domains requested: {len(external_domains)}")

        # 5. IFrame Check (Refined)
        checks_to_run += 1
        initial_reasons_count = len(results["analysis"]["reasons"])
        iframes = page.frames
        if len(iframes) > 1:
            for frame in iframes[1:]:
                try:
                    frame_url = frame.url
                    # Skip empty/internal frames more reliably
                    if frame_url and frame_url != 'about:blank' and not frame_url.startswith('data:'):
                        results["iframes"].append(frame_url)
                        frame_domain = get_domain(frame_url)
                        if frame_domain and original_domain and frame_domain != original_domain:
                            if not frame_domain.endswith(original_domain):
                                results["analysis"]["suspicious"] = True
                                results["analysis"]["reasons"].append(f"External domain iframe detected: {frame_url}")
                    else:
                         results["iframes"].append("[Internal/Blank Frame]")
                except Exception as e:
                    results["iframes"].append(f"[Error fetching frame URL: {e}]")
        if len(results["analysis"]["reasons"]) == initial_reasons_count:
            results["analysis"]["local_checks_passed"] += 1

        # 6. Redirect Check (Existing)
        checks_to_run += 1
        initial_reasons_count = len(results["analysis"]["reasons"])
        redirect_count = len(results["redirects"])
        if redirect_count > 5:
             results["analysis"]["suspicious"] = True
             results["analysis"]["reasons"].append(f"High number of redirects: {redirect_count}")
        if len(results["analysis"]["reasons"]) == initial_reasons_count:
             results["analysis"]["local_checks_passed"] += 1

        # 7. Password Field Check
        checks_to_run += 1
        try:
            password_input = await page.query_selector('input[type="password"]')
            print(f"DEBUG: Password field query result: {password_input}") # DEBUG LOG
            if password_input:
                results["analysis"]["suspicious"] = True
                results["analysis"]["reasons"].append("Password input field found on page.")
            else:
                 results["analysis"]["local_checks_passed"] += 1
        except Exception as e:
            print(f"Error checking for password field: {e}")

        # 8. Keyword Check
        checks_to_run += 1
        try:
            page_text = await page.locator('body').inner_text(timeout=5000) 
            page_text_lower = page_text.lower()
            print(f"DEBUG: Page text (first 200 chars): {page_text_lower[:200]}") # DEBUG LOG
            found_keywords = set()
            for keyword in phishing_keywords:
                if keyword in page_text_lower:
                    found_keywords.add(keyword)
            print(f"DEBUG: Found keywords: {found_keywords}") # DEBUG LOG
            if len(found_keywords) > 1: 
                 results["analysis"]["suspicious"] = True
                 results["analysis"]["reasons"].append(f"Potential phishing keywords found: {list(found_keywords)}")
            else:
                results["analysis"]["local_checks_passed"] += 1
        except Exception as e:
            print(f"Error checking keywords: {e}")
        
        # Update passed checks count
        results["analysis"]["local_checks_total"] = checks_to_run
        # --- End Local Phishing Analysis ---

        results["status"] = "analyzed"

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
    finally:
        if browser:
            await browser.close()

    # Print results as JSON with delimiters
    print("---JSON_START---")
    print(json.dumps(results, indent=2))
    print("---JSON_END---")

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

asyncio.run(main())