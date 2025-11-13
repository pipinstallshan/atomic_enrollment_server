import csv
import json
import google.generativeai as genai
import os
from dotenv import load_dotenv
from models import db, FieldDefinition, Lead, LeadData
from typing import List, Dict, Any, Optional
import datetime
import aisuite

from utils.ai_prompts import create_prompt_for_column_mapping
load_dotenv(override=True)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def csv_to_json_list(input_csv_path: str) -> list[dict]:
    """
    Reads a CSV file, converts each line to a JSON object, and returns a list of these objects.
    Removes lines where all values are empty strings.

    Args:
        input_csv_path: The path to the input CSV file.

    Returns:
        A list of dictionaries, where each dictionary represents a line in the CSV.
    """
    json_list = []
    with open(input_csv_path, 'r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if any(value.strip() for value in row.values()):
                json_list.append(row)
    return json_list

def get_field_definitions() -> List[Dict[str, Any]]:
    """Get all field definitions from the database."""
    fields = FieldDefinition.query.all()
    return [{
        'name': field.name,
        'display_name': field.display_name,
        'description': field.description,
        'type': field.field_type,
        'required': field.is_required
    } for field in fields]

def ai_map_columns(input_csv_path: str, fields: List[Dict[str, Any]]) -> Dict[str, Optional[Dict]]:
    """
    Maps input CSV columns to output columns, handling direct matches and name splitting.

    Args:
        input_csv_path: Path to the CSV file
        fields: List of field definitions
        
    Returns:
        Dict[str, Optional[Dict]]: Mapping from output columns to input columns
    """
    # Get raw data
    raw_data_list = csv_to_json_list(input_csv_path)
    if not raw_data_list:
        return {}

    # Get input columns
    input_columns = list(raw_data_list[0].keys())
    
    prompt = create_prompt_for_column_mapping(raw_data_list=raw_data_list, fields=get_field_definitions())

    response = aisuite.Client().chat.completions.create(model="openai:gpt-4o", messages=[{"role": "user", "content": prompt}])

    content = response.choices[0].message.content

    content = content.strip("`json \n")

    column_mapping = json.loads(content)
    final_mapping = {}
    for mapping in column_mapping:
        if mapping["type"] == "match":
            final_mapping[mapping["Output"]] = {"type": mapping["type"], "input": mapping["Input"]}
        elif mapping["type"] == "complex":
            final_mapping[mapping["Output"]] = {"type": mapping["type"], "inputs": mapping["Input"]}
        elif mapping["type"] == "missing":
            final_mapping[mapping["Output"]] = {"type": mapping["type"]}

    return final_mapping



if __name__ == "__main__":

    print(ai_map_columns("Sample CSV.csv", get_field_definitions()))
