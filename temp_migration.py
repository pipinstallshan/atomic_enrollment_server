#!/usr/bin/env python
"""
Migration script to add import batch tags to companies that don't have them.

This script:
1. Queries all companies in the database
2. Checks each company for an existing import batch tag
3. For companies without an import batch tag, adds one based on their creation date
   in the format "import-batch DD-MM-YYYY/0"

Run this script with:
```
python temp_migration.py
```
"""

from main import app
from models import db, Company
import re
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def has_import_batch_tag(tags):
    """Check if the company already has an import batch tag."""
    if not tags:
        return False
    
    # Pattern to match "import-batch DD-MM-YYYY/N"
    pattern = r'import-batch \d{2}-\d{2}-\d{4}/\d+'
    
    # Check if any of the comma-separated tags match the pattern
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',')]
        for tag in tag_list:
            if re.match(pattern, tag):
                return True
    
    return False

def add_import_batch_tags():
    """Add import batch tags to companies that don't have them."""
    with app.app_context():
        # Get all companies
        companies = Company.query.all()
        logger.info(f"Found {len(companies)} companies in total")
        
        # Counter for companies that need tags
        updated_count = 0
        already_tagged_count = 0
        
        # Process each company
        for company in companies:
            # Skip if company already has an import batch tag
            if has_import_batch_tag(company.tags):
                already_tagged_count += 1
                continue
            
            # Get creation date and format it
            if company.created_at:
                date_str = company.created_at.strftime('%d-%m-%Y')
            else:
                # Use current date if created_at is None (shouldn't happen, but just in case)
                date_str = datetime.utcnow().strftime('%d-%m-%Y')
            
            # Create the new tag
            new_tag = f"import-batch {date_str}/0"
            
            # Add the tag to the company
            if company.tags:
                company.tags = f"{company.tags},{new_tag}"
            else:
                company.tags = new_tag
            
            updated_count += 1
            
            # Log every 100 companies for visibility
            if updated_count % 100 == 0:
                logger.info(f"Processed {updated_count} companies so far")
        
        # Commit all changes to the database
        db.session.commit()
        
        logger.info(f"Migration complete. Added tags to {updated_count} companies.")
        logger.info(f"{already_tagged_count} companies already had import batch tags.")

if __name__ == "__main__":
    logger.info("Starting migration to add import batch tags to companies")
    add_import_batch_tags()
    logger.info("Migration completed successfully")
