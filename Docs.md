# Vid Automation Project Documentation

## Project Overview

This project is an AI/Automation-powered database/CSV manager designed for salespeople. It allows users to:

1. **Import Lead Data**: Users can dump their existing leads from CSV files with any structure
2. **Automated Enrichment**: The system uses AI and automation to enrich lead data:
   - Split names into first/last
   - Find email addresses
   - Generate personalized videos
   - More enrichments can be easily added
3. **Flexible Data Storage**: All data is stored flexibly, allowing for:
   - Any CSV structure to be imported
   - New fields to be added dynamically
   - Tracking of enrichment sources
4. **Processing Management**: The system manages various automated tasks:
   - Video rendering
   - Data enrichment
   - Status tracking
   - Multi-instance processing

The goal is to provide salespeople with a powerful tool that automates repetitive tasks and enriches their lead data using AI and automation, while maintaining flexibility in data structure.

## Code Structure and Functionality

### Database Schema

The project uses SQLite with SQLAlchemy, implementing a flexible schema:

1. `Lead` table:
   - Core lead entry
   - Stores only essential metadata (ID, timestamps, source)
   - All actual data is stored flexibly in LeadData

2. `LeadData` table:
   - Stores any field (first_name, email, etc.)
   - Tracks if data was enriched by AI/automation
   - Tracks which enrichment added the data
   - Can easily add new fields without schema changes

3. `ProcessingTask` table:
   - Tracks all processing/automation tasks
   - For video rendering, email finding, etc.
   - Stores status, instance ID, result data
   - One lead can have multiple tasks

### Key Files

#### `main.py`
Flask application that provides the web interface for:
- CSV file uploads
- YouTube account management
- CSV exports
- Authentication
- **Leads Overview**

#### `csv_parser.py`
Handles the processing of uploaded CSV files:
- Uses AI to extract relevant information
- Creates Lead and LeadData entries
- Initializes ProcessingTasks for video rendering
- Prevents duplicate entries using normalized URLs

#### `video_renderer.py`
Continuous processing script that:
- Picks up pending ProcessingTasks
- Takes screenshots of websites
- Renders videos according to configurations
- Updates task status and stores results

#### `models.py`
Defines the database schema and provides utility methods for:
- Flexible data storage
- Task management
- User authentication
- YouTube integration

### Configuration Files

#### `config.py`
Contains video rendering configurations:
- Different video types (money coaching, skills program)
- Video segment specifications
- Resolution settings
- Default configurations

### Utility Modules

#### `utils/render.py`
Handles video rendering:
- Processes different types of video segments
- Applies effects and transitions
- Manages video composition

#### `utils/browser_tools.py`
Provides web automation functionality:
- Takes screenshots of websites
- Handles pop-ups using AI

#### `utils/csv_tools.py`
Processes CSV data:
- Uses AI to extract information
- Normalizes data format
- Handles various CSV structures
- **`ai_get_links` function:**
    - Takes a CSV file path and a list of field definitions as input.
    - Uses the Gemini AI to intelligently map input CSV columns to predefined output columns.
    - Handles different mapping types: "match", "no match", "missing", and "complex".
    - Returns a dictionary representing the mapping.
- **`get_field_definitions` function:**
    - Retrieves all field definitions from the database.

## Usage Instructions

1. **Setting Up**:
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Create initial user
   python create_user.py <username> <email> <password>
   ```

2. **Running the Application**:
   ```bash
   # Start the web interface
   python main.py
   
   # Start the video renderer (in a separate terminal)
   python video_renderer.py
   ```

3. **Using the System**:
   - Log in through the web interface
   - Upload CSV files with lead data
   - Connect YouTube accounts if needed
   - Monitor processing status
   - Export processed data

## Leads Overview Page

The "Leads Overview" page provides a comprehensive view of all leads in the system. It displays lead data in a tabular format with the following features:

- **Dynamic Columns:** The table automatically includes all columns defined in the `FieldDefinition` table, allowing for flexibility as new fields are added.
- **Column Ordering:** Columns are displayed in a specific order:
    1. `company_name`, `first_name`, `last_name`
    2. Other data columns in a predefined order: `website_url`, `ads_url`, `niche_category`, `email`, `phone`, `linkedin`, `revenue`, `employees`
    3. Any new data columns added in the future will appear after the predefined data columns.
    4. Metadata columns: `created_at`, `updated_at`, `source`
    5. Task-related columns: `task_status`, `task_updated_at`
- **Missing Data:** Missing data is represented by empty cells in the table.
- **Styling:** The table's styling matches the overall website's design.
- **Sorting:** Users can sort the table by any column by clicking on the column header. Clicking a header again reverses the sort order. This functionality is implemented using the DataTables JavaScript library.
- **Accessibility:** The page is accessible via the "Leads" link in the navigation bar.

## Development Notes

### Adding New Enrichments

To add a new enrichment type:
1. Create a new task type in ProcessingTask
2. Implement the enrichment logic
3. Update the relevant processor to handle the new task type
4. Add any necessary UI elements

### Database Operations

The flexible schema allows for:
- Adding new fields without migrations
- Tracking data sources and enrichments
- Multiple processing tasks per lead
- Easy querying of enriched vs. original data

### Error Handling

- Failed tasks are marked and can be retried
- Stuck tasks (in_progress > 1 hour) are automatically reset
- All errors are logged with detailed information

## Future Enhancements

Planned features include:
- More AI-powered enrichments
- Additional data source integrations
- Advanced querying and filtering
- Bulk operations and automation rules
- API access for external integration

## Notes

- The system is designed to be scalable and flexible
- New enrichment types can be added without schema changes
- The database structure supports future AI/automation features
- Multiple instances can process tasks concurrently
