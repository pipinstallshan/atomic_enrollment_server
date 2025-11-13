from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session, send_file, send_from_directory, abort, current_app
from flask_login import login_required, current_user
import os, sys
import threading
from werkzeug.utils import secure_filename
import csv_parser
from models import init_db, DriveAccount, db, Lead, LeadData, ProcessingTask, FieldDefinition, ExportTemplate, StructuredLead, Company
from auth import init_auth
import logging
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import AI_database_agent
import csv
from sqlalchemy import or_
from drive import drive_bp
from utils.ai_basic_functions import run_prompt_with_gemini
from utils.role_helpers import roles_required


# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]  # Add StreamHandler
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
logger.debug(f"Template folder path: {app.template_folder}")

# Add max and min functions to the Jinja2 environment
app.jinja_env.globals.update(max=max, min=min)

# Create blueprint for main routes
main_bp = Blueprint('main', __name__)

def run_csv_import_in_thread(app, filepath):
    """Worker executed in a detached thread."""
    with app.app_context():
        try:
            csv_parser.process_csv_file(filepath)
            logger.info(f"CSV import completed successfully for file: {filepath}")
        except Exception:
            logger.exception(f"CSV import failed for file: {filepath}")

# Configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key')
app.config['UPLOAD_FOLDER'] = 'data'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = False  # Temporarily disable CSRF
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # Set session lifetime

# Initialize database and authentication
logger.debug("Initializing database...")
init_db(app)
logger.debug("Initializing authentication...")
init_auth(app)

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.before_request
def before_request():
    """Ensure user session is handled correctly."""
    if current_user.is_authenticated:
        session.permanent = True  # Make session permanent
        app.permanent_session_lifetime = timedelta(days=30)


@app.route('/output/<path:filename>')
def serve_file(filename):
    OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    try:
        # Check if the file exists in the output folder
        if os.path.exists(os.path.join(OUTPUT_FOLDER, filename)):
            return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True, download_name="Exported Leads.csv")
        else:
            abort(404)  # File not found
    except Exception as e:
        return f"Error serving file: {str(e)}", 500

@main_bp.route('/debug-info')
def debug_info():
    """Debug route to show application configuration"""
    debug_data = {
        'template_folder': app.template_folder,
        'static_folder': app.static_folder,
        'secret_key_set': bool(app.config.get('SECRET_KEY')),
        'blueprints': list(app.blueprints.keys()),
        'routes': [str(rule) for rule in app.url_map.iter_rules()],
        'session': dict(session)
    }
    return jsonify(debug_data)

@main_bp.route('/')
def index():
    """Redirect root to upload page"""
    logger.debug("Accessing index route")
    if current_user.is_authenticated:
        return redirect(url_for('main.upload_file'))
    return redirect(url_for('auth.login'))

@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@roles_required('uploader', 'admin')  # Both uploaders and admins can access
def upload_file():
    """Handle CSV file uploads"""
    message = None
    if request.method == 'POST':
        if 'file' not in request.files:
            message = 'No file part'
            return render_template('upload.html', message=message)
        
        file = request.files['file']
        
        if file.filename == '':
            message = 'No selected file'
            return render_template('upload.html', message=message)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            
            prompt = f"""
You are a helpful assistant that analyzes a CSV file to determine if all the necessary information is present.
The CSV file is for a list of Leads+Companies.

Each actual entry has to have the information about first name, email, company name, website url and niche or something (like 'BC blue collar', 'coaching' or whatever).
This is just a safety check to make sure the CSV file is not missing any important information.
It is very likely that all the information is present, but we want to be sure.
Other information is not important and can be missing. We just need the basic information (first name, email, company name, website url and niche or something).

If any of this information is missing, you should return write 'MISSING_INFO: explanaition of what is missing' at the end of your response. If no information is missing, return 'ALL_GOOD' at the end.
So now alanlyse critically the csv and write if the information is missing for any Lead. Please explain what is missing if something is missing in understandable form.
Example 1:
Input:
```csv
First Name, Last Name, Email, Company Name, Website URL, Type
John, Doe, john.doe@example.com, Example Inc, https://example.com,na
Jane, Smith,, Example Corp, https://example.com, "coaching"
```
Output:
```
Okay, I will analyze the CSV data to check for missing information in the required fields: FirstName, email, CompanyName, Website Link, and Niche.
Here's the analysis:
* **John Doe** has missing type/niche
* **Jane Smith** has missing email

Example 2:
Input:
```csv
First Name, Last Name, Email, Company Name, Website URL, Type, Phone, LinkedIn URL
Justin, D., justin.doe@example.com, Example Inc, https://example.com, "bc", na, na
Fleur,, fleur.smith@example.com, Example Corp, https://example.com, "construction", na, na
```
Output:
```
Okay, I will analyze the CSV data to check for missing information in the required fields: FirstName, email, CompanyName, Website Link, and Niche.
Here's the analysis:
* **Justin D.** has all basic information
* **Fleur** has all basic information

Conslusion:
ALL_GOOD
```

Now it's your turn.
```csv
{text}
```
So now alanlyse critically the csv and write if the information is missing for any Lead. Please explain what is missing if something is missing .
"""
            response = run_prompt_with_gemini(prompt=prompt)
            if 'MISSING_INFO' in response:
                message = 'Missing information in the CSV file. Please check the file and try again.\n\nFeedback:\n' + response.split('MISSING_INFO')[1][1:]
                return render_template('upload.html', message=message)
            
            # Kick off background processing
            t = threading.Thread(
                target=run_csv_import_in_thread,
                args=(current_app._get_current_object(), filepath),
                daemon=True           # dies with the main process
            )
            t.start()

            message = "File received – processing has started in the background."
            return render_template('upload.html', message=message)
        else:
            message = 'Invalid file type. Please upload a CSV file.'
    
    return render_template('upload.html', message=message)

def allowed_file(filename):
    """Check if the file extension is .csv"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

@main_bp.route('/export')
@login_required
@roles_required('admin')  # Only admins can access export functionality
def list_export_templates():
    """
    Display the list of export templates for the current user.
    """
    user_templates = ExportTemplate.query.filter_by(user_id=current_user.id).all()
    return render_template(
        'export.html', 
        templates=user_templates
    )

@main_bp.route('/export/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin')  # Only admins can create export templates
def create_export_template():
    """
    Create a new export template.
    """
    all_fields = FieldDefinition.query.all()

    if request.method == 'POST':
        template_name = request.form.get('templateName', '').strip()
        columns = request.form.getlist('columns')  # list of selected columns

        if not template_name:
            # In real code, handle error properly, e.g. flash message
            return render_template(
                'create_or_edit_export_template.html',
                heading="Create Export Template",
                button_text="Create",
                template_name=template_name,
                all_fields=all_fields,
                selected_columns=columns
            )

        new_template = ExportTemplate(
            user_id=current_user.id,
            name=template_name,
        )
        new_template.set_columns(columns)
        db.session.add(new_template)
        db.session.commit()

        return redirect(url_for('main.list_export_templates'))

    return render_template(
        'create_or_edit_export_template.html',
        heading="Create Export Template",
        button_text="Create",
        template_name='',
        all_fields=all_fields,
        selected_columns=[]
    )

@main_bp.route('/export/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_export_template(template_id: int):
    """
    Edit an existing export template by ID.
    """
    template = ExportTemplate.query.filter_by(
        id=template_id, user_id=current_user.id
    ).first_or_404()

    all_fields = FieldDefinition.query.all()

    if request.method == 'POST':
        template_name = request.form.get('templateName', '').strip()
        columns = request.form.getlist('columns')

        template.name = template_name
        template.set_columns(columns)
        template.updated_at = datetime.utcnow()
        db.session.commit()

        return redirect(url_for('main.list_export_templates'))

    return render_template(
        'create_or_edit_export_template.html',
        heading="Edit Export Template",
        button_text="Save",
        template_name=template.name,
        all_fields=all_fields,
        selected_columns=template.get_columns()
    )

@main_bp.route('/export/templates/<int:template_id>', methods=['DELETE'])
@login_required
@roles_required('admin')  # Only admins can delete export templates
def delete_export_template(template_id: int):
    """
    Delete an export template by ID.
    """
    template = ExportTemplate.query.filter_by(
        id=template_id, user_id=current_user.id
    ).first()
    if not template:
        return jsonify({'error': 'Template not found'}), 404

    db.session.delete(template)
    db.session.commit()
    return jsonify({'status': 'deleted'}), 200

@main_bp.route('/export/do', methods=['POST'])
@login_required
@roles_required('admin')  # Only admins can perform exports
def do_export():
    """
    Placeholder route to initiate the actual export with a chosen template and list of leads.
    The real CSV generation will be implemented later.
    """
    data = request.json or {}
    template_id = data.get('template_id')
    lead_ids = data.get('lead_ids', [])

    # Just a placeholder: we can log or store a Task to export the leads.
    logger.info(f"User {current_user.id} wants to export leads {lead_ids} with template {template_id}")
    return jsonify({'status': 'ok', 'message': 'Export initiated (placeholder)'}), 200

@main_bp.route('/api/export/templates', methods=['GET'])
@login_required
@roles_required('admin')  # Only admins can access export template API
def api_list_export_templates():
    """
    Return the list of export templates as JSON.
    """
    user_templates = ExportTemplate.query.filter_by(user_id=current_user.id).all()
    results = []
    for t in user_templates:
        results.append({
            'id': t.id,
            'name': t.name,
            'columns': t.get_columns(),
            'created_at': t.created_at.isoformat(),
            'updated_at': t.updated_at.isoformat()
        })
    return jsonify({'templates': results})

@main_bp.route('/leads_overview')
def leads_overview():
    """Handle the Leads Overview page."""
    
    # Get pagination parameters from request
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '')
    
    # Create a query for structured leads
    query = StructuredLead.query
    
    # Apply search if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            StructuredLead.first_name.ilike(search_term),
            StructuredLead.last_name.ilike(search_term),
            StructuredLead.email.ilike(search_term),
            # Add more fields as needed
        ))
    
    # Paginate the query
    leads_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    leads_data = []
    for lead in leads_pagination.items:
        lead_info = lead.dict_with_company()

        # Fetch the latest task related to this lead OR company.  Prioritize lead-related tasks.
        latest_task = ProcessingTask.query.filter(
            or_(ProcessingTask.structured_lead_id == lead.id,
                ProcessingTask.company_id == lead.company_id)
        ).order_by(ProcessingTask.structured_lead_id.desc(), ProcessingTask.updated_at.desc()).first()

        if latest_task:
            lead_info['task_status'] = latest_task.status
            lead_info['task_updated_at'] = latest_task.updated_at
        else:
            lead_info['task_status'] = None
            lead_info['task_updated_at'] = None

        leads_data.append(lead_info)

    # Get total number of leads for pagination info
    total_leads = leads_pagination.total

    # Define the order of fields for display
    ordered_fields_names = [
        {'display_name': 'First Name', 'name': 'first_name'},
        {'display_name': 'Last Name', 'name': 'last_name'},
        {'display_name': 'Email', 'name': 'email'},
        {'display_name': 'Company Name', 'name': 'company_name'},
        {'display_name': 'Website URL', 'name': 'company_website_url'},
        {'display_name': 'Niche Category', 'name': 'company_niche_category'},
        {'display_name': 'Company Is Running Ads', 'name': 'company_is_running_ads'},
        {'display_name': 'Company Custom Video', 'name': 'company_custom_youtube_video'},
        {'display_name': 'Phone', 'name': 'phone'},
        {'display_name': 'LinkedIn URL', 'name': 'linkedin_url'},
        {'display_name': 'Company Ads URL', 'name': 'company_ads_url'},
        {'display_name': 'Source', 'name': 'source'},
        {'display_name': 'Tags', 'name': 'tags'},
        {'display_name': 'Company Tags', 'name': 'company_tags'},
        {'display_name': 'Task Status', 'name': 'task_status'},
    ]
    
    return render_template(
        'leads_overview.html', 
        leads_data=leads_data, 
        ordered_fields=ordered_fields_names,
        pagination=leads_pagination,
        total_leads=total_leads,
        search=search
    )

@main_bp.route('/start_render', methods=['POST'])
@login_required
@roles_required('admin')  # Only admins can start renders
def start_render():
    """
    Handles the request to start rendering a video for a specific lead.
    First looks up the StructuredLead, then gets its company_id to start the render.
    """
    data = request.get_json()
    lead_id = data.get('lead_id')
    overwrite_conditions = data.get('overwrite_conditions', False)

    if not lead_id:
        return jsonify({'status': 'error', 'reason': 'No lead_id provided'}), 400

    # Look up the StructuredLead to get its company_id
    structured_lead = StructuredLead.query.get(lead_id)
    if not structured_lead:
        return jsonify({'status': 'error', 'reason': 'Structured lead not found'}), 404

    company_id = structured_lead.company_id
    
    from automation_manager import start_render_and_upload_if_not_exist
    result = start_render_and_upload_if_not_exist(company_id, overwrite_conditions)

    if result['status'] == 'created':
        return jsonify({'status': 'created', 'task_id': result['task_id']})
    elif result['status'] == 'skipped':
        return jsonify({'status': 'skipped', 'reason': result['reason']})
    else:
        return jsonify({'status': 'error', 'reason': result['reason']}), 500

@main_bp.route('/ai_chat', methods=['POST'])
@login_required
@roles_required('admin')  # Only admins can use AI chat
def ai_chat():
    """
    Dummy AI endpoint that receives conversation + selected leads and returns a placeholder response.
    """
    data = request.json or {}
    messages = data.get('messages', [])
    selected_leads = data.get('selected_leads', [])

    # Let AI Agent do actions and respond
    messages = AI_database_agent.respond(messages, selected_leads)
    print(messages)
    
    return jsonify({"messages": messages}), 200



@main_bp.route('/batch-manager')
@login_required
@roles_required('admin', 'uploader')
def batch_manager():
    """
    Shows a list of unique import batch tags with pagination (10 per page). 
    Displays each batch with the progress of how many leads have a Drive video (via Company's custom_youtube_video) vs total leads.
    Also shows how many have tasks that failed.
    If progress < 100%, the user can still click Export, which will only export leads with YT links.
    """
    # Get page number from query params, default to 1
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of batches per page

    # Step 1: Retrieve all tags that contain 'import-batch' from StructuredLead tags column
    batch_tags_data = (
        db.session.query(StructuredLead.tags)
        .filter(StructuredLead.tags.ilike('%import-batch%'))
        .all()
    )
    
    # Step 2: Extract individual import-batch tags
    import_tags_set = set()
    for row in batch_tags_data:
        if row[0]:
            tags = [tag.strip() for tag in row[0].split(',')]
            import_tags = [tag for tag in tags if tag.startswith('import-batch')]
            import_tags_set.update(import_tags)
    
    # Step 3: Convert to list and sort by date (newest first)
    def parse_tag(tag):
        # Expected tag format: "import-batch DD-MM-YYYY/N"
        try:
            # Split the tag into prefix and the date/N part
            parts = tag.split()
            if len(parts) < 2:
                return (0, 0, 0, 0)
            date_and_n = parts[1]
            date_part, n_part = date_and_n.split('/')
            day, month, year = date_part.split('-')
            return (int(year), int(month), int(day), int(n_part))
        except Exception:
            return (0, 0, 0, 0)
    
    all_batch_tags = sorted(list(import_tags_set), key=parse_tag, reverse=True)
    
    # Step 4: Calculate pagination values
    total_batches = len(all_batch_tags)
    total_pages = (total_batches + per_page - 1) // per_page  # Ceiling division
    
    # Make sure page is within valid range
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Step 5: Get only the batch tags for the current page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_batches)
    current_page_tags = all_batch_tags[start_idx:end_idx] if start_idx < total_batches else []
    
    # Step 6: For each batch tag on the current page, gather batch information
    batch_info_list = []
    for tag in current_page_tags:
        # Use LIKE patterns to match exact tags within the comma-separated string in the StructuredLead.tags column
        leads_in_batch = (
            db.session.query(StructuredLead)
            .filter(
                StructuredLead.tags.isnot(None),
                or_(
                    StructuredLead.tags == tag,
                    StructuredLead.tags.like(f'{tag},%'),
                    StructuredLead.tags.like(f'%, {tag},%'),
                    StructuredLead.tags.like(f'%, {tag}')
                )
            )
            .all()
        )
        
        total_leads = len(leads_in_batch)

        # Initialize counters
        done_count = 0
        failed_count = 0
        pending_count = 0
        in_progress_count = 0
        error_messages = []

        for lead in leads_in_batch:
            # Check if the associated Company has a custom YouTube video link
            if lead.company and lead.company.custom_youtube_video and lead.company.custom_youtube_video.strip():
                done_count += 1
            
            # Process tasks for each company
            if lead.company:
                has_failed = False
                for task in lead.company.tasks:
                    if task.status == 'failed':
                        has_failed = True
                        failed_count += 1
                        # Get error message from result_data if available
                        result_data = task.get_result_data()
                        if result_data and 'error' in result_data:
                            error_message = f"Company: {lead.company.name} - {result_data['error']}"
                            if error_message not in error_messages:
                                error_messages.append(error_message)
                    elif task.status == 'pending':
                        pending_count += 1
                    elif task.status == 'in_progress':
                        in_progress_count += 1
                
                # Ensure we don't double-count companies with multiple failed tasks
                if has_failed:
                    failed_count -= (len([t for t in lead.company.tasks if t.status == 'failed']) - 1)

        # Calculate percentages
        progress_percent = round((done_count / total_leads) * 100) if total_leads > 0 else 0
        failed_percent = round((failed_count / total_leads) * 100) if total_leads > 0 else 0
        pending_percent = round((pending_count / total_leads) * 100) if total_leads > 0 else 0
        in_progress_percent = round((in_progress_count / total_leads) * 100) if total_leads > 0 else 0
        # For the progress bar, combine pending and in_progress
        pending_in_progress_percent = pending_percent + in_progress_percent

        if done_count + failed_count + pending_count + in_progress_count == total_leads:
            pending_in_progress_percent += 100 - (pending_in_progress_percent + progress_percent + failed_percent)

            
        # Limit the number of error messages to prevent overwhelming the UI
        original_count = len(error_messages)
        if original_count > 5:
            error_messages = error_messages[:5]
            error_messages.append(f"... and {original_count - 5} more errors")

        batch_info_list.append({
            'batch_tag': tag,
            'total_leads': total_leads,
            'done_count': done_count,
            'progress_percent': progress_percent,
            'failed_count': failed_count,
            'failed_percent': failed_percent,
            'pending_percent': pending_in_progress_percent,
            'completed_percent': progress_percent,
            'error_messages': error_messages,
        })
    
    # Step 7: Create pagination info to pass to the template
    pagination = {
        'page': page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
        'total_batches': total_batches,
    }

    return render_template('batch_manager.html', 
                          batch_info_list=batch_info_list, 
                          pagination=pagination)

@main_bp.route('/batch/render', methods=['POST'])
@login_required
def render_batch():
    """
    Resets all failed tasks in the specified batch to 'pending', then starts 
    the render+upload process for each Lead in that batch.
    """
    from automation_manager import start_render_and_upload_if_not_exist
    data = request.json
    batch_tag = data.get('batch_tag')

    if not batch_tag:
        return jsonify({'status': 'error', 'message': 'No batch_tag provided'}), 400

    # Retrieve all leads with this batch_tag
    companies_in_batch = (
        db.session.query(Company)
        .filter(Company.tags.contains(batch_tag))  # Assuming tags are comma-separated
        .all()
    )

    if not companies_in_batch:
        return jsonify({'status': 'error', 'message': 'No leads found for that batch'}), 404

    # Reset failed tasks to 'pending' for all these leads
    for company in companies_in_batch:
        for task in company.tasks:
            if task.status == 'failed':
                task.status = 'pending'
                task.updated_at = datetime.utcnow()
    db.session.commit()

    # Start render+upload tasks
    # overwrite_conditions=True ensures we create fresh tasks even if previous ones existed
    for company in companies_in_batch:
        start_render_and_upload_if_not_exist(company.id, overwrite_conditions=False)

    return jsonify({
        'status': 'ok',
        'message': f'Render tasks started for {len(companies_in_batch)} companies in batch {batch_tag}.'
    })

@main_bp.route('/batch/export', methods=['POST'])
@login_required
def export_batch():
    """
    Exports structured leads in a given batch as CSV, but only those whose associated Company 
    has a YouTube URL. Also tags exported leads with 'exported'.
    """
    data = request.json
    batch_tag = data.get('batch_tag')
    if not batch_tag:
        return jsonify({'status': 'error', 'message': 'No batch_tag provided'}), 400

    # Get all structured leads whose tags include the batch_tag
    leads_in_batch = (
        db.session.query(StructuredLead)
        .filter(StructuredLead.tags.contains(batch_tag))
        .all()
    )

    if not leads_in_batch:
        return jsonify({'status': 'error', 'message': 'No leads found for that batch'}), 404

    # Prepare CSV data
    output = []
    headers = ["First Name", "Last Name", "email", "YouTube URL", "Company Name", "Title"]
    output.append(headers)

    for lead in leads_in_batch:
        # Retrieve the YouTube URL from the associated Company, if available
        video_url = lead.company.custom_youtube_video if (lead.company and lead.company.custom_youtube_video) else ''
        # Skip if there's no Video link:
        if not video_url or not video_url.strip():
            continue

        row = [
            lead.first_name or '',
            lead.last_name or '',
            lead.email or '',
            video_url,
            lead.company.name if (lead.company and lead.company.name) else '',
            lead.title or ''
        ]
        output.append(row)

        # Add 'exported' tag to the lead's tags if not already present
        existing_tags = lead.tags or ''
        tags_list = [t.strip() for t in existing_tags.split(',') if t.strip()] if existing_tags else []
        if 'exported' not in tags_list:
            tags_list.append('exported')
            lead.tags = ','.join(tags_list)
            db.session.add(lead)

    db.session.commit()

    if len(output) == 1:  # Only the header row exists, meaning no leads with a YouTube link were processed.
        return jsonify({'status': 'error', 'message': 'No leads with a Video in this batch.'}), 400

    # Create CSV file
    import uuid
    unique_filename = f"batch_export_{uuid.uuid4().hex}.csv"
    final_path = os.path.join('output', unique_filename)
    
    # Ensure output directory exists
    os.makedirs('output', exist_ok=True)

    with open(final_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(output)

    # Return download URL
    download_url = url_for('serve_file', filename=unique_filename, _external=True)
    return jsonify({'status': 'ok', 'download_url': download_url})

@main_bp.route('/batch/delete', methods=['POST'])
@login_required
@roles_required('admin')  # Only admins can delete batches
def delete_batch():
    """
    Delete all leads and companies associated with a specific batch tag.
    """
    data = request.json
    batch_tag = data.get('batch_tag')
    
    if not batch_tag:
        return jsonify({"status": "error", "message": "No batch tag provided"}), 400
    
    try:
        # Find all leads with this batch tag
        leads_in_batch = (
            db.session.query(StructuredLead)
            .filter(
                StructuredLead.tags.isnot(None),
                or_(
                    StructuredLead.tags == batch_tag,
                    StructuredLead.tags.like(f'{batch_tag},%'),
                    StructuredLead.tags.like(f'%, {batch_tag},%'),
                    StructuredLead.tags.like(f'%, {batch_tag}')
                )
            )
            .all()
        )
        
        # If no leads found with this batch tag
        if not leads_in_batch:
            return jsonify({"status": "error", "message": f"No leads found with batch tag '{batch_tag}'"}), 404
        
        # Collect company IDs to be deleted
        company_ids = []
        for lead in leads_in_batch:
            if lead.company_id and lead.company_id not in company_ids:
                company_ids.append(lead.company_id)
        
        # Delete all tasks associated with these companies first to avoid foreign key constraints
        for company_id in company_ids:
            tasks = ProcessingTask.query.filter_by(company_id=company_id).all()
            for task in tasks:
                db.session.delete(task)
        
        # Delete all tasks associated with these leads
        for lead in leads_in_batch:
            tasks = ProcessingTask.query.filter_by(structured_lead_id=lead.id).all()
            for task in tasks:
                db.session.delete(task)
        
        # Delete the leads
        lead_count = 0
        for lead in leads_in_batch:
            db.session.delete(lead)
            lead_count += 1
        
        # Delete the companies
        company_count = 0
        for company_id in company_ids:
            company = Company.query.get(company_id)
            if company:
                # Check if the company still has any leads (not in this batch)
                remaining_leads = StructuredLead.query.filter_by(company_id=company_id).count()
                if remaining_leads == 0:  # Only delete if no leads remain
                    db.session.delete(company)
                    company_count += 1
        
        # Commit the changes
        db.session.commit()
        
        return jsonify({
            "status": "ok", 
            "message": f"Successfully deleted {lead_count} leads and {company_count} companies for batch '{batch_tag}'"
        })
    
    except Exception as e:
        db.session.rollback()  # Roll back in case of error
        print(f"Error deleting batch: {str(e)}")
        return jsonify({"status": "error", "message": f"Error deleting batch: {str(e)}"}), 500


@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 errors"""
    logger.error(f"403 error occurred: {error}")
    return redirect(url_for('auth.login'))

# @app.errorhandler(Exception)
# def handle_exception(e):
#     """Handle all other exceptions"""
#     logger.error(f"Unhandled exception: {e}")
#     return str(e), 500

# Register the main blueprint
app.register_blueprint(main_bp)
app.register_blueprint(drive_bp, url_prefix="/drive")

if __name__ == '__main__':

    logger.debug("Starting Flask application...")
    # Make sure the templates directory exists
    if not os.path.exists(os.path.join(app.root_path, 'templates')):
        logger.error(f"Templates directory not found at {os.path.join(app.root_path, 'templates')}")
        os.makedirs(os.path.join(app.root_path, 'templates'), exist_ok=True)
        logger.info("Created templates directory")
    
    app.run(debug=True)

