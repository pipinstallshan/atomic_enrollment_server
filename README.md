# Lead Management Web Application

This web application helps salespeople manage and enrich lead data. It allows users to upload CSV files of leads, which are then processed and stored in a flexible database. Key features include:

## Key Features

### AI-Powered CSV Parsing
The app uses AI (Gemini and OpenAI) to intelligently map columns from uploaded CSV files to predefined fields, handling variations in CSV structure. It can also split names and extract information from unstructured text fields.

### Lead and Company Data Storage
It stores lead information in two main tables: Company and StructuredLead, separating company-level data from individual lead details, and auto creates both.

### Automated Video Generation
The system generates personalized videos for leads by taking screenshots of their websites and ads (using Selenium), and then overlaying pre-recorded video clips (using MoviePy) based on configurable templates. It prioritizes video tasks, and supports batch rendering and uploading to Google Drive.

### Google Drive Integration
The app allows connecting Google Drive accounts for storing generated videos and offers direct upload of completed videos, providing shareable links.

### Batch Processing and Task Management
Leads are processed in batches, with a dedicated ProcessingTask model to track the status of various automated tasks (like video rendering and uploading). A separate Task_worker.py script continuously monitors and processes these tasks.

### Leads Overview Page
A web interface page displays all leads and associated data in a sortable table, enabling users to view progress and details. An integrated AI chat allows for interaction with selected leads, including triggering video renders and CSV exports.

### Export Templates
It manages different export templates, using FieldDefinitions, that a user can use for creating CSV files.

### Authentication
It manages different users and roles.


## File Structure

Here's a concise list of the most relevant files and their core responsibilities:
1.  **`main.py`:**
    *   Flask application setup and routing.
    *   Handles user interface for CSV upload, Google Drive account management, lead overview, export template management, and batch management.
    *   Interacts with the database and other modules to process user requests.
    *   Includes error handling and serves files for downloading exports.

2.  **`models.py`:**
    *   Defines the database schema using SQLAlchemy.
    *   Includes models for `User`, `DriveAccount`, `FieldDefinition`, `Lead` (deprecated), `LeadData` (deprecated), `ProcessingTask`, `ExportTemplate`, `Company`, and `StructuredLead`.
    *   Provides methods for database interaction (creating, querying, updating records).
    *   Includes logic for handling duplicates (for companies and leads).
    *   Implements AI-driven data loading and enrichment within model methods.

3.  **`csv_parser.py`:**
    *   Handles the processing of uploaded CSV files.
    *   Uses `utils/csv_tools.py` (and AI) to map CSV columns to database fields.
    *   Creates `Company` and `StructuredLead` records in the database.
    *   Creates initial `ProcessingTask` entries for video rendering.
    *   Manages batch tagging of imported data.
    *   Includes duplicate detection logic to prevent redundant entries.

4.  **`Task_worker.py`:**
    *   Runs as a continuous background process (independent of the web interface).
    *   Queries the database for pending or stuck `ProcessingTask` entries.
    *   Executes tasks:
        *   `video_render`: Calls `utils/render.py` to generate videos.
        *   `upload_video`: Calls `drive_oauth.py` to upload videos to Google Drive.
    *   Updates task status in the database.
    *   Includes error handling and retry logic.

5.  **`utils/render.py`:**
    *   Contains functions for video rendering using the `moviepy` library.
    *   Handles different video segment types (PIP, full-screen, audio-over-image).
    *   Calculates positions for Picture-in-Picture (PIP) elements.
    *   Applies fade-in/fade-out effects and transitions.
    *   Reads video configurations from `config.py`.

6.  **`utils/csv_tools.py`:**
    *    Provides utility functions for working with CSV files.
    *   `ai_map_columns`: Uses AI to map CSV columns to database fields.
    *   `csv_to_json_list`: Converts CSV file content to a list of dictionaries.

7.  **`utils/ai_basic_functions.py`:**
    *    Houses functions that use the AI models.
    *   `ask_question_and_get_boolean_answer()`
    *   `categorize()`
    *   `run_prompt_with_gemini()` and `run_prompt_with_openai()`

8.  **`utils/ai_prompts.py`:**
    *    Contains functions that create the prompts for the AI models.

9.  **`drive_oauth.py` & `drive.py`:**
    *   `drive_oauth.py`: Manages Google Drive OAuth flow, credential storage, and file uploads.
    *   `drive.py`: Flask blueprint providing routes for connecting/disconnecting Drive accounts.

10. **`automation_manager.py`:**
    *   Contains helper functions for managing automation tasks, particularly around video rendering and uploading.
    *   `start_render_and_upload_if_not_exist`:  Initiates video creation for a company, checking for existing tasks.
    *   `get_company_task_statuses`: Retrieves tasks for companies.
    *  `clear_company_tasks`: Deletes tasks associated with a company.

11. **`AI_database_agent.py`:**
     *   Implements the AI agent for the lead overview chat interface.
     *   Defines available tools (functions) for the AI.
     *   Handles conversation flow and calls appropriate functions based on AI responses.

12. **`config.py`:**
      * Holds the video configurations.

13. **`auth.py`:**
     * Manages User Authentication.

14. **`templates/`:**
        *   Contains all HTML templates for the web interface.  `base.html` provides the common layout.  Other templates are specific to individual pages (upload, leads overview, etc.).
        *   Includes Javascript and CSS within the templates.


## Summary
In essence, it combines CSV parsing, AI-driven data enrichment, automated video creation, and Google Drive integration to streamline the lead management process. The Task_worker.py script runs as a separate, continuous background process. The main.py file defines a flask web app.