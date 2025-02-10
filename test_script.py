import openai
import os
import requests
import json

# Set API keys
openai.api_key = os.getenv("OPENAI_API_KEY")
CORESIGNAL_API_KEY = os.getenv("CORESIGNAL_API_KEY")

# Function to process user query with OpenAI
def process_query(prompt):
    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Extract structured parameters from user queries in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        # ✅ Ensure JSON format
        structured_params = json.loads(response.choices[0].message.content)
        return structured_params

    except Exception as e:
        print(f"❌ Error in OpenAI API request: {e}")
        return None  # Return None on failure

# Function to query Coresignal API
def query_coresignal(params):
    if params is None:
        return {"error": "No valid query parameters extracted from OpenAI."}

    url = "https://api.coresignal.com/cdapi/v1/multi_source/company/search/es_dsl"

    headers = {
        "Authorization": f"Bearer {CORESIGNAL_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # ✅ Fixing the query format (Coresignal expects specific structure)
    query_body = {
        "query": {
            "bool": {
                "must": []
            }
        }
    }  # ❌ Removed "size"

    # ✅ Add filters based on extracted parameters
    if "location" in params:
        query_body["query"]["bool"]["must"].append({"match": {"hq_country": params["location"]}})

    # ✅ Use 'industry.keyword' instead of just 'industry' (Coresignal may expect this)
    if "industry" in params:
        query_body["query"]["bool"]["must"].append({"match": {"industry.keyword": params["industry"]}})

    # ✅ Convert employee_count range correctly
    if "employee_count" in params:
        employee_range = params["employee_count"]
        query_body["query"]["bool"]["must"].append({
            "range": {
                "employees_count": {  # Ensure correct field name
                    "gte": employee_range.get("min", 1),  # Minimum employees
                    "lte": employee_range.get("max", 10000)  # Maximum employees
                }
            }
        })

    # ✅ Debug: Print the final query payload
    print("\n🛠️ Final API Query Payload:", json.dumps(query_body, indent=2))

    try:
        response = requests.post(url, headers=headers, json=query_body)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"\n❌ Coresignal API Error: {response.status_code}")
            print("Response Body:", response.text)
            return {"error": f"API request failed with status code {response.status_code}", "details": response.text}

    except Exception as e:
        return {"error": f"Failed to connect to Coresignal API: {e}"}

# Function to format response for better readability
def format_response(api_response):
    if isinstance(api_response, dict) and "error" in api_response:
        return f"❌ Coresignal API Error: {api_response['error']}"

    if isinstance(api_response, list):  # ✅ FIX: Check if response is a list
        business_ids = api_response  # The API returned a list of company IDs

        if not business_ids:
            return "🔹 No companies found matching your criteria."

        formatted_results = []
        for company_id in business_ids:
            formatted_results.append(f"Company ID: {company_id}")

        return formatted_results

    return "❌ Unexpected API response format."

# Main script execution
if __name__ == "__main__":
    user_query = "Show me companies in Italy in retail with 10-15 employees"
    structured_params = process_query(user_query)

    if structured_params:
        print("\n🔹 Extracted Query Parameters:", structured_params)

        # Query Coresignal API
        coresignal_results = query_coresignal(structured_params)

        # Format and display response
        formatted_data = format_response(coresignal_results)
        print("\n🔹 Coresignal API Results:", json.dumps(formatted_data, indent=2))
    else:
        print("\n❌ Failed to extract query parameters from OpenAI.")
