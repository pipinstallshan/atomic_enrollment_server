import aisuite
import json
import automation_manager


tools = [
    {
        "type": "function",
        "function": {
            "name": "start_rendering_and_uploading_process",
            "description": (
                "Starts rendering the custom video for each Lead in the list and uploads them to the integrated Google Drive account. "
                "This tool only starts the process which happens in the background and can take 10-40 minutes per video, one by one. "
                "By default, only the videos that don't exist yet will be rendered. If the user wants to rerender all videos like when the videos have a problem, use the rerender_all=True parameter."
                "Once a video is done rendering and uploading, the resulting Video URL (youtube or drive url) will be in the Lead's 'Custom YouTube Video' column."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "list_of_leads": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "IDs of the Leads for which the rendering and uploading process needs to be started"
                        },
                        "description": "List of Lead IDs to process"
                    },
                    "rerender_all": {
                        "type": "boolean",
                        "description": "If true, all videos will be rerendered and uploaded again, regardless of whether they already exist. If false (default), only the videos that don't exist yet will be rendered."
                    },
                },
                "additionalProperties": False,
                "required": ["list_of_leads", "rerender_all"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_csv_file",
            "description": (
                "Used to send the user a custom CSV file as per their specifications. How to use tool:\n"
                "If the user asks to download or export the selected Leads (maybe even with custom columns and column names), "
                "you can use this tool to rewrite the selected Leads into a CSV file and send it directly to the user. "
                "Make sure not to make mistakes while copying data over."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "csv_content": {
                        "type": "string",
                        "description": (
                            "The content of the CSV file, formatted as text. Example: 'header,header2\\nvalue1,value2\\n...'"
                        )
                    }
                },
                "additionalProperties": False,
                "required": ["csv_content"]
            }
        }
    },
    # {
    # "type": "function",
    # "function": {
    #     "name": "make_edit",
    #     "description": (
    #         "Updates data in the database and for the user. Use this tool if the user asked you to update data, etc. "
    #         "Only for selected Leads."
    #     ),
    #     "strict": True,
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "updates": {
    #             "type": "array",
    #             "description": "List of updates to apply to Leads.",
    #             "items": {
    #                 "type": "object",
    #                 "properties": {
    #                 "leadId": {
    #                     "type": "string",
    #                     "description": "The ID of the Lead to update."
    #                 },
    #                 "field": {
    #                     "type": "string",
    #                     "description": "The name of the field to be updated."
    #                 },
    #                 "overwrite_value": {
    #                     "type": "string",
    #                     "description": "The new value for the specified field."
    #                 }
    #                 },
    #                 "required": ["leadId", "field", "overwrite_value"],
    #                 "additionalProperties": False
    #             },
    #             "minItems": 1
    #             }
    #         },
    #         "required": ["updates"],
    #         "additionalProperties": False
    #         }
    #     }
    # }
]


def start_rendering_and_uploading_process(list_of_leads: list[str], rerender_all: bool):
    list_of_leads = [int(l) for l in list_of_leads]
    result = ""
    for lead_id in list_of_leads:
        
        from models import StructuredLead
        lead = StructuredLead.query.get(lead_id)
        if lead and lead.company_id:
            result += str(automation_manager.start_render_and_upload_if_not_exist(company_id=lead.company_id, rerender_all=rerender_all)) + "\n"
        else:
            result += f"Lead with id {lead_id} not found or has no company assigned.\n"
    return result


def send_csv_file(csv_content: str):
    import secrets
    hex_code = secrets.token_hex(16)
    with open("output/"+hex_code+".csv", "w") as file:
        file.write(csv_content)
    return f"new CSV file downloadable via 'https://atomic.steamlined.solutions/output/{hex_code}.csv'"  # TODO: make the link be relative to the URL that the user is on.
    

def make_edit(edits_json: dict[str, list[dict[str, str]]]):
    """
    Makes changes to multiple Leads at once

    Args:
    edits_json: {"updates": [{"leadId": "leadid", "field": "name", "overwrite_value": "new value"}, ...]}
    """
    # Get the database session
    from models import Lead, LeadData
    from main import db

    edits_json = {lead_id: [{"field": u["field"], "value": u["overwrite_value"]} for u in edits_json["updates"] if u["leadId"] == lead_id] for lead_id in {u["leadId"] for u in edits_json["updates"]}}
    #  {"leadid": [{"field": "new value", "field2": "new value"}]}

    # Process each lead's edits
    for lead_id, edits in edits_json.items():
        # Get the lead
        lead = db.session.get(Lead, int(lead_id))
        if not lead:
            continue

        # Apply each edit
        for edit in edits:
            field_name = edit["field"]
            new_value = edit["value"]
            
            # Create new LeadData entry
            lead_data = LeadData(
                lead_id=lead.id,
                field_name=field_name,
                field_value=new_value
            )
            db.session.add(lead_data)

    # Commit all changes
    try:
        db.session.commit()
        return 'Successfully updated leads'
    except Exception as e:
        db.session.rollback()
        return f'Error updating leads: {str(e)}'


tool_call_dict = {
    "start_rendering_and_uploading_process": start_rendering_and_uploading_process,
    "send_csv_file": send_csv_file,
    "make_edit": make_edit
}



def respond(messages: list, selected_leads:list, depth=0):
    if depth > 2:
        return messages

    from models import Lead
    from main import db
    selected_leads_string = ""
    for lead_id in selected_leads:
        lead = db.session.get(Lead, int(lead_id))
        if lead:
            selected_leads_string += str(lead.to_dict()) + "\n"
    
    from models import ExportTemplate
    exporting_templates_string = ""
    for t in ExportTemplate.query.all():
        exporting_templates_string += f"Template {t.id} ({t.name}): {t.get_columns()}\n"

    prompt = f"""You are a AI Agent that the user talks to to manage their database of Leads and maybe other datatypes.
    You have many tools and intelligently use them to do the users requests.
    You do not see the full database. You only see the Leads that the user selected and you are only allowed to make edits on the selected Leads.
    This is for safety. You can only write to data entries that are selected for safety.
    You can always talk to the user to inform him/her on things that go wrong or maybe they didn't understand.

    Currently selected Leads:
    ```
    {selected_leads_string}
    ```
    Note that earlier in the conversation the user might have had other Leads selected than these, however you can not see them. You can only see the ones that are selected at the very last point of this ongoing conversation.

    When asking to export the user can reference an export template, which are the columns you should use when exporting. A list of all templates are here:
    ```
    {exporting_templates_string}
    ```

"""
    
    response = aisuite.Client().chat.completions.create(
        model="openai:gpt-4o", 
        messages=[{"role": "system", "content": prompt}] + messages, 
        tools=tools,
        temperature=0
    )
    messages.append(response.choices[0].message)
    if response.choices[0].message.tool_calls:

        for call in response.choices[0].message.tool_calls:
            args = json.loads(call.function.arguments)
        
            function = tool_call_dict[call.function.name]

            tool_call_result = function(**args)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(tool_call_result)
            })
        messages = respond(messages=messages, selected_leads=selected_leads, depth=depth+1)
    
    messages = [json.loads(m.model_dump_json()) if not isinstance(m, dict) else m for m in messages]
    return messages

if __name__ == "__main__":
    mess = []
    while True:
        mess.append({"role": "user", "content": input("> ")})
        mess = respond(mess, [25, 26, 27])
        
        print(mess[-1]["content"])
        print(type(mess[-1]))
    
