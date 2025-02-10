import os
import json
import time
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.serving import WSGIRequestHandler
from functools import partial

# Set HTTP protocol version
WSGIRequestHandler.protocol_version = "HTTP/1.1"

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
CORS(app)

# Endpoints for Company API
CORESIGNAL_FILTER_URL = "https://api.coresignal.com/cdapi/v1/professional_network/company/search/filter"
CORESIGNAL_COLLECT_URL = "https://api.coresignal.com/cdapi/v1/professional_network/company/collect/{company_id}"
EMPLOYEE_SEARCH_URL = "https://api.coresignal.com/cdapi/v1/professional_network/employee/search/filter"
CORESIGNAL_API_KEY = os.getenv("CORESIGNAL_API_KEY")

# Allowed filter keys
ALLOWED_FILTERS = {
    "name", "website", "exact_website", "size", "industry", "country", "location",
    "created_at_gte", "created_at_lte", "last_updated_gte", "last_updated_lte",
    "employees_count_gte", "employees_count_lte", "source_id", "founded_year_gte",
    "founded_year_lte", "funding_total_rounds_count_gte", "funding_total_rounds_count_lte",
    "funding_last_round_type", "funding_last_round_date_gte", "funding_last_round_date_lte"
}

# Dropdown options
INDUSTRIES = [
    "Railroad Manufacture", "Gambling & Casinos", "Alternative Dispute Resolution", 
    "Translation & Localization", "Museums & Institutions", "Motion Pictures & Film", 
    "Information Technology & Services", "Apparel & Fashion", "Farming", "Judiciary", 
    "Banking", "Airlines/Aviation", "Photography", "Telecommunications", "Printing", 
    "Machinery", "Textiles", "Hospitality", "Transportation/Trucking/Railroad", "Retail", 
    "Construction", "Utilities", "Supermarkets", "Research", "Sports", "Internet", 
    "Accounting", "Insurance", "Automotive", "Semiconductors", "Warehousing", 
    "Restaurants", "Entertainment", "Cosmetics", "Chemicals", "Biotechnology", 
    "Philanthropy", "Wholesale", "Design", "Ranching", "Libraries", "Dairy", "Newspapers", 
    "Maritime", "Pharmaceuticals", "Military", "Outsourcing/Offshoring", "Fishery", 
    "Furniture", "Animation", "Publishing", "Plastics", "Other", "Wireless", "Music", 
    "E-learning", "Veterinary", "Shipbuilding", "Fundraising", "Tobacco", "Nanotechnology", 
    "Think Tanks", "Public Relations & Communications", "Import & Export", 
    "Mechanical Or Industrial Engineering", "Arts & Crafts", "Computer Hardware", 
    "Electrical & Electronic Manufacturing", "Consumer Electronics", "Human Resources", 
    "Civil Engineering", "Capital Markets", "Non-profit Organization Management", 
    "Financial Services", "Packaging & Containers", "Computer Software", 
    "Alternative Medicine", "Consumer Services", "Luxury Goods & Jewelry", 
    "Industrial Automation", "Computer & Network Security", "Civic & Social Organization", 
    "Facilities Services", "Medical Practice", "Primary/Secondary Education", 
    "Staffing & Recruiting", "Broadcast Media", "Marketing & Advertising", 
    "Health, Wellness & Fitness", "Logistics & Supply Chain", 
    "Business Supplies & Equipment", "Real Estate", "Information Services", 
    "Education Management", "Consumer Goods", "Food & Beverages", "Law Practice", 
    "Government Administration", "Management Consulting", "Law Enforcement", 
    "Building Materials", "Executive Office", "Political Organization", 
    "Government Relations", "Renewables & Environment", "Investment Management", 
    "Hospital & Health Care", "Glass, Ceramics & Concrete", "Higher Education", 
    "Program Development", "Oil & Energy", "International Affairs", "Fine Art", 
    "International Trade & Development", "Mining & Metals", "Medical Device", 
    "Food Production", "Market Research", "Paper & Forest Products", 
    "Computer Networking", "Defense & Space", "Writing & Editing", "Graphic Design", 
    "Environmental Services", "Computer Games", "Security & Investigations", 
    "Venture Capital & Private Equity", "Aviation & Aerospace", "Public Policy", 
    "Events Services", "Public Safety", "Package/Freight Delivery", 
    "Architecture & Planning", "Leisure, Travel & Tourism", "Commercial Real Estate", 
    "Individual & Family Services", "Investment Banking", "Sporting Goods", 
    "Professional Training & Coaching", "Legal Services", 
    "Recreational Facilities & Services", "Legislative Office", 
    "Religious Institutions", "Mental Health Care", "Online Media", 
    "Wine & Spirits", "Media Production", "Performing Arts"
]

COUNTRIES = [
    "United States", "United Kingdom", "Canada", "Australia", "India", "Germany", 
    "France", "Brazil", "Japan", "China", "Singapore", "Netherlands", "Spain", 
    "Sweden", "Switzerland", "Italy", "Israel", "Ireland", "Norway", "Denmark", 
    "Finland", "Belgium", "New Zealand", "Austria", "Poland", "South Korea", 
    "Mexico", "South Africa", "Portugal", "Argentina", "Chile", "Colombia", 
    "Russia", "Turkey", "Indonesia", "Malaysia", "Thailand", "Vietnam", 
    "Philippines", "United Arab Emirates", "Saudi Arabia"
]

@app.route('/')
def index():
    return render_template("index.html", industries=INDUSTRIES, countries=COUNTRIES)

def collect_company_by_id(session, company_id):
    """
    Collect data for a single company using the individual collect endpoint
    """
    collect_url = CORESIGNAL_COLLECT_URL.format(company_id=company_id)
    headers = {
        "Authorization": f"Bearer {CORESIGNAL_API_KEY}",
        "accept": "application/json"
    }
    
    try:
        response = session.get(collect_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to collect company {company_id}: {str(e)}")
        return None
@app.route('/employees/<company_id>', methods=['GET'])
def get_employees(company_id):
    try:
        # Create session for consistent timeout settings
        session = requests.Session()
        session.request = partial(session.request, timeout=30)

        # Build filter payload for employees - using correct filters from docs
        filter_payload = {
            "experience_company_id": int(company_id),
            "active_experience": True
        }

        print(f"DEBUG - Employee filter payload: {json.dumps(filter_payload, indent=2)}")
        response = session.post(
            EMPLOYEE_SEARCH_URL,
            headers={
                "Authorization": f"Bearer {CORESIGNAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json=filter_payload
        )
        
        # Add detailed logging
        print(f"DEBUG - Employee search response status: {response.status_code}")
        print(f"DEBUG - Employee search response headers: {dict(response.headers)}")
        print(f"DEBUG - Employee search response content: {response.text[:500]}...")
        
        response.raise_for_status()
        employee_ids = response.json()

        if not isinstance(employee_ids, list):
            return jsonify({
                "error": "Unexpected response format from employee search",
                "employees": [],
                "total": 0
            })

        # Get details for each employee (limit to first 5)
        employees = []
        for emp_id in employee_ids[:5]:  # Limit to 5 employees
            try:
                # Use the collect endpoint for each employee
                emp_url = f"https://api.coresignal.com/cdapi/v1/professional_network/employee/collect/{emp_id}"
                emp_response = session.get(
                    emp_url,
                    headers={
                        "Authorization": f"Bearer {CORESIGNAL_API_KEY}",
                        "accept": "application/json"
                    }
                )
                
                if emp_response.status_code == 200:
                    employee = emp_response.json()
                    
                    # Find current experience at this company
                    current_experience = next(
                        (
                            exp for exp in employee.get("member_experience_collection", [])
                            if not exp.get("deleted") and 
                            str(exp.get("company_id")) == str(company_id) and
                            exp.get("date_to") is None  # Current position will have no end date
                        ),
                        {}
                    )

                    # Get skills
                    skills = [
                        skill.get("member_skill_list", {}).get("skill")
                        for skill in employee.get("member_skills_collection", [])
                        if not skill.get("deleted") and skill.get("member_skill_list")
                    ]

                    # Get education
                    education = [
                        {
                            "institution": edu.get("title"),
                            "program": edu.get("subtitle"),
                            "date_from": edu.get("date_from"),
                            "date_to": edu.get("date_to")
                        }
                        for edu in employee.get("member_education_collection", [])
                        if not edu.get("deleted")
                    ]

                    # Process employee data with more details
                    processed_employee = {
                        "name": employee.get("name"),
                        "title": current_experience.get("title", employee.get("title")),
                        "location": employee.get("location"),
                        "profile_url": employee.get("url"),
                        "experience": current_experience.get("description"),
                        "start_date": current_experience.get("date_from"),
                        "duration": current_experience.get("duration"),
                        "industry": employee.get("industry"),
                        "skills": skills,
                        "education": education,
                        "summary": employee.get("summary"),
                        "connections": employee.get("connections")
                    }
                    
                    # Only add if we have at least a name or title
                    if processed_employee["name"] or processed_employee["title"]:
                        employees.append(processed_employee)
                
                time.sleep(1)  # Respect rate limits
                
            except Exception as e:
                print(f"Error fetching employee {emp_id}: {str(e)}")
                continue

        return jsonify({
            "employees": employees,
            "total": len(employee_ids)
        })

    except Exception as e:
        print(f"Employee search error: {str(e)}")
        error_message = str(e)
        if "422" in error_message:
            error_message = "Unable to fetch employee data. Please try again."
        return jsonify({"error": error_message}), 500

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No request data provided"}), 400

        # Limit page size
        page = data.get("page", 0)
        limit = min(data.get("limit", 3), 3)

        # Build filter payload
        filter_payload = {}
        
        if data.get("country"):
            filter_payload["country"] = data["country"]
        if data.get("industry"):
            filter_payload["industry"] = data["industry"]
        if data.get("employees_count_gte"):
            filter_payload["employees_count_gte"] = int(data["employees_count_gte"])
        if data.get("employees_count_lte"):
            filter_payload["employees_count_lte"] = int(data["employees_count_lte"])

        print("DEBUG - filter payload:", json.dumps(filter_payload, indent=2))

        # Create session for consistent timeout settings
        session = requests.Session()
        session.request = partial(session.request, timeout=30)

        # Get company IDs
        print("Fetching company IDs...")
        response = session.post(
            CORESIGNAL_FILTER_URL,
            headers={
                "Authorization": f"Bearer {CORESIGNAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json=filter_payload
        )
        response.raise_for_status()
        filter_response = response.json()

        if not isinstance(filter_response, list):
            print("Unexpected response format:", filter_response)
            return jsonify({"error": "Unexpected response format from API"}), 500

        # Paginate IDs
        start = page * limit
        end = start + limit
        paginated_ids = filter_response[start:end]
        total_results = len(filter_response)

        print(f"Found {total_results} total results, processing page {page + 1} ({start}-{end})")

        if not paginated_ids:
            return jsonify({
                "results": [],
                "total": total_results,
                "page": page,
                "hasMore": end < total_results
            }), 200

        # Collect individual company details
        processed_results = []
        for company_id in paginated_ids:
            company = collect_company_by_id(session, company_id)
            if company:
                processed = {
                    "ID": company.get("id"),
                    "Name": company.get("name"),
                    "Website": company.get("website"),
                    "Size": company.get("size"),
                    "Industry": company.get("industry"),
                    "Country": (company.get("headquarters_country_parsed") or 
                              company.get("headquarters_country_restored")),
                    "Location": (company.get("headquarters_new_address") or 
                               company.get("location")),
                    "Employees Count": company.get("employees_count"),
                    "Founded": company.get("founded"),
                    "Type": company.get("type")
                }
                processed_results.append(processed)
            time.sleep(1)  # Add delay between requests to respect rate limits

        return jsonify({
            "results": processed_results,
            "total": total_results,
            "page": page,
            "hasMore": end < total_results
        })

    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 Starting Flask app on http://127.0.0.1:10000")
    app.run(host="0.0.0.0", port=10000, debug=True)
