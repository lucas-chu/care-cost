import os
import json
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from functools import lru_cache

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/estimate', methods=['POST'])
def estimate():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        procedure = data.get('procedure')
        zip_code = data.get('zip_code')
        procedure_code = data.get('procedure_code', '')
        
        if not procedure or not zip_code:
            return jsonify({'error': 'Missing procedure or ZIP code'}), 400

        estimate = get_gpt_estimate(procedure, zip_code, procedure_code)
        return jsonify(estimate)
    except Exception as e:
        app.logger.error(f"Error in estimate route: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@lru_cache(maxsize=100)
def get_gpt_estimate(procedure, zip_code, procedure_code=''):
    try:
        procedure_specific_prompt = get_procedure_specific_prompt(procedure)
        prompt = f"""Estimate the cost of {procedure} in ZIP code {zip_code}.
        {f'The procedure code is {procedure_code}.' if procedure_code else ''}
        {procedure_specific_prompt}
        Provide the estimate as a JSON object with the following keys:
        'procedure_name', 'procedure_code', 'zip_code', 'low_estimate', 'high_estimate', 'typical_insurance_cost',
        'common_complications', 'alternative_procedures', 'recovery_info', 'additional_info'.
        For 'common_complications', provide an array of objects, each containing 'name' and 'estimated_cost'.
        For 'alternative_procedures', provide an array of objects, each containing 'name' and 'estimated_cost_range' (an array with two numbers).
        For 'recovery_info', provide an object with 'estimated_time' and 'associated_costs'.
        All cost values should be positive numbers without currency symbols.
        Use null for any information that is not applicable or cannot be determined."""

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response.")
        
        estimate_data = json.loads(content)
        
        # Validate and sanitize the data
        sanitized_data = sanitize_estimate_data(estimate_data)
        return sanitized_data
    except json.JSONDecodeError:
        app.logger.error("Failed to parse GPT-4o response as JSON")
        return {"error": "Unable to parse the estimate. Please try again."}
    except OpenAI.RateLimitError:
        app.logger.error("OpenAI API rate limit exceeded")
        return {"error": "Rate limit exceeded. Please try again later."}
    except OpenAI.APIError as e:
        app.logger.error(f"OpenAI API error: {str(e)}")
        return {"error": "An error occurred while fetching the estimate. Please try again."}
    except Exception as e:
        app.logger.error(f"Error in get_gpt_estimate: {str(e)}")
        return {"error": "An unexpected error occurred while estimating the cost. Please try again."}

def sanitize_estimate_data(data):
    def sanitize_cost(cost):
        try:
            return max(0, float(cost)) if cost is not None else None
        except (ValueError, TypeError):
            return None

    sanitized = {
        "procedure_name": data.get("procedure_name", "N/A"),
        "procedure_code": data.get("procedure_code", "N/A"),
        "zip_code": data.get("zip_code", "N/A"),
        "low_estimate": sanitize_cost(data.get("low_estimate")),
        "high_estimate": sanitize_cost(data.get("high_estimate")),
        "typical_insurance_cost": sanitize_cost(data.get("typical_insurance_cost")),
        "common_complications": [],
        "alternative_procedures": [],
        "recovery_info": {
            "estimated_time": data.get("recovery_info", {}).get("estimated_time", "N/A"),
            "associated_costs": sanitize_cost(data.get("recovery_info", {}).get("associated_costs"))
        },
        "additional_info": data.get("additional_info", "N/A")
    }

    for complication in data.get("common_complications", []):
        sanitized["common_complications"].append({
            "name": complication.get("name", "N/A"),
            "estimated_cost": sanitize_cost(complication.get("estimated_cost"))
        })

    for procedure in data.get("alternative_procedures", []):
        cost_range = procedure.get("estimated_cost_range", [])
        sanitized["alternative_procedures"].append({
            "name": procedure.get("name", "N/A"),
            "estimated_cost_range": [sanitize_cost(cost_range[0]) if len(cost_range) > 0 else None,
                                     sanitize_cost(cost_range[1]) if len(cost_range) > 1 else None]
        })

    return sanitized

def get_procedure_specific_prompt(procedure):
    procedure_prompts = {
        "Appendectomy": "Include information about laparoscopic vs. open procedures, typical hospital stay duration, and potential complications such as infection or abscess.",
        "Colonoscopy": "Include information about sedation options, polyp removal costs, and the importance of follow-up appointments.",
        "Hip Replacement": "Discuss different types of implants (ceramic, metal, plastic), rehabilitation costs, and potential complications like dislocation or infection.",
        "Knee Replacement": "Include information about partial vs. total knee replacement, rehabilitation costs, and potential complications like blood clots or infection.",
        "MRI Scan": "Discuss differences in costs for various body parts, contrast vs. non-contrast scans, and potential additional readings or interpretations.",
        "CT Scan": "Include information about contrast vs. non-contrast scans, radiation exposure, and potential additional costs for specialized CT procedures.",
        "Cataract Surgery": "Discuss different types of intraocular lenses, potential need for glasses post-surgery, and follow-up care costs.",
        "Childbirth (Vaginal Delivery)": "Include information about epidural costs, potential complications like C-section conversion, and postpartum care.",
        "Childbirth (C-Section)": "Discuss planned vs. emergency C-section costs, longer hospital stay, and potential complications like infection or blood loss.",
        "Dental Cleaning": "Include information about basic cleaning vs. deep cleaning, potential X-ray costs, and frequency recommendations.",
        "Root Canal": "Discuss costs for different types of teeth (molars vs. front teeth), potential need for a crown, and follow-up visits.",
        "Dental Crown": "Include information about different materials (porcelain, metal, ceramic), preparation costs, and temporary crown expenses.",
        "Tooth Extraction": "Discuss simple vs. surgical extraction costs, potential need for sedation, and post-extraction care.",
        "Physical Therapy Initial Evaluation": "Include information about assessment duration, potential tests or measurements, and treatment plan development.",
        "Physical Therapy Follow-up Session": "Discuss typical session duration, potential equipment or modality costs, and at-home exercise recommendations.",
        "Annual Physical Exam": "Include information about routine lab work, potential vaccinations, and preventive screenings based on age and gender.",
        "Mammogram": "Discuss 2D vs. 3D mammography costs, potential need for additional imaging, and frequency recommendations.",
        "Flu Shot": "Include information about different vaccine types (standard, high-dose for seniors), potential side effects, and effectiveness.",
        "Cholesterol Screening": "Discuss fasting vs. non-fasting tests, additional lipid panel components, and frequency recommendations based on risk factors.",
    }
    return procedure_prompts.get(procedure, "Provide detailed information about the procedure, including common variations, potential complications, and factors that might affect the cost.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
