from models import db, ProcessingTask, StructuredLead, Company
from datetime import datetime

def get_company_task_statuses(company_id):
    """
    Retrieve all video-related tasks for the given company and return them as a list of dicts, 
    each containing task_type, status, and updated_at.

    Args:
        company_id (int): The ID of the company.

    Returns:
        list: A list of dictionaries representing each task found, e.g.:
              [
                  {"task_type": "video_render", "status": "pending", "updated_at": "..."},
                  {"task_type": "upload_video", "status": "completed", "updated_at": "..."},
                  ...
              ]
    """
    tasks: list[ProcessingTask] = ProcessingTask.query.filter_by(company_id=company_id).all()
    task_list = []
    for t in tasks:
        task_list.append({
            "task_type": t.task_type,
            "status": t.status,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            "result_data": t.result_data
        })
    return task_list

def start_render_and_upload_if_not_exist(company_id, overwrite_conditions=False):
    """
    Starts the video rendering + uploading process for the specified company. 
    - Checks existing tasks to see if there's already a render or upload in progress or completed.
    - If a suitable task is found and overwrite_conditions=False, does nothing.
    - Otherwise, creates a new 'video_render' task (which will eventually create an 'upload_video' task).
    
    Args:
        company_id (int): The ID of the company for which we want to render a video.
        overwrite_conditions (bool): If True, will create a new task regardless of existing tasks.
                                     If False, only create a task if no suitable one exists.

    Returns:
        dict: Information about the newly-created task or a message stating that no task was created.
              For example: {"status": "created", "task_id": 123} or {"status": "skipped", "reason": "..."}.
    """
    from main import db
    company = db.session.get(Company, int(company_id))
    if not company:
        return {"status": "error", "reason": f"Company with id={company_id} not found."}

    if company.custom_youtube_video and "http" in company.custom_youtube_video and not overwrite_conditions:
        return {
            "status": "skipped",
            "reason": "Company has a custom YouTube video and overwrite_conditions is False."
        }
    
    # Grab existing tasks
    existing_tasks = ProcessingTask.query.filter_by(company_id=company_id).all()
    
    # Check for a video_render or upload_video task that's not failed.
    # We might consider 'failed' a possible re-start condition if desired.
    # If you consider 'failed' tasks as a reason to re-render, adjust logic accordingly.
    relevant_task_found = False
    for t in existing_tasks:
        if t.task_type in ("video_render", "upload_video") and t.status in ("pending", "in_progress", "completed"):
            relevant_task_found = True
            break

    if relevant_task_found and not overwrite_conditions:
        # Check if video_render was successful but upload_video failed
        video_render_success = False
        upload_failed = False
        for t in existing_tasks:
            if t.task_type == "video_render" and t.status == "completed":
                video_render_success = True
            elif t.task_type == "upload_video" and t.status == "failed":
                upload_failed = True
                t.status = "pending"  # Reset failed upload task to pending
                t.updated_at = datetime.utcnow()
                db.session.commit()

        if video_render_success and upload_failed:
            return {
                "status": "skipped", 
                "reason": "Video render completed, resetting failed upload task to pending."
            }
        return {
            "status": "skipped",
            "reason": "A render/upload task is already in progress or completed for this company."
        }
    

    # Otherwise, create a new 'video_render' task
    new_task = ProcessingTask(
        company_id=company_id,
        task_type='video_render',
        status='pending',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(new_task)
    db.session.commit()

    return {
        "status": "created",
        "task_id": new_task.id
    }

def clear_company_tasks(company_id):
    """
    Deletes all tasks associated with a given company.

    Args:
        company_id (int): The ID of the company whose tasks should be deleted.

    Returns:
        dict: A dictionary containing the status of the operation and a message.
              For example: {"status": "success", "message": "All tasks for company {company_id} have been deleted."}
              or {"status": "error", "message": "Company with id {company_id} not found."}
    """
    from main import db
    company = db.session.get(Company, int(company_id))
    if not company:
        return {"status": "error", "message": f"Company with id {company_id} not found."}

    tasks = ProcessingTask.query.filter_by(company_id=company_id).all()
    for task in tasks:
        db.session.delete(task)
    db.session.commit()
    return {"status": "success", "message": f"All tasks for company {company_id} have been deleted."}


if __name__ == "__main__":
    import main
    with main.app.app_context():
        import random
        from models import Company

        if "y" in input("get list of task info? (y/n)").lower():
            companies = Company.query.all()
            for company in companies:
                result = get_company_task_statuses(company.id)
                print(f"Company {company.id}: " + str(result))
        
        if "y" in input("create video_render tasks for all companies without one? (y/n)").lower():
            companies = Company.query.all()
            id_list = []
            for company in companies:
                id_list.append(company.id)
            total = 0
            for id in id_list:
                temp = start_render_and_upload_if_not_exist(id)
                if temp["status"] == "created":
                    total += 1
            print(f"Processes turned on: {total}")

        if "y" in input("reset failed tasks as pending?").lower():
            from models import ProcessingTask
            from datetime import datetime
            failed_tasks = ProcessingTask.query.filter_by(status='failed').all()
            for task in failed_tasks:
                task.status = 'pending'
                task.updated_at = datetime.utcnow()
            db.session.commit()
            print(f"Reset {len(failed_tasks)} failed tasks to pending.")

        if "y" in input("reset in_progress tasks as pending?").lower():
            from models import ProcessingTask
            from datetime import datetime
            failed_tasks = ProcessingTask.query.filter_by(status='in_progress').all()
            for task in failed_tasks:
                task.status = 'pending'
                task.updated_at = datetime.utcnow()
            db.session.commit()
            print(f"Reset {len(failed_tasks)} failed tasks to pending.")
        
        if "y" in input("delete all tasks?").lower():
            from models import ProcessingTask
            tasks = ProcessingTask.query.all()
            for task in tasks:
                db.session.delete(task)
            db.session.commit()
            print(f"Deleted {len(tasks)} tasks.")
