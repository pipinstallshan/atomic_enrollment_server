import time
from utils.csv_tools import get_field_definitions
from models import db, StructuredLead, Company, ProcessingTask
from urllib.parse import urlparse
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from utils.csv_tools import ai_map_columns, csv_to_json_list
from sqlalchemy import func
from automation_manager import start_render_and_upload_if_not_exist
import logging
import asyncio

# Get logger for this module
logger = logging.getLogger(__name__)

def normalize_url(url: str | None) -> str | None:
    """
    Normalizes a URL to increase matching accuracy.
    Removes 'www.', 'http://', 'https://' and trailing slashes.
    Returns None if url is None.
    
    Example:
        'https://www.example.com/' -> 'example.com'
    """
    if url is None:
        return None
    
    try:
        # Parse the URL
        parsed = urlparse(url)
        # Get the netloc (domain) and remove 'www.'
        domain = parsed.netloc.replace('www.', '')
        # Remove trailing dots and convert to lowercase
        domain = domain.rstrip('.').lower()
        return domain
    except Exception:
        # If URL parsing fails, return the original URL
        return url

async def process_csv_file_async(csv_filepath: str):
    """
    Process a single CSV file, map columns, and add leads to the database.
    Uses async processing to handle company creation in parallel.
    Each import is tagged with a unique batch tag: 'import-batch DD-MM-YYYY/N',
    where N is the batch number for that day.
    """
    # Get today's date in 'DD-MM-YYYY' format
    today_str = datetime.now().strftime('%d-%m-%Y')

    # Determine the current batch number (N) for today
    current_batch_count = (
        db.session.query(func.count(func.distinct(StructuredLead.tags)))
        .filter(
            StructuredLead.tags.like(f'import-batch {today_str}/%')
        )
        .scalar()
    )

    # The next batch is N=current_batch_count
    batch_index = current_batch_count

    # Create the tag for this batch
    batch_tag = f'import-batch {today_str}/{batch_index}'

    # Convert the CSV into a list of dictionaries
    list_of_dicts = csv_to_json_list(csv_filepath)

    # Filter out rows with insufficient data
    valid_rows = []
    skipped_rows = []

    for row in list_of_dicts:
        if len("".join(row.values())) >= 20:
            valid_rows.append(row)
        else:
            skipped_rows.append(row)

    # Process company creation in parallel using async
    start_time = time.time()
    company_tasks = []
    for row in valid_rows:
        company_tasks.append(Company.create_with_ai_async(str(row)))
    
    # Wait for all company creation tasks to complete
    companies = await asyncio.gather(*company_tasks)
    print(f"Time taken to create companies: {time.time() - start_time} seconds")
    # Process company duplicates and get company IDs
    company_ids = []
    valid_companies = []
    valid_indices = []
    
    for i, company in enumerate(companies):
        row = valid_rows[i]
        
        # Add the batch tag to the company
        company.tags = batch_tag

        # Handle potential duplicates, prefer existing company
        other_company = company.look_for_duplicate()
        if not other_company:
            db.session.add(company)
            try:
                db.session.flush()  # Get the ID
                company_id = company.id
                company_ids.append(company_id)
                valid_companies.append(company)
                valid_indices.append(i)
                start_render_and_upload_if_not_exist(company_id)
            except Exception as e:
                logger.error(f"Error flushing session for row: {row}, company: {company.dict()}. Exception: {e}", exc_info=True)
                # ignore this lead
                db.session.rollback()
                continue  # Skip this lead
        else:
            # TODO: maybe merge the company infos
            company_id = other_company.id
            company_ids.append(company_id)
            valid_companies.append(company)
            valid_indices.append(i)
            start_render_and_upload_if_not_exist(company_id)
    
    # Now process leads in parallel
    lead_tasks = []
    for i in valid_indices:
        row = valid_rows[i]
        lead_tasks.append(StructuredLead.create_using_ai_async(str(row)))
    
    # Wait for all lead creation tasks to complete
    structured_leads = await asyncio.gather(*lead_tasks)
    
    # Process lead duplicates and finalize
    leads_processed = 0
    leads_skipped = 0
    
    for i, structured_lead in enumerate(structured_leads):
        leads_processed += 1
        idx = valid_indices[i]
        company_id = company_ids[i]
        
        # Set company ID and batch tag
        structured_lead.company_id = company_id
        structured_lead.tags = batch_tag

        # Handle potential duplicate leads, prefer existing
        other_lead = structured_lead.look_for_duplicate()
        if not other_lead:
            db.session.add(structured_lead)
            try:
                db.session.flush()  # Get the ID
            except Exception as e:
                logger.error(f"Error flushing session for lead: {structured_lead.dict()}. Exception: {e}", exc_info=True)
                # ignore this lead
                db.session.rollback()
                continue  # Skip this lead
        else:
            # Skip if duplicate exists
            leads_skipped += 1
            continue  # skip this lead

    # Commit all changes at once
    db.session.commit()

    return leads_processed, leads_skipped, batch_tag, skipped_rows

def process_csv_file(csv_filepath: str):
    """
    Process a single CSV file, map columns, and add leads to the database.
    Each import is tagged with a unique batch tag: 'import-batch DD-MM-YYYY/N',
    where N is the batch number for that day.
    
    This function is a synchronous wrapper around the async version.
    """
    return asyncio.run(process_csv_file_async(csv_filepath))


