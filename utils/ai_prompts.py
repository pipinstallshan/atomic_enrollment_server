"""
This module contains functions for generating AI prompts used in the application.
"""
import json


def create_prompt_for_object_detection(image_path: str) -> str:
    """
    Generates a prompt for detecting the object in an image.

    Args:
        image_path: The path to the image.

    Returns:
        The generated prompt.
    """
    prompt = f"""
        Return bounding boxes as a JSON array with labels. Never return masks or code fencing. Limit to 1 object.
        You need to return the 2d bounding boxes of the element we want to click.

        I want you to first think about the image and about the searched object. 
        Then you output the json using:
        ```json
        [
           {{...}}
        ]
        ```
          """
    return prompt

def create_prompt_for_popup_detection() -> str:
    """
    Generates a prompt for detecting pop-ups in a webpage screenshot.

    Returns:
        The generated prompt.
    """
    prompt = """Your job is to classify the image of the website into one of three categories.
We are trying to capture a clean screenshot of an actual website.

Either
1. it's a clear screenshot that shows the website
2. It's a correct screenshot of the website, but there is a pop-up or similar that we should close to get a better screenshot
3. The screenshot is completely unusable (eg. 404 errors, blocked site, cloudflare verification check etc.)

you can first think about the screenshot you see.
Then at the end you output either "CLEAR SCREENSHOT", "CLOSE POP-UP" or "UNUSABLE"."""
    return prompt


def create_prompt_for_column_mapping(raw_data_list: list[dict], fields: list[dict]) -> str:
    """
    Creates a prompt that can be used to prompt an LLM to map input CSV columns to output columns.

    Args:
        raw_data_list: List of dictionaries containing the raw CSV data
        fields: List of field definitions
        
    Returns:
        str: The generated prompt
    """
    # Get field definitions
    output_columns = [f['name'] for f in fields]

    # Get input columns
    input_columns = list(raw_data_list[0].keys())

    # Create the prompt
    prompt = f"""
You are an expert data analyst. Your task is to determine the correct mapping between input CSV columns and the predefined output columns.

Input Columns:
{json.dumps(input_columns, indent=2)}

Output Columns:
{json.dumps(output_columns, indent=2)}

Instructions:
1. Analyze the input columns and map them to the output columns.
2. You may assign null to any output column if no relevant input column exists.
3. Do not need to use all input columns; only map the matching ones.
""" + """
Return a list of JSON objects as specified.
Possible types:
{"type": "match", "Output": "column name", "Input":"column name"}
{"type": "no match", "Input": "column name"}
{"type": "missing", "Output": "column name"}
{"type": "complex", "Input": ["column name 1", "column name 2"], "Output": ["column name 3", "column name 4"], "logic prompt": "explaination of how the data should be transfered if a simple column match is not possible."}

For "complex" mappings, always include the "Output" key as an array, even if there's only one output column.

The complex type should only be used for splitting names.

Example 1:
Input Columns: ["Full Name", "Website", "Ad URL", "employees"]
Output Columns: ["name", "website_url", "ads_url", "revenue"]

Your Ouput:
[
{"type": "match", "Input":"Full Name", "Output": "name"},
{"type": "match", "Input":"Website", "Output": "website_url"},
{"type": "match", "Input":"Ad URL", "Output": "ads_url"},
{"type": "no match", "Input": "revenue"},
{"type": "missing", "Output": "employees"}
]

Example 2:
Input Columns: ["Full Name", "profit", "expenses"]
Output Columns: ["first name", "last name", "revenue"]

Your Ouput:
[
{"type": "complex", "Input": ["Full Name"], "Outputs": ["first name", "last name"], "logic prompt": "Split the  \\"Full Name\\" into 'first name' and 'last name' in the most appropriate way possible.\\nExample: input: {\\"Full Name\\": \\"John Doe\\"}\\nExample Output: {\\"first name\\": \\"John\\", \\"last name\\": \\"Doe\\"}"},
{"type": "missing", "Output": "revenue"},
{"type": "no match", "Output": "profit"},
{"type": "no match", "Output": "expenses"},
]

Provide the mapping for the given input and output columns. Return only the JSON object without any introduction or explanation.
"""+ f"""
Input Columns:
{json.dumps(input_columns, indent=2)}

Output Columns:
{json.dumps(output_columns, indent=2)}
"""
    return prompt

def create_prompt_for_csv_tools_test() -> str:
    """
    Generates a prompt for testing the csv tools.

    Returns:
        The generated prompt.
    """
    prompt = """
        Return bounding boxes as a JSON array with labels. Never return masks or code fencing. Limit to 1 object.
        You need to return the 2d bounding boxes of the element we want to click.

        I want you to first think about the image and about the searched object. 
        Then you output the json using:
        ```json
        [
           {...}
        ]
        ```
          """
    return prompt

def create_prompt_for_loading_data(input: str, output_rules: str) -> str:
    return f"""Your job is to extract the available Leads information into a uniform format into a json. As part of this you can and should format the data.

## Examples
### Exaple 1
Input:
```
{{"name": "friedrich wichtinger", "mail address": "fridi@gmail.com", "Job": "CEO@Sterling Station}}
```
Expected data structure and formating rules:
- first_name: Title Case
- last_name: Title Case
- title: Title Case (company title)
- email: Lowercase, valid email
- phone: valid phone number with country code (use '+1' by default if it looks like a NA number)
- linkedin_url URL: valid url
Output:
```json
{{
    "first_name": "Friedrich",
    "last_name": "Wichtinger",
    "title": "CEO",
    "email": "fridi@gmail.com",
    "phone": null,
    "linkedin_url": null
}}
```

### Exaple 2
Input:
```
contact person: Mr. jOhN dOe, email: John.Doe@example.COM,  phone: 123-456-7890, linkedin: linkedin.com/in/johndoe, company:  Acme Corp.
```
Expected data structure and formating rules:
- first_name: Title Case
- last_name: Title Case
- title: Title Case (company title)
- email: Lowercase, valid email
- gender: Enum[male, female, other]
- phone: valid phone number with country code (use '+1' by default if it looks like a NA number)
- linkedin_url URL: valid url
Output:
```json
{{
    "first_name": "John",
    "last_name": "Doe",
    "title": null,
    "email": "john.doe@example.com",
    "gender": "male",
    "phone": "+11234567890",
    "linkedin_url": "https://linkedin.com/in/johndoe"
}}
```

### Exaple 3
Input:
```
Lead Info: Name is  Ms. jane  smiTH III,  Contact email:  Jane.Smith @company.net,  Mobile: +44 20 7946 0958,  LinkedIn profile:  linkedin.com, 
```
Expected data structure and formating rules:
- name: Title Case
- phone: valid phone number with country code (use '+1' by default if it looks like a NA number)
- linkedin_url URL: valid url
Output:
```json
{{
    "name": "Jane Smith III",
    "phone": "+442079460958",
    "linkedin_url": null
}}
```

### Exaple 4
Input:
```
```
Expected data structure and formating rules:
- full_name: Title Case
- phone_number: valid phone number with country code (use '+1' by default if it looks like a NA number)
- linkedin_url URL: valid url
Output:
```json
{{
    "full_name": null,
    "phone_number": null,
    "linkedin_url": null
}}
```

### Exaple 5
Input:
```
Company data: company-name: Acme Corp; website = example.com. Niche: tech,  yes-ads. ads url- fb.com/acme,  youtube custom video: youtube.com/acmecorp
```
Expected data structure and formating rules:
- name: Title Case
- website_url: valid url
- niche_category: Enum[tech, finance, health]
- is_running_ads: Enum[Yes, No, Unknown]
- ads_url: valid url
- custom_youtube_video: valid url
Output:
```json
{{
    "name": "Acme Corp",
    "website_url": "https://example.com",
    "niche_category": "tech",
    "is_running_ads": "Yes",
    "ads_url": "https://fb.com/acme",
    "custom_youtube_video": "https://youtube.com/acmecorp"
}}
```

### Exaple 6
Input:
```
Company data: https://airstreams-media.com
```
Expected data structure and formating rules:
- name: Title Case, not nullable (not nullable)
- website_url: valid url, not nullable
- niche_category: Enum[tech, finance, health, other]
- is_running_ads: bool; Enum[true, false] (not nullable; false by default)
- ads_url: valid url

Output:
```json
{{
    "name": "Airstreams Media",
    "website_url": "https://airstreams-media.com",
    "niche_category": "other",
    "is_running_ads": false,
    "ads_url": null
}}
```







## Implementation
Input:
```
{input}
```
Expected data structure and formating rules:
{output_rules}

Output:
    """
