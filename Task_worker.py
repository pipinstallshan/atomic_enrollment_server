import uuid
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Union

import config
import utils.render as render
import utils.browser_tools as browser_tools
from main import app, db
from models import ProcessingTask, Company, get_session
from sqlalchemy.sql import case
from utils.types import VideoConfig
from drive_oauth import upload_file_to_drive


def get_next_task(session, instance_id: str) -> Union[ProcessingTask, None]:
    """
    Gets the next video task to process and marks it as in progress.
    
    Args:
        session (Session): The SQLAlchemy session to use.
        instance_id (str): The ID of the current processing instance
    
    Returns:
        Union[ProcessingTask, None]: The next task to process, or None if no tasks are available
    """
    stuck_timeout = datetime.utcnow() - timedelta(hours=1)

    # We define a custom ordering: tasks with type 'upload_video' first, then 'video_render', then others
    task_priority = ["upload_video", "video_render"]
    ordering = case(
        {task: index for index, task in enumerate(task_priority)},
        value=ProcessingTask.task_type,
        else_=len(task_priority)  # tasks not in the list come last
    )

    try:
        # Use FOR UPDATE to lock the row while we're processing it
        next_task = (
            session.query(ProcessingTask)
            .filter(
                (ProcessingTask.status == 'pending')
                | ((ProcessingTask.status == 'in_progress') & (ProcessingTask.updated_at < stuck_timeout))
            )
            .order_by(ordering)
            .with_for_update(skip_locked=True)  # Skip locked rows to avoid waiting
            .first()
        )

        if next_task:
            next_task.status = 'in_progress'
            next_task.instance_id = instance_id
            next_task.updated_at = datetime.utcnow()
            session.commit()
            
        return next_task
    except Exception as e:
        # If any exception occurs during task acquisition, rollback and return None
        session.rollback()
        print(f"Error acquiring task: {e}")
        return None


def process_upload_video_task(session, task: ProcessingTask, instance_id: str) -> None:
    """
    Processes a video upload task.
    
    Args:
        session (Session): The SQLAlchemy session to use.
        task (ProcessingTask): The upload video task to process.
        instance_id (str): The ID of the processing instance.
    """
    try:
        task.status = 'in_progress'
        session.commit()

        task_data = task.get_result_data()
        video_path = task_data.get('rendered_file')

        if video_path is None:
            # Load the 'task_data.get("output_filename", None)' from the completed video_render associated to the same Company
            # Try to find the video_render task associated with this company
            video_render_task = session.query(ProcessingTask).filter_by(
                company_id=task.company_id,
                task_type='video_render',
                status='completed'
            ).first()

            if video_render_task:
                video_render_task_data = video_render_task.get_result_data()
                video_path = video_render_task_data.get("output_filename", None)

        if not video_path:
            # Mark task as failed since no video path was found
            task.status = 'failed'
            task.set_result_data({'error': 'No rendered_file found'})
            task.updated_at = datetime.utcnow()
            session.commit()
            return
        
        company = session.query(Company).get(task.company_id)
        if not company:
            task.status = 'failed'
            task.set_result_data({'error': 'Company not found'})
            task.updated_at = datetime.utcnow()
            session.commit()
            return
        
        # Assume you have a datetime object
        dt = datetime.now()

        # Format as "Month Year"
        formatted_date = dt.strftime("%B %Y")

        # Re-fetch the task to make sure it's still valid
        session.refresh(task)

        # Actually upload to Drive
        drive_link = upload_file_to_drive(video_path, f"{company.name} | Atomic Enrollment | {formatted_date}")  
        # store the link in the company:
        company.custom_youtube_video = drive_link
        session.commit()

        # Re-fetch task once more before final update
        session.refresh(task)
        task.set_result_data({'drive_link': drive_link})
        task.status = 'completed'
        session.commit()

    except Exception as e:
        session.rollback()
        # Re-fetch the task after rollback
        refreshed_task = session.query(ProcessingTask).get(task.id)
        if refreshed_task:
            refreshed_task.status = 'failed'
            refreshed_task.set_result_data({'error': str(e)})
            refreshed_task.updated_at = datetime.utcnow()
            session.commit()
        raise  # Re-raise the exception for the main loop to handle


def process_video_task(session, task: ProcessingTask, instance_id: str) -> None:
    """
    Processes a video rendering task.

    This function generates screenshots of the website and ads (if applicable),
    renders a video based on the specified configuration, and creates a new
    'upload_video' task.

    Args:
        session (Session): The SQLAlchemy session to use.
        task (ProcessingTask): The video rendering task to process.
        instance_id (str): The ID of the processing instance.
    """
    try:
        company = session.query(Company).get(task.company_id)
        if not company:
            task.status = 'failed'
            task.set_result_data({'error': 'Company not found'})
            task.updated_at = datetime.utcnow()
            session.commit()
            return

        website_url = company.website_url
        ads_url = company.ads_url
        niche_category = company.niche_category
        is_running_ads = company.is_running_ads

        if not all([website_url, niche_category]):
            task.status = 'failed'
            task.set_result_data({'error': 'Missing required fields: website_url or niche_category'})
            task.updated_at = datetime.utcnow()
            session.commit()
            return

        # 1) Generate screenshots
        website_screenshot_path = f"temp/website_screenshot_{instance_id}.png"
        ads_screenshot_path = f"temp/ads_screenshot_{instance_id}.png"

        r = browser_tools.get_screenshot(website_url, website_screenshot_path)
        if r["success"] == False:
            task.status = "failed"
            task.set_result_data({"error": "Error when taking screenshot. The website likely blocked us or the image is unusable for the video"})
            session.commit()
            return
        if ads_url:
            browser_tools.get_screenshot(ads_url, ads_screenshot_path)

        from utils.ai_basic_functions import categorize
        # 2) Render video
        # TODO better info parsing and config category detection
        config_setting_name = (
            categorize(niche_category, ["skills program", "money coaching"], "blue collar and bootcamps and trade/vocational schools are usually 'skills program'", "openai:gpt-4o-mini")
            + (" yes ads" if True else " no ads")
        )
        video_config = config.all_configs[config_setting_name].copy()

        for instruction in video_config["instructions"]:
            if "image_path" in instruction:
                instruction["image_path"] = instruction["image_path"].format(instance_id)

        output_filename = f"output/video_task_{task.id}.mp4"
        render.render_video(video_config, output_filename)

        # Re-fetch the task to make sure it's still valid and hasn't been modified
        session.refresh(task)
        
        # 3) Mark the render task 'completed'
        task.status = 'completed'
        task.set_result_data({
            'output_filename': output_filename,
            'config_used': config_setting_name
        })
        task.updated_at = datetime.utcnow()
        session.commit()

        # 4) Create a new 'upload_video' task
        new_task = ProcessingTask(
            company_id=task.company_id,
            task_type='upload_video',
            status='pending'
        )
        # We can store the rendered file path in the result_data if we want:
        new_task.set_result_data({'rendered_file': output_filename})
        session.add(new_task)
        session.commit()
    
    except Exception as e:
        session.rollback()
        # Re-fetch the task after rollback
        refreshed_task = session.query(ProcessingTask).get(task.id)
        if refreshed_task:
            refreshed_task.status = 'failed'
            refreshed_task.set_result_data({'error': str(e)})
            refreshed_task.updated_at = datetime.utcnow()
            session.commit()
        raise  # Re-raise the exception for the main loop to handle


def main() -> None:
    """
    Main function for the video renderer.

    This function continuously checks for pending or stuck video tasks and processes them.
    It runs in an infinite loop until manually stopped.
    """
    instance_id = str(uuid.uuid4())
    print(f"Starting video renderer instance {instance_id}")

    while True:
        # Use an application context to ensure access to Flask's config and DB
        with app.app_context():
            # Get a session for fetching and processing tasks
            with get_session() as session:
                next_task = get_next_task(session, instance_id)

                if next_task:
                    try:
                        # Re-fetch task in case the object is stale
                        next_task = session.query(ProcessingTask).get(next_task.id)
                        if not next_task:
                            print("Task not found or already processed by another worker.")
                            continue

                        if next_task.task_type == 'video_render':
                            process_video_task(session, next_task, instance_id)
                        elif next_task.task_type == 'upload_video':
                            process_upload_video_task(session, next_task, instance_id)
                        else:
                            print(f"Unknown task type: {next_task.task_type}")
                            next_task.status = 'failed'
                            session.commit()

                    except Exception as e:
                        print(f"Unexpected error processing task {next_task.id if next_task else 'unknown'}: {e}")
                        # First roll back the session to recover from any previous errors
                        session.rollback()
                        
                        try:
                            # Re-fetch the task after rollback
                            if next_task and next_task.id:
                                next_task = session.query(ProcessingTask).get(next_task.id)
                                if next_task:
                                    # Mark task as failed
                                    next_task.status = 'failed'
                                    next_task.set_result_data({'error': str(e)})
                                    next_task.updated_at = datetime.utcnow()
                                    session.commit()
                                else:
                                    print(f"Task not found after rollback, it may have been processed by another worker")
                        except Exception as inner_e:
                            print(f"Error updating task status after exception: {inner_e}")
                            session.rollback()
                else:
                    print(f"Instance {instance_id}: No pending tasks found. Waiting...")
                    time.sleep(60)


if __name__ == "__main__":
    main()
