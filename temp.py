from main import app
from models import db, Company, StructuredLead, Lead

def check_database_counts():
    with app.app_context():
        # Count all types of records
        structured_leads_count = StructuredLead.query.count()
        companies_count = Company.query.count()
        old_leads_count = Lead.query.count()
        
        print("\n=== Database Record Counts ===")
        print(f"Structured Leads: {structured_leads_count}")
        print(f"Companies: {companies_count}")
        print(f"Old Leads: {old_leads_count}")
        print("=============================\n")

if __name__ == "__main__":
    check_database_counts()
