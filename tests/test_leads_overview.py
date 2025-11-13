import unittest
from main import app
from models import db, Lead, LeadData, FieldDefinition, ProcessingTask

class TestLeadsOverview(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Tear down test environment."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # Test 1: Page and Navbar (Manual Tests - described in comments)

    # Test: Verify that a new page titled "Leads Overview" exists.
    # Method: Access the website and check for the page's presence and title. (Manual Test)
    # Passing Criteria: The page at /leads-overview should exist and have the title "Leads Overview".

    # Test: Verify that a new navbar entry labeled "Leads" exists.
    # Method: Access the website and check for the navbar entry. (Manual Test)
    # Passing Criteria: A navbar entry labeled "Leads" should be visible and clickable.

    # Test: Verify that clicking the "Leads" navbar entry navigates to the "Leads Overview" page.
    # Method: Click the navbar entry and check the resulting URL and page content. (Manual Test)
    # Passing Criteria: Clicking "Leads" should redirect to /leads-overview and display the correct page.

    # Test 2: Table Structure and Data (Manual and Programmatic Tests)

    # Test: Verify that the table displays the correct columns in the specified order:
    # `company_name`, `first_name`, `last_name`, followed by other data columns (dynamically determined),
    # and finally metadata/task columns (`created_at`, `updated_at`, `source`, `task_status`, `task_updated_at`).
    # Method: Inspect the table headers and compare them to the expected order. (Manual Test)
    # Passing Criteria: Table headers should match the specified order.

    def test_table_displays_all_leads(self):
        """Test that the table displays data for all leads."""
        # Create some sample leads and data
        with app.app_context():
            lead1 = Lead(source='test')
            lead2 = Lead(source='test')
            db.session.add_all([lead1, lead2])
            db.session.commit()

            # Add some LeadData for lead1
            lead_data1 = LeadData(lead_id=lead1.id, field_name='company_name', field_value='Company A')
            lead_data2 = LeadData(lead_id=lead1.id, field_name='website_url', field_value='http://companya.com')
            db.session.add_all([lead_data1, lead_data2])
            db.session.commit()

            # Add a ProcessingTask for lead2
            task1 = ProcessingTask(lead_id=lead2.id, task_type='test_task', status='completed')
            db.session.add(task1)
            db.session.commit()

        # Access the "Leads Overview" page
        response = self.app.get('/leads-overview')
        self.assertEqual(response.status_code, 200)

        # Check if the response data indicates the presence of all leads
        self.assertIn(b'Company A', response.data)
        self.assertIn(b'http://companya.com', response.data)
        self.assertIn(b'completed', response.data)

    # Test: Verify that missing data is represented by empty cells.
    # Method: Inspect table cells corresponding to leads with missing data and check for empty values. (Manual Test)
    # Passing Criteria: Cells with missing data should be empty (not display "None" or "N/A").

    # Test 3: Dynamic Column Handling (Programmatic and Manual Tests)

    def test_new_field_definition_appears_in_table(self):
        """Test that adding a new field definition dynamically adds a column to the table."""
        # Add a new field definition
        with app.app_context():
            new_field = FieldDefinition(name='new_field', display_name='New Field', description='A new field', field_type='text', is_system=False, is_required=False)
            db.session.add(new_field)
            db.session.commit()

        # Access the "Leads Overview" page
        response = self.app.get('/leads-overview')
        self.assertEqual(response.status_code, 200)

        # Check if the new column appears in the table
        self.assertIn(b'New Field', response.data)

    # Test 4: Styling and Sorting (Manual Tests - described in comments)

    # Test: Verify that the table's styling matches the existing website's style.
    # Method: Visually inspect the table and compare it to other elements on the website. (Manual Test)
    # Passing Criteria: The table should have a similar look and feel to other tables or elements on the site.

    # Test: Verify that clicking on a column header sorts the table by that column.
    # Method: Click on different column headers and observe the table's sorting behavior. (Manual Test)
    # Passing Criteria: Clicking a header should sort the table rows based on that column's values.

    # Test: Verify that clicking on a column header a second time reverses the sort order.
    # Method: Click on the same column header twice and observe the table's sorting behavior. (Manual Test)
    # Passing Criteria: Clicking the same header again should reverse the sort order (ascending/descending).

if __name__ == '__main__':
    unittest.main()
