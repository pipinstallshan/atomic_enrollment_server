from typing import Optional
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import json
from contextlib import contextmanager
import re
from sqlalchemy.orm import validates
from sqlalchemy import func, or_
from utils.ai_prompts import create_prompt_for_loading_data
from utils.ai_basic_functions import run_prompt_with_gemini, run_prompt_with_gemini_async

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

@contextmanager
def get_session():
    """
    Provide a transactional scope for SQLAlchemy sessions.
    Rolls back on exceptions and commits otherwise.
    """
    session = db.session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()

class User(UserMixin, db.Model):
    """User model for authentication."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role = db.Column(db.String(50), nullable=False, default="uploader")
    
    # One-to-many relationship with DriveAccount
    drive_accounts = db.relationship('DriveAccount', backref='user', lazy=True)

    def set_password(self, password):
        """Set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'role': self.role
        }

class DriveAccount(db.Model):
    """
    Holds each user's connected Google Drive info.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)
    account_name = db.Column(db.String(120), nullable=True)
    refresh_token = db.Column(db.String(250), nullable=False)
    access_token = db.Column(db.String(250))
    token_expiry = db.Column(db.DateTime)
    needs_reauth = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<DriveAccount {self.email}>'

    def dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.email,
            'account_name': self.account_name,
            'token_expiry': self.token_expiry.isoformat() if self.token_expiry else None,
            'needs_reauth': self.needs_reauth
        }

class FieldDefinition(db.Model):
    """Defines available fields for leads."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    field_type = db.Column(db.String(50), nullable=False)  # text, number, boolean, etc.
    is_system = db.Column(db.Boolean, default=False)  # True for system-required fields
    is_required = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    
    def __repr__(self):
        return f'<FieldDefinition {self.name}>'

    def dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'field_type': self.field_type,
            'is_system': self.is_system,
            'is_required': self.is_required,
            'created_at': self.created_at.isoformat()
        }

class Lead(db.Model):
    """Core lead model containing only essential metadata."""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    source = db.Column(db.String(50), nullable=False)  # e.g., 'csv_import', 'manual', 'api'
    
    # Relationships
    data = db.relationship('LeadData', backref='lead', lazy=True, cascade='all, delete-orphan')

    def get_data(self, field_name):
        """Get the value of a specific field."""
        data_entry = LeadData.query.filter_by(lead_id=self.id, field_name=field_name).first()
        return data_entry.field_value if data_entry else None

    def set_data(self, field_name, value, is_enriched=False, enrichment_source=None):
        """Set or update a field value."""
        data_entry = LeadData.query.filter_by(lead_id=self.id, field_name=field_name).first()
        if data_entry:
            data_entry.field_value = value
            data_entry.is_enriched = is_enriched
            data_entry.enrichment_source = enrichment_source
        else:
            data_entry = LeadData(
                lead_id=self.id,
                field_name=field_name,
                field_value=value,
                is_enriched=is_enriched,
                enrichment_source=enrichment_source
            )
            db.session.add(data_entry)
        self.updated_at = utc_now()
        db.session.commit()

    def to_dict(self):
        """Convert lead to dictionary including all data."""
        return {
            'id': self.id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'source': self.source,
            'data': {d.field_name: d.field_value for d in self.data},
        }

    def dict(self):
        return self.to_dict()

class LeadData(db.Model):
    """Flexible data storage for lead fields."""
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    field_name = db.Column(db.String(100), nullable=False)
    field_value = db.Column(db.Text)
    is_enriched = db.Column(db.Boolean, default=False)
    enrichment_source = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        db.Index('idx_lead_field', lead_id, field_name),  # Index for faster field lookups
    )

    def dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'field_name': self.field_name,
            'field_value': self.field_value,
            'is_enriched': self.is_enriched,
            'enrichment_source': self.enrichment_source,
            'updated_at': self.updated_at.isoformat()
        }

class ProcessingTask(db.Model):
    """Model for tracking processing tasks (video rendering, enrichments, etc.)."""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    structured_lead_id = db.Column(db.Integer, db.ForeignKey('structured_lead.id'), nullable=True)
    task_type = db.Column(db.String(50), nullable=False)  # e.g., 'video_render', 'email_find'
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, in_progress, completed, failed
    instance_id = db.Column(db.String(36))  # UUID of processing instance
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    result_data = db.Column(db.Text)  # JSON string for task-specific data

    # Relationships
    company = db.relationship('Company', backref='tasks', lazy=True)
    structured_lead = db.relationship('StructuredLead', backref='tasks', lazy=True)

    def set_result_data(self, data):
        """Set result data as JSON."""
        self.result_data = json.dumps(data)

    def get_result_data(self):
        """Get result data as Python object."""
        return json.loads(self.result_data) if self.result_data else None

    def to_dict(self):
        """Convert task to dictionary."""
        return {
            'id': self.id,
            'task_type': self.task_type,
            'status': self.status,
            'instance_id': self.instance_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'result_data': self.get_result_data()
        }

    def dict(self):
        return self.to_dict()

class ExportTemplate(db.Model):
    """
    Model representing a user's export template.

    :param id: Primary key
    :param user_id: Foreign key to the user who owns this template
    :param name: Human-friendly name of the template
    :param columns_json: JSON string storing an array of field names that the user wants to export
    :param created_at: When the template was created
    :param updated_at: When the template was last updated
    """
    __tablename__ = "export_templates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    columns_json = db.Column(db.Text, nullable=False, default='[]')
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationship to user
    user = db.relationship('User', backref='export_templates', lazy=True)

    def get_columns(self) -> list[str]:
        """Return the list of columns from the stored JSON."""
        return json.loads(self.columns_json)

    def set_columns(self, columns: list[str]) -> None:
        """
        Set the columns in the template.
        
        :param columns: A list of strings representing field names
        """
        self.columns_json = json.dumps(columns)

    def dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'columns': self.get_columns(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Company(db.Model):
    """Company model containing company information."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    website_url = db.Column(db.String(512), nullable=False)
    niche_category = db.Column(db.String(100), nullable=False)
    is_running_ads = db.Column(db.Boolean, nullable=False, default=False)
    ads_url = db.Column(db.String(512))
    custom_youtube_video = db.Column(db.String(512))
    tags = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    
    # Relationships
    leads = db.relationship('StructuredLead', backref='company', lazy=True)
    
    def __repr__(self):
        return f'<Company {self.name}>'

    def load_using_ai(self, input_data: str):
        output_rules = """- name: Title Case (not nullable; if not provided, use 'Unknown') 
- website_url: valid url (not nullable; if not provided, use 'Unknown')
- niche_category: Enum[skills program,money coaching] (not nullable; if not provided, use 'Unknown')
- is_running_ads: bool, Enum[true,false] (not nullable; true by default)
- ads_url: valid url
- custom_youtube_video: valid url or empty string (can also be a google drive or dropbox etc url with the custom video)
- tags: String of list of tags, comma seperated (eg 'tag1,tag2' or '')

Notes: in the niche things like 'blue collar', 'BC', 'coding bootcamp' are 'skills program' and things like financial investing or coaching is 'money coaching'."""
        prompt = create_prompt_for_loading_data(input_data, output_rules)
        response = run_prompt_with_gemini(prompt=prompt)
        response = response.strip("\n `json")
        json_response = json.loads(response)

        for attribute, value in json_response.items():
            if hasattr(self, attribute) and value is not None:
                setattr(self, attribute, value)
        return self
    
    async def load_using_ai_async(self, input_data: str):
        """
        Async version of load_using_ai that uses async Gemini API.
        """
        output_rules = """- name: Title Case (not nullable; if not provided, use 'Unknown') 
- website_url: valid url (not nullable; if not provided, use 'Unknown')
- niche_category: Enum[skills program,money coaching] (not nullable; if not provided, use 'Unknown')
- is_running_ads: bool, Enum[true,false] (not nullable; true by default)
- ads_url: valid url
- custom_youtube_video: valid url or empty string (can also be a google drive or dropbox etc url with the custom video)
- tags: String of list of tags, comma seperated (eg 'tag1,tag2' or '')

Notes: in the niche things like 'blue collar', 'BC', 'coding bootcamp' are 'skills program' and things like financial investing or coaching is 'money coaching'."""
        prompt = create_prompt_for_loading_data(input_data, output_rules)
        response = await run_prompt_with_gemini_async(prompt=prompt)
        response = response.strip("\n `json")
        json_response = json.loads(response)

        for attribute, value in json_response.items():
            if hasattr(self, attribute) and value is not None:
                setattr(self, attribute, value)
        return self
    
    @classmethod
    def create_with_ai(cls, input_data: str):
        """
        Create a new Company instance using AI enrichment.

        Args:
            input_data (str): The input data to use for enrichment.

        Returns:
            Company: The newly created Company instance.
        """
        company = cls()
        company.load_using_ai(input_data)
        return company
    
    @classmethod
    async def create_with_ai_async(cls, input_data: str):
        """
        Async version of create_with_ai.
        Create a new Company instance using AI enrichment asynchronously.

        Args:
            input_data (str): The input data to use for enrichment.

        Returns:
            Company: The newly created Company instance.
        """
        company = cls()
        await company.load_using_ai_async(input_data)
        return company
    
    def look_for_duplicate(self) -> Optional['Company']:
        """
        Look for a possible duplicate company in the database.

        Checks for duplicates based on the following criteria:
        1. Exact match of 'website_url'.
        2. If no exact match, check for normalized 'website_url' match.
        3. If no match, check for base_url match.

        Returns:
            Company: The duplicate Company object if found, otherwise None.
        """
        print(self.website_url)
        if not self.website_url:
            return None
        # 1. Check for exact match on website_url
        exact_duplicate = Company.query.filter(Company.website_url == self.website_url, Company.id != self.id).first()
        if exact_duplicate:
            return exact_duplicate

        # 2. Check for normalized URL match
        normalized_url = self.website_url.replace("www.", "").replace("https", "http").replace("http", "").replace("/", "").replace(":", "").lower() if self.website_url else None
        if normalized_url:
            # Query using normalized URL comparison
            duplicate = Company.query.filter(
                Company.id != self.id,
                func.lower(func.replace(func.replace(func.replace(func.replace(func.replace(Company.website_url, 'www.', ''), "http", ""), 'https', 'http'), '/', ''), ':', '')) == normalized_url
            ).first()
            if duplicate:
                return duplicate
        
        # 3. Check for base_url match
        if self.website_url.startswith("http://") or self.website_url.startswith("https://"):
            base_url = self.website_url.split("/")[2].split("?")[0].split(":")[0].split("#")[0]
        else:
            base_url = self.website_url.split("/")[0].split("?")[0].split(":")[0].split("#")[0]

        if len(base_url) < 3:
            return None  # Parsing failed

        duplicates = Company.query.filter(
            Company.id != self.id,
            func.lower(func.substr(Company.website_url, 1, len(base_url) + 10)) == base_url.lower()
        ).all()
        if len(duplicates) > 0:
            print("base url match found, checking for duplicates. original url: ", self.website_url, "base url: ", base_url, "example duplicate url: ", duplicates[0].website_url)
            if len(duplicates) > 5:
                print('Too many duplicates, limiting to 5. base_url: ', base_url, 'total duplicates: ', len(duplicates))
                duplicates = duplicates[:5]
            for duplicate in duplicates:
                prompt = f"""
                Are these two company records representing the same actual company?
                Company 1 (New):
                - Name: {self.name}
                - Website: {self.website_url}
                - Niche: {self.niche_category}
                - Running Ads: {self.is_running_ads}
                - Ads URL: {self.ads_url}
                - Tags: {self.tags}

                Company 2 (Existing):
                - Name: {duplicate.name}
                - Website: {duplicate.website_url}
                - Niche: {duplicate.niche_category}
                - Running Ads: {duplicate.is_running_ads}
                - Ads URL: {duplicate.ads_url}
                - Tags: {duplicate.tags}

                Return JSON response with format: 
                {{"same_company": bool, "confidence": float, "reason": str}}

                Example output:
                {{"same_company": true, "confidence": 0.95, "reason": "The websites and company names are almost identical, with only minor differences in formatting and content and company name. rest is identical."}}
                """
                
                response = run_prompt_with_gemini(prompt=prompt)
                try:
                    result = json.loads(response.strip(" \n`json"))
                    if result.get('same_company', False) and result.get('confidence', 0) >= 0.7:
                        return duplicate
                except json.JSONDecodeError:
                    continue
            return duplicates[0]

        return None

    def dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'website_url': self.website_url,
            'niche_category': self.niche_category,
            'is_running_ads': self.is_running_ads,
            'ads_url': self.ads_url,
            'custom_youtube_video': self.custom_youtube_video,
            'tags': self.tags,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class StructuredLead(db.Model):
    """Structured lead model with direct field access."""
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100))
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(50))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    linkedin_url = db.Column(db.String(512))
    tags = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    
    def __repr__(self):
        return f'<Lead {self.first_name} {self.last_name}>'
    
    def load_using_ai(self, input_data: str):
        output_rules = """- first_name: Title Case (not nullable; if not provided, use 'Unknown')
- last_name: Title Case (not nullable; if not provided, use 'Unknown')
- title: Title Case (company title)
- email: Lowercase, valid email (not nullable; if not provided, use 'Unknown')
- phone: valid phone number with country code (use '+1' by default if it looks like a NA number)
- linkedin_url: account url
- tags: string of comma seperated tags (eg. 'tag1,tag2')"""
        prompt = create_prompt_for_loading_data(input_data, output_rules)
        response = run_prompt_with_gemini(prompt=prompt)
        response = response.strip("\n `json")
        json_response = json.loads(response)
        
        for attribute, value in json_response.items():
            if hasattr(self, attribute) and value is not None:
                setattr(self, attribute, value)
        return self

    async def load_using_ai_async(self, input_data: str):
        """
        Async version of load_using_ai that uses async Gemini API.
        """
        output_rules = """- first_name: Title Case (not nullable; if not provided, use 'Unknown')
- last_name: Title Case (not nullable; if not provided, use 'Unknown')
- title: Title Case (company title)
- email: Lowercase, valid email (not nullable; if not provided, use 'Unknown')
- phone: valid phone number with country code (use '+1' by default if it looks like a NA number)
- linkedin_url: account url
- tags: string of comma seperated tags (eg. 'tag1,tag2')"""
        prompt = create_prompt_for_loading_data(input_data, output_rules)
        response = await run_prompt_with_gemini_async(prompt=prompt)
        response = response.strip("\n `json")
        json_response = json.loads(response)
        
        for attribute, value in json_response.items():
            if hasattr(self, attribute) and value is not None:
                setattr(self, attribute, value)
        return self

    @classmethod
    def create_using_ai(cls, input_data: str):
        lead = cls()
        lead.load_using_ai(input_data)
        return lead
    
    @classmethod
    async def create_using_ai_async(cls, input_data: str):
        """
        Async version of create_using_ai.
        Create a new StructuredLead instance using AI enrichment asynchronously.

        Args:
            input_data (str): The input data to use for enrichment.

        Returns:
            StructuredLead: The newly created StructuredLead instance.
        """
        lead = cls()
        await lead.load_using_ai_async(input_data)
        return lead
    
    def look_for_duplicate(self):
        """
        Searches for potential duplicates of the current lead.

        It considers a lead a duplicate if:
        1.  Both first name and last name match exactly (case-insensitive).
        2.  OR: The email matches exactly (case-insensitive).

        Returns:
            A Lead object that is a potential duplicate.
            Returns None if no duplicates are found.
        """
        if not any([self.first_name, self.last_name, self.email]):
            return []  # Not enough information to find duplicates

        # Build the query dynamically
        duplicates_query = db.session.query(StructuredLead).filter(
            StructuredLead.id != self.id,  # Exclude the current lead itself
            or_(
                (func.lower(StructuredLead.first_name) == func.lower(self.first_name)) &
                (func.lower(StructuredLead.last_name) == func.lower(self.last_name)) if self.first_name and self.last_name else False,
                func.lower(StructuredLead.email) == func.lower(self.email) if self.email else False,
            )
        )

        # Execute the query and return the results
        potential_duplicate = duplicates_query.first()
        return potential_duplicate

    def dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'title': self.title,
            'email': self.email,
            'phone': self.phone,
            'company_id': self.company_id,
            'linkedin_url': self.linkedin_url,
            'tags': self.tags,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def dict_with_company(self):
        """
        Returns a dictionary representing the StructuredLead and its associated Company.

        Company fields are prefixed with "company_" to avoid key collisions.
        """
        lead_dict = self.dict()  # Get the basic lead dictionary
        if self.company:  # Check if a company is associated
            company_dict = self.company.dict()
            # Prefix company keys and merge
            prefixed_company_dict = {f"company_{k}": v for k, v in company_dict.items()}
            lead_dict.update(prefixed_company_dict)  # Merge into lead_dict
        return lead_dict

def init_db(app):
    """Initialize the database and create tables."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        
        
        db.session.commit()

def create_user(username, email, password, role='uploader'):
    """Create a new user."""
    user = User(username=username, email=email)
    user.set_password(password)
    user.role = role
    db.session.add(user)
    db.session.commit()
    return user


