import pytest
from unittest.mock import patch, MagicMock
import utils.csv_tools
import json
from models import FieldDefinition, Lead, LeadData, db
from main import app
import os

from utils.ai_prompts import create_prompt_for_csv_tools_test

# Sample field definitions for testing
@pytest.fixture
def sample_field_definitions():
    return [
        {"name": "first_name", "display_name": "First Name", "description": "The person's first name", "field_type": "text", "is_required": False},
        {"name": "last_name", "display_name": "Last Name", "description": "The person's last name", "field_type": "text", "is_required": False},
        {"name": "website_url", "display_name": "Website URL", "description": "The website URL", "field_type": "text", "is_required": True},
        {"name": "ads_url", "display_name": "Ads URL", "description": "The ads URL", "field_type": "text", "is_required": False},
        {"name": "niche_category", "display_name": "Niche Category", "description": "The niche category", "field_type": "text", "is_required": True},
        {"name": "employees", "display_name": "Employees", "description": "Number of employees", "field_type": "text", "is_required": False},
        {"name": "revenue", "display_name": "Revenue", "description": "Company revenue", "field_type": "text", "is_required": False},
    ]

# Test cases for ai_map_columns
@pytest.mark.parametrize("csv_data, expected_mapping", [
    # Test case 1: Successful mapping of all types
    (
        [
            {"Full Name": "John Doe", "Website": "https://example.com", "Ad URL": "https://example.com/ads", "Category": "Tech", "Expenses": "$500k"}
        ],
        {
            "first_name": {"type": "complex", "inputs": ["Full Name"]},
            "last_name": {"type": "complex", "inputs": ["Full Name"]},
            "website_url": {"type": "match", "input": "Website"},
            "ads_url": {"type": "match", "input": "Ad URL"},
            "niche_category": {"type": "match", "input": "Category"},
            "employees": {"type": "missing"},
            "revenue": {"type": "missing"}
        }
    ),
    # Test case 2: Empty CSV data
    (
        [],
        {}
    ),
])
def test_ai_map_columns(csv_data, expected_mapping, sample_field_definitions, tmp_path):
    # Create a temporary CSV file
    csv_file = tmp_path / "test.csv"
    with open(csv_file, "w", newline="") as f:
        if csv_data:
            writer = utils.csv_tools.csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)

    # Call the function
    result = utils.csv_tools.ai_map_columns(str(csv_file), sample_field_definitions)

    # Assertions
    assert result.keys() == expected_mapping.keys()

    for key, expected_value in expected_mapping.items():
        assert key in result
        assert result[key]["type"] == expected_value["type"]

        if expected_value["type"] == "match":
            assert result[key]["input"] == expected_value["input"]
        elif expected_value["type"] == "complex":
            assert result[key]["inputs"] == expected_value["inputs"]

# New tests for convert_and_store_data

@pytest.fixture(scope="function")
def setup_db(tmp_path):
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_path}/test.db'
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()

def test_convert_and_store_data_successful_conversion(setup_db, tmp_path, sample_field_definitions):
    # Create a temporary CSV file with sample data
    csv_file = tmp_path / "test_convert.csv"
    csv_data = [
        {"Website": "https://example.com", "Category": "Tech", "Ad URL": "https://example.com/ads"},
        {"Website": "https://another.com", "Category": "Finance", "Ad URL": "https://another.com/ads"}
    ]
    with open(csv_file, "w", newline="") as f:
        writer = utils.csv_tools.csv.DictWriter(f, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)

    # Mock ai_map_columns to return a predefined mapping
    mock_mapping = {
        "website_url": {"type": "match", "input": "Website"},
        "niche_category": {"type": "match", "input": "Category"},
        "ads_url": {"type": "match", "input": "Ad URL"},
        "first_name": {"type": "missing"},
        "last_name": {"type": "missing"},
        "employees": {"type": "missing"},
        "revenue": {"type": "missing"}
    }
    with patch('utils.csv_tools.ai_map_columns', return_value=mock_mapping):
        # Call the function
        utils.csv_tools.convert_and_store_data(str(csv_file), sample_field_definitions)

        # Assertions
        with app.app_context():
            leads = Lead.query.all()
            assert len(leads) == 2

            lead1_data = {d.field_name: d.field_value for d in leads[0].data}
            lead2_data = {d.field_name: d.field_value for d in leads[1].data}

            assert lead1_data["website_url"] == "https://example.com"
            assert lead1_data["niche_category"] == "Tech"
            assert lead1_data["ads_url"] == "https://example.com/ads"

            assert lead2_data["website_url"] == "https://another.com"
            assert lead2_data["niche_category"] == "Finance"
            assert lead2_data["ads_url"] == "https://another.com/ads"

def test_convert_and_store_data_ignore_non_match_mappings(setup_db, tmp_path, sample_field_definitions):
    # Create a temporary CSV file
    csv_file = tmp_path / "test_ignore_non_match.csv"
    csv_data = [{"Full Name": "John Doe", "Website": "https://example.com"}]
    with open(csv_file, "w", newline="") as f:
        writer = utils.csv_tools.csv.DictWriter(f, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)

    # Mock ai_map_columns to return a mapping with non-match types
    mock_mapping = {
        "website_url": {"type": "match", "input": "Website"},
        "first_name": {"type": "complex", "inputs": ["Full Name"]},
        "last_name": {"type": "complex", "inputs": ["Full Name"]},
        "niche_category": {"type": "missing"},
        "ads_url": {"type": "missing"},
        "employees": {"type": "missing"},
        "revenue": {"type": "missing"}
    }
    with patch('utils.csv_tools.ai_map_columns', return_value=mock_mapping):
        # Call the function
        utils.csv_tools.convert_and_store_data(str(csv_file), sample_field_definitions)

        # Assertions
        with app.app_context():
            leads = Lead.query.all()
            assert len(leads) == 1

            lead_data = {d.field_name: d.field_value for d in leads[0].data}
            assert lead_data["website_url"] == "https://example.com"
            assert "first_name" not in lead_data
            assert "last_name" not in lead_data

def test_convert_and_store_data_duplicate_website_url(setup_db, tmp_path, sample_field_definitions):
    # Create a temporary CSV file with duplicate website URLs
    csv_file = tmp_path / "test_duplicate.csv"
    csv_data = [
        {"Website": "https://example.com", "Category": "Tech"},
        {"Website": "https://example.com", "Category": "Finance"}
    ]
    with open(csv_file, "w", newline="") as f:
        writer = utils.csv_tools.csv.DictWriter(f, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)

    # Mock ai_map_columns to return a simple mapping
    mock_mapping = {
        "website_url": {"type": "match", "input": "Website"},
        "niche_category": {"type": "match", "input": "Category"},
        "first_name": {"type": "missing"},
        "last_name": {"type": "missing"},
        "ads_url": {"type": "missing"},
        "employees": {"type": "missing"},
        "revenue": {"type": "missing"}
    }
    with patch('utils.csv_tools.ai_map_columns', return_value=mock_mapping):
        # Call the function
        utils.csv_tools.convert_and_store_data(str(csv_file), sample_field_definitions)

        # Assertions
        with app.app_context():
            leads = Lead.query.all()
            # Ensure only one lead is created
            assert len(leads) == 2

def test_convert_and_store_data_missing_data(setup_db, tmp_path, sample_field_definitions):
    # Create a temporary CSV file with missing data
    csv_file = tmp_path / "test_missing.csv"
    csv_data = [
        {"Website": "https://example.com", "Category": "Tech"},
        {"Website": "https://another.com"}
    ]
    with open(csv_file, "w", newline="") as f:
        writer = utils.csv_tools.csv.DictWriter(f, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)

    # Mock ai_map_columns to return a simple mapping
    mock_mapping = {
        "website_url": {"type": "match", "input": "Website"},
        "niche_category": {"type": "match", "input": "Category"},
        "first_name": {"type": "missing"},
        "last_name": {"type": "missing"},
        "ads_url": {"type": "missing"},
        "employees": {"type": "missing"},
        "revenue": {"type": "missing"}
    }
    with patch('utils.csv_tools.ai_map_columns', return_value=mock_mapping):
        # Call the function
        utils.csv_tools.convert_and_store_data(str(csv_file), sample_field_definitions)

        # Assertions
        with app.app_context():
            leads = Lead.query.all()
            assert len(leads) == 2

            lead1_data = {d.field_name: d.field_value for d in leads[0].data}
            lead2_data = {d.field_name: d.field_value for d in leads[1].data}

            assert lead1_data["website_url"] == "https://example.com"
            assert lead1_data["niche_category"] == "Tech"

            assert lead2_data["website_url"] == "https://another.com"
            assert "niche_category" not in lead2_data

# New test for complex name splitting in ai_map_columns
def test_ai_map_columns_complex_name_splitting(setup_db, tmp_path, sample_field_definitions):
    # Test case: Complex mapping for name splitting
    csv_file = tmp_path / "test_complex_name.csv"
    csv_data = [
        {"Full Name": "John Doe", "Website": "https://example.com"},
        {"Full Name": "Jane Smith", "Website": "https://another.com"}
    ]
    with open(csv_file, "w", newline="") as f:
        writer = utils.csv_tools.csv.DictWriter(f, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)

    # Call ai_map_columns
    result = utils.csv_tools.ai_map_columns(str(csv_file), sample_field_definitions)

    # Assertions
    assert "first_name" in result
    assert "last_name" in result
    assert result["first_name"]["type"] == "complex"
    assert result["last_name"]["type"] == "complex"
    assert result["first_name"]["inputs"] == ["Full Name"]
    assert result["last_name"]["inputs"] == ["Full Name"]
    assert "logic prompt" in result["first_name"]
    assert "logic prompt" in result["last_name"]

# New test for error handling in ai_map_columns
@patch('utils.csv_tools.genai.GenerativeModel')
def test_ai_map_columns_error_handling(mock_generative_model, setup_db, tmp_path, sample_field_definitions):
    # Mock the AI model to simulate an error
    mock_response = MagicMock()
    mock_response.text = "Invalid JSON response"  # Simulate an invalid JSON response
    mock_generative_model.return_value.generate_content.return_value = mock_response

    # Create a temporary CSV file
    csv_file = tmp_path / "test_error_handling.csv"
    csv_data = [{"Full Name": "John Doe", "Website": "https://example.com"}]
    with open(csv_file, "w", newline="") as f:
        writer = utils.csv_tools.csv.DictWriter(f, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)

    # Call ai_map_columns and expect a ValueError
    with pytest.raises(ValueError) as excinfo:
        utils.csv_tools.ai_map_columns(str(csv_file), sample_field_definitions)

    # Assert that the error message is as expected
    assert "AI returned invalid JSON" in str(excinfo.value)

# New test for various data types in convert_and_store_data
def test_convert_and_store_data_various_data_types(setup_db, tmp_path, sample_field_definitions):
    # Create a temporary CSV file with various data types
    csv_file = tmp_path / "test_data_types.csv"
    csv_data = [
        {"Website": "https://example.com", "Category": "Tech", "Employees": "50", "Revenue": "1000000.50"},
        {"Website": "https://another.com", "Category": "Finance", "Employees": "100", "Revenue": "2000000"}
    ]
    with open(csv_file, "w", newline="") as f:
        writer = utils.csv_tools.csv.DictWriter(f, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)

    # Mock ai_map_columns to return a mapping for these fields
    mock_mapping = {
        "website_url": {"type": "match", "input": "Website"},
        "niche_category": {"type": "match", "input": "Category"},
        "employees": {"type": "match", "input": "Employees"},
        "revenue": {"type": "match", "input": "Revenue"},
        "first_name": {"type": "missing"},
        "last_name": {"type": "missing"},
        "ads_url": {"type": "missing"}
    }
    with patch('utils.csv_tools.ai_map_columns', return_value=mock_mapping):
        # Call convert_and_store_data
        utils.csv_tools.convert_and_store_data(str(csv_file), sample_field_definitions)

        # Assertions
        with app.app_context():
            leads = Lead.query.all()
            assert len(leads) == 2

            lead1_data = {d.field_name: d.field_value for d in leads[0].data}
            lead2_data = {d.field_name: d.field_value for d in leads[1].data}

            assert lead1_data["employees"] == "50"
            assert lead1_data["revenue"] == "1000000.50"
            assert lead2_data["employees"] == "100"
            assert lead2_data["revenue"] == "2000000"

# New test for edge cases in convert_and_store_data
def test_convert_and_store_data_edge_cases(setup_db, tmp_path, sample_field_definitions):
    # Create a temporary CSV file with edge case data
    csv_file = tmp_path / "test_edge_cases.csv"
    csv_data = [
        {"Website": "https://example.com", "Category": "", "Employees": "0"},
        {"Website": "https://another.com", "Category": "Special & Characters", "Employees": "-1"}
    ]
    with open(csv_file, "w", newline="") as f:
        writer = utils.csv_tools.csv.DictWriter(f, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)

    # Mock ai_map_columns to return a mapping for these fields
    mock_mapping = {
        "website_url": {"type": "match", "input": "Website"},
        "niche_category": {"type": "match", "input": "Category"},
        "employees": {"type": "match", "input": "Employees"},
        "first_name": {"type": "missing"},
        "last_name": {"type": "missing"},
        "ads_url": {"type": "missing"},
        "revenue": {"type": "missing"}
    }
    with patch('utils.csv_tools.ai_map_columns', return_value=mock_mapping):
        # Call convert_and_store_data
        utils.csv_tools.convert_and_store_data(str(csv_file), sample_field_definitions)

        # Assertions
        with app.app_context():
            leads = Lead.query.all()
            assert len(leads) == 2

            lead1_data = {d.field_name: d.field_value for d in leads[0].data}
            lead2_data = {d.field_name: d.field_value for d in leads[1].data}

            assert lead1_data["niche_category"] == ""  # Empty string
            assert lead1_data["employees"] == "0"  # Zero value
            assert lead2_data["niche_category"] == "Special & Characters"  # Special characters
            assert lead2_data["employees"] == "-1"  # Negative value
