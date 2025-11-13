import os


def unified_sort(items, path):
    """
    Sorts items with directories first, then alphabetically.

    Args:
        items: A list of file and directory names.
        path: The path to the directory containing these items.

    Returns:
        A new list with items sorted as per the requirements.
    """
    
    dirs = []
    files = []
    for item in items:
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            dirs.append(item)
        else:
            files.append(item)
    
    dirs.sort()
    files.sort()

    return dirs + files



def display_project_structure(path, project_root, ignored_items=None, indent="", structure_string=""):
    """
    Displays the project structure in a terminal-like tree format,
    respecting the ignored items, and returns the structure as a string.

    Args:
        path: The path to the directory you want to display the structure for.
        project_root: The root path of the project.
        ignored_items: A list of items (files or directories) to ignore.
        indent: The current indentation level (used for recursion).
        structure_string: The string accumulating the structure (used for recursion).

    Returns:
        The project structure as a formatted string.
    """
    if ignored_items is None:
        ignored_items = []

    if os.path.isfile(path):
        structure_string += indent + os.path.basename(path) + "\n"
        return structure_string

    try:
        items = os.listdir(path)
    except PermissionError:
        structure_string += indent + "└── [Permission Denied]\n"
        return structure_string

    items = [
        item
        for item in items
        if item not in ignored_items and (not item.startswith(".") or item == ".gitignore" or item == ".env")
    ]
    items = unified_sort(items, path)

    for i, item in enumerate(items):
        item_path = os.path.join(path, item)
        is_last_item = i == len(items) - 1

        if is_last_item:
            prefix = indent + "└── "
            new_indent = indent + "    "
        else:
            prefix = indent + "├── "
            new_indent = indent + "│   "

        structure_string += prefix + item + "\n"

        if os.path.isdir(item_path):
            structure_string = display_project_structure(
                item_path, project_root, ignored_items, new_indent, structure_string
            )

    return structure_string

def process_file_content(file_path):
    """
    Processes the content of a Python file, replacing sections between
    `# project_printer:ignore_start` and `# project_printer:ignore_end` with
    ...truncated code...

    Args:
        file_path: The path to the Python file.

    Returns:
        A string containing the processed file content.
    """
    processed_lines = []
    in_ignore_block = False
    ignore_replaced = False  # To avoid multiple replacements in the same block

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped_line = line.strip()
                if stripped_line == "# project_printer:ignore_start":
                    in_ignore_block = True
                    if not ignore_replaced:
                        processed_lines.append("# truncated code\n")
                        ignore_replaced = True
                    continue  # Skip the ignore_start line
                elif stripped_line == "# project_printer:ignore_end":
                    in_ignore_block = False
                    continue  # Skip the ignore_end line

                if not in_ignore_block:
                    processed_lines.append(line)
    except Exception as e:
        return f"# Error processing file: {e}\n"

    return ''.join(processed_lines)


def print_project_structure_and_code(project_path, ignored_items=None, output_file=None, list_of_truncated_files=None):
    """
    Writes the project structure and the content of each Python file
    to the specified output file, always displaying the relative path for each file.
    Replaces ignored sections with '# truncated code'.

    Args:
        project_path: The path to the root of the project.
        ignored_items: A list of file or folder names to be ignored.
        output_file: A file object to write the output to.
    """
    if ignored_items is None:
        ignored_items = ["venv"]  # Default to ignoring the "venv" folder
    if list_of_truncated_files is None:
        list_of_truncated_files = []

    basic_project_structure = display_project_structure(project_path, project_path, ignored_items=ignored_items)
    current_root_folder_name = os.path.basename(os.path.abspath(project_path))
    print(
        "First the basic project structure:\n========== START OF BASIC PROJECT STRUCTURE ==========\n\n"
        + current_root_folder_name
        + "\n"
        + basic_project_structure
        + "\n\n========== END OF BASIC PROJECT STRUCTURE ==========\n\n========== START OF FULL CODE BASE ==========",
        file=output_file,
    )

    def process_directory(path, relative_path, level):
        """
        Processes a directory, prints its structure, and then processes its contents.

        Args:
            path: The absolute path to the directory.
            relative_path: The path of the directory relative to the project root.
            level: The depth level of the directory in the project structure.
        """
        indent = " " * 4 * level
        print(f"{indent}📁{relative_path}", file=output_file)

        try:
            items = os.listdir(path)
        except PermissionError:
            print(f"{indent}    [Permission Denied]", file=output_file)
            return

        items = [item for item in items if item not in ignored_items and (not item.startswith(".") or item == ".gitignore" or item == ".env")]
        items = unified_sort(items, path)

        for item in items:
            item_path = os.path.join(path, item)
            item_relative_path = os.path.join(relative_path, item) if relative_path else item

            if os.path.isdir(item_path):
                process_directory(item_path, item_relative_path, level + 1)
            else:
                if (
                    item.endswith((".py", ".md", ".html", ".css", ".js"))
                    or item in (".gitignore", "requirements.txt", ".env")
                ) and item not in ignored_items:
                    print(f"{indent}└───{item_relative_path}:", file=output_file)
                    try:
                        processed_content = process_file_content(item_path)
                        
                        if item_relative_path not in list_of_truncated_files:
                            print(f"{indent}    <file path='{item_relative_path}'>\n===== START OF {item_relative_path} =====", file=output_file)
                            print(f"{indent}        ```", file=output_file)
                            print(processed_content, end="", file=output_file)
                            print(f"{indent}        ```", file=output_file)
                            print(f"===== END OF {item_relative_path} =====\n{indent}    </file path='{item_relative_path}'>", file=output_file)

                        else:
                            print(f"...{item_relative_path}: {processed_content.count('\n')} lines of content truncated because deemed irrelevant for the task. Use tools to read the content if necessary...", file=output_file)
                    except Exception as e:
                        print(f"{indent}        Error reading file: {e}", file=output_file)
                elif item not in ignored_items:
                    print(f"{indent}└───{item_relative_path}", file=output_file)

    # Start processing from the project root
    process_directory(project_path, "", 0)

    print("\n========== END OF FULL CODE BASE ==========", file=output_file)



def main(list_of_truncated_files: list=None):
    project_root = "."  # Set to your project's root directory
    ignore_list = [
        "venv", "__pycache__", ".git", ".idea", "project_printer.py", "project.txt",
        "AI_Coding_Agent.py", ".DS_Store", "temp_test.py", "AI_Coding_Planner.py", "coding_agent_conv.txt"
    ]
    

    # Open 'project.txt' in write mode to overwrite existing content
    with open("temp/project.txt", "w", encoding="utf-8") as f:
        print_project_structure_and_code(project_root, ignore_list, f, list_of_truncated_files=list_of_truncated_files)
    
    with open("temp/project.txt", "r", encoding="utf-8") as f:
        project_content = f.read()
    return project_content
    


if __name__ == "__main__":
    objective = input("Objective: ")
    if not objective:
        main()
        quit()
    import google.generativeai as genai
    import dotenv
    dotenv.load_dotenv()
    def generate_text(prompt, messages: list[dict]=[], model="gemini-2.0-flash-exp"):
        """
        Generates text using the Gemini model.

        Args:
            prompt (str): The prompt to generate text from.

        Returns:
            str: The generated text.
        """
        retries = 5
        for x in range(retries):
            if model.startswith("gemini"):
                gemini_model = genai.GenerativeModel(
                    model_name=model,
                )
                messages.insert(0, {"role": "user", "parts": prompt})
                response = gemini_model.generate_content(messages)
                return response.text


    code_base = main()
    truncated_files_response = generate_text(prompt="""We are about to start a coding task and try to achieve the objective below using our tools like a file editing tool and a code intepreter tool.
                                             
To solve this objective we will likely need to read some of the codebase to fully understand how we can achieve the objective and how all the things interact with each other.
However, we do not want to read completely unnecessary code, that will be completely irrelevant to our goal to save time.
> Your job is to identify all files that are completely irrelevant for solving the task and list their relative paths in a list.

Only truncate files that are of Zero value to the task. It's better to keep a few too many even if they only help a little bit.
Especially small files with only a few lines or no lines can be included.

It's recommended to first think about what information would help to solve the task, and then for each file, decide it's contents are completely irrelavant or if they are at least somewhat helpful.

<example>
    <objective>
tell me what 2^37 is using the python executer.
    </objective>
    <codebase>
```
TaskManager/
├── tasks.json
├── task_manager.py
├── utils.py
└── README.md
```

**task_manager.py:**

```python
import json
from utils import get_next_task_id

def load_tasks(filepath="tasks.json"):
    with open(filepath, 'r') as f:
        tasks = json.load(f)
    return tasks

def save_tasks(tasks, filepath="tasks.json"):
    with open(filepath, 'w') as f:
        json.dump(tasks, f, indent=4)

def add_task(description, filepath="tasks.json"):
    tasks = load_tasks(filepath)
    new_id = get_next_task_id(tasks)
    new_task = {"id": new_id, "description": description, "status": "incomplete"}
    tasks.append(new_task)
    save_tasks(tasks, filepath)
    print(f"Task '{description}' added successfully.")

def complete_task(task_id, filepath="tasks.json"):
    tasks = load_tasks(filepath)
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = "complete"
            save_tasks(tasks, filepath)
            print(f"Task {task_id} marked as complete.")
            return
    print(f"Task {task_id} not found.")

def list_tasks(filepath="tasks.json"):
    \"\"\"Lists all tasks.\"\"\"
    tasks = load_tasks(filepath)
    if not tasks:
        print("No tasks found.")
        return
    for task in tasks:
        print(f"ID: {task['id']}, Description: {task['description']}, Status: {task['status']}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manage your tasks.")
    parser.add_argument("action", choices=["add", "complete", "list"], help="Action to perform (add, complete, list).")
    parser.add_argument("--desc", help="Task description (for add action).")
    parser.add_argument("--id", type=int, help="Task ID (for complete action).")

    args = parser.parse_args()

    if args.action == "add":
        if args.desc:
            add_task(args.desc)
        else:
            print("Error: Task description is required for adding a task.")
    elif args.action == "complete":
        if args.id:
            complete_task(args.id)
        else:
            print("Error: Task ID is required for completing a task.")
    elif args.action == "list":
        list_tasks()
```

**utils.py:**

```python
def get_next_task_id(tasks):
    if not tasks:
        return 1
    return max(task["id"] for task in tasks) + 1
```

README.md:
```
This project manages Tasks.
You can add a new task using:
task_manager.py add  --desc <your description of the task>

Hope this helps you manage your day better :D
```
</codebase>
<output>
The objective involves using tools to calculate a number and seems completely seperate from this code base. Maybe I will leave in the Readme.md so that they still have an idea of what the codebase is about even if its quite irrelevant for solving the objective.

list of files that can be ignored:
```json
["tasks.json", "task_manager.py", "utils.py"]
```
</output>
</example>

<example>
    <objective>
        Add a new feature to the task_manager that allows users to delete a task using the command line interface. Tasks are identified by their ID for deletion.
    </objective>
    <codebase>
```
TaskManager/
├── tasks.json
├── task_manager.py
├── utils.py
└── README.md
```

**task_manager.py:**

```python
import json
from utils import get_next_task_id

def load_tasks(filepath="tasks.json"):
    with open(filepath, 'r') as f:
        tasks = json.load(f)
    return tasks

def save_tasks(tasks, filepath="tasks.json"):
    with open(filepath, 'w') as f:
        json.dump(tasks, f, indent=4)

def add_task(description, filepath="tasks.json"):
    tasks = load_tasks(filepath)
    new_id = get_next_task_id(tasks)
    new_task = {"id": new_id, "description": description, "status": "incomplete"}
    tasks.append(new_task)
    save_tasks(tasks, filepath)
    print(f"Task '{description}' added successfully.")

def complete_task(task_id, filepath="tasks.json"):
    tasks = load_tasks(filepath)
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = "complete"
            save_tasks(tasks, filepath)
            print(f"Task {task_id} marked as complete.")
            return
    print(f"Task {task_id} not found.")

def list_tasks(filepath="tasks.json"):
    \"\"\"Lists all tasks.\"\"\"
    tasks = load_tasks(filepath)
    if not tasks:
        print("No tasks found.")
        return
    for task in tasks:
        print(f"ID: {task['id']}, Description: {task['description']}, Status: {task['status']}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manage your tasks.")
    parser.add_argument("action", choices=["add", "complete", "list"], help="Action to perform (add, complete, list).")
    parser.add_argument("--desc", help="Task description (for add action).")
    parser.add_argument("--id", type=int, help="Task ID (for complete action).")

    args = parser.parse_args()

    if args.action == "add":
        if args.desc:
            add_task(args.desc)
        else:
            print("Error: Task description is required for adding a task.")
    elif args.action == "complete":
        if args.id:
            complete_task(args.id)
        else:
            print("Error: Task ID is required for completing a task.")
    elif args.action == "list":
        list_tasks()
```

**utils.py:**

```python
def get_next_task_id(tasks):
    if not tasks:
        return 1
    return max(task["id"] for task in tasks) + 1
```

**README.md:**

```
This project manages Tasks.
You can add a new task using:
task_manager.py add  --desc <your description of the task>

Hope this helps you manage your day better :D
```
</codebase>
<output>
The objective requires adding functionality to delete tasks, which involves understanding how tasks are stored, accessed, modified, and how the command-line interface works. Additionally, understanding existing functionalities and how new features might integrate is crucial. Therefore, all files in this codebase are relevant for solving the objective, as they contribute to understanding the system's operation, data management, and user interaction. The README is important as it gives an overview over all the features. The task.json will have to be updated to remove the task, the task_manager.py is responsible for the logic and the utils.py will have to be understood since it will probably interact with task_manager.py.

list of files that can be ignored:
```json
[]
```
</output>
</example>
<example>
    <objective>
        Modify the existing `generateReport` function in `report_generator.py` to include the average order value in the generated sales reports.
    </objective>
    <codebase>
```
ECommercePlatform/
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── scripts.js
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── orders.py
│   │   └── products.py
│   ├── reports/
│   │   ├── __init__.py
│   │   └── report_generator.py
│   ├── utils.py
│   └── main.py
├── tests/
│   ├── test_orders.py
│   └── test_reports.py
└── README.md
```

**frontend/index.html:**

```html
<!DOCTYPE html>
<html>
<head>
    <title>E-Commerce Platform</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <h1>Welcome to Our Store</h1>
    <div id="products"></div>
    <script src="scripts.js"></script>
</body>
</html>
```

**frontend/styles.css:**

```css
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f4f4f4;
}

h1 {
    text-align: center;
    color: #333;
}

#products {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    padding: 20px;
}
```

**frontend/scripts.js:**

```javascript
document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/products')
        .then(response => response.json())
        .then(products => {
            const productsDiv = document.getElementById('products');
            products.forEach(product => {
                const productElement = document.createElement('div');
                productElement.innerHTML = `<h3>${product.name}</h3><p>${product.price}</p>`;
                productsDiv.appendChild(productElement);
            });
        });
});
```

**backend/api/orders.py:**

```python
from flask import Blueprint, jsonify

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/orders')
def get_orders():
    orders = [
        {"id": 1, "product": "Laptop", "price": 1200},
        {"id": 2, "product": "Mouse", "price": 25}
    ]
    return jsonify(orders)
```

**backend/api/products.py:**

```python
from flask import Blueprint, jsonify

products_bp = Blueprint('products', __name__)

@products_bp.route('/products')
def get_products():
    products = [
        {"id": 1, "name": "Laptop", "price": 1200},
        {"id": 2, "name": "Mouse", "price": 25}
    ]
    return jsonify(products)
```

**backend/reports/report_generator.py:**

```python
def generate_report(orders):
    \"\"\"Generates a sales report.\"\"\"
    total_sales = sum(order['price'] for order in orders)
    report = f"Total Sales: {total_sales}"
    return report
```

**backend/utils.py:**

```python
def calculate_tax(price, tax_rate=0.07):
    \"\"\"Calculates the tax for a given price.\"\"\"
    return price * tax_rate
```

**backend/main.py:**

```python
from flask import Flask
from api.orders import orders_bp
from api.products import products_bp

app = Flask(__name__)
app.register_blueprint(orders_bp, url_prefix='/api')
app.register_blueprint(products_bp, url_prefix='/api')

if __name__ == '__main__':
    app.run(debug=True)
```

**tests/test_orders.py:**

```python
import unittest
from backend.api.orders import get_orders

class TestOrdersAPI(unittest.TestCase):
    def test_get_orders(self):
        \"\"\"Test the get_orders API endpoint.\"\"\"
        response = get_orders()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json) > 0)

if __name__ == '__main__':
    unittest.main()
```

**tests/test_reports.py:**

```python
import unittest
from backend.reports.report_generator import generate_report

class TestReportGenerator(unittest.TestCase):
    def test_generate_report(self):
        \"\"\"Test the generate_report function.\"\"\"
        orders = [{"id": 1, "product": "Laptop", "price": 1200}]
        report = generate_report(orders)
        self.assertIn("Total Sales: 1200", report)

if __name__ == '__main__':
    unittest.main()
```

**README.md:**

```
# E-Commerce Platform

This is a simple e-commerce platform with a frontend and a backend.

## Running the Application

1. Ensure you have Python 3 installed.
2. Run `python backend/main.py` to start the backend server.
3. Open `frontend/index.html` in your browser to view the frontend.
```
</codebase>
<output>
The objective is to modify the `generateReport` function to include the average order value in the generated sales reports. This task primarily involves understanding how reports are generated and how order data is accessed and processed within the backend.

Let's consider each file:

-   **frontend/index.html**: This file defines the structure of the frontend's main page. It's completely irrelevant to the objective, which is focused on backend report generation.
-   **frontend/styles.css**: This file contains styles for the frontend. It has no bearing on the backend logic for report generation and is thus irrelevant.
-   **frontend/scripts.js**: This file handles frontend interactions, such as fetching and displaying products. It does not interact with the report generation logic and is irrelevant to the objective.
-   **backend/api/orders.py**: This file defines an API endpoint for retrieving orders. While it shows the structure of order data, it's not directly involved in the report generation process. However, understanding the order structure might be helpful, so it's not entirely irrelevant.
-   **backend/api/products.py**: This file defines an API endpoint for products. It's unrelated to report generation and can be considered irrelevant.
-   **backend/reports/report_generator.py**: This file contains the `generateReport` function, which is the direct target of the objective. It is highly relevant.
-   **backend/reports/__init__.py**: This file likely initializes the reports module. While it doesn't contain logic, it's part of the module structure and might be helpful to understand how the module is organized.
-   **backend/utils.py**: This file contains utility functions, such as tax calculation. These are not directly related to report generation, but might be helpful to understand general backend logic.
-   **backend/main.py**: This file sets up the Flask application and registers blueprints. It's not directly involved in report generation but is crucial for the application's overall structure.
-   **tests/test_orders.py**: This file contains tests for the orders API. While not directly related to `generateReport`, it demonstrates how tests are structured in the project, which can be helpful for writing tests for the modified function. Therefore, it's somewhat relevant.
-   **tests/test_reports.py**: This file tests the `generateReport` function. It's highly relevant as it shows how the function is currently tested and will likely need to be updated to reflect the changes.
-   **README.md**: This file provides an overview of the project and instructions on running the application. It's not directly related to the objective's logic but can be helpful for understanding the project setup.

Based on this analysis, only the frontend files are truly 100% irrelevant to the objective, as they deal with the client-side and do not interact with the backend report generation logic.

list of files that can be ignored:
```json
["frontend/index.html", "frontend/styles.css", "frontend/scripts.js"]
```
</output>
</example>


End of examples.

# Implementation
"""+f"""
Objective: "{objective}"

""" + code_base + f"""

Now please think about which files can safely be ignored when solving the objective ("{objective}").
You need to go through all files in the order they are presented to you and for each, debate if they are completely irrelevant or at least slightly helpful.

After that ordered list you write the list of truncated files.""")
    

    def parse_truncated_files_response(response):
        """Parse the response looking for json list of files to ignore"""
        import json
        import re
        
        # Find content between ```json and ``` using regex
        pattern = r'```json\s*(.*?)\s*```'
        match = re.search(pattern, response, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return []
        return []

    truncated_files: list = parse_truncated_files_response(truncated_files_response)
    
    main(truncated_files)


