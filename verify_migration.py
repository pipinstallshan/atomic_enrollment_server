from models import db, Company, StructuredLead

def print_companies_and_leads():
    """Prints the first 10 companies and their connected Structured Leads."""

    with db.session() as session:  # Use a session for the database interaction
        companies = session.query(Company).limit(10).all()

        for company in companies:
            print(f"Company: {company.name} (ID: {company.id}, Website: {company.website_url})")
            leads = company.leads
            if leads:
                print("  Structured Leads:")
                for lead in leads:
                    print(f"    - {lead.first_name} {lead.last_name} (Email: {lead.email})")
            else:
                print("  No Structured Leads found.")
            print("-" * 30)

if __name__ == '__main__':
    from main import app  # Import your Flask app instance
    with app.app_context():  # Establish an application context.
        print_companies_and_leads()
