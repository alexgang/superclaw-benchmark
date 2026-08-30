import json
from datetime import datetime

# Read the input file
with open('/workspace/todos.json', 'r') as f:
    data = json.load(f)

todos = data['todos']
reference_date = datetime.strptime(data['reference_date'], '%Y-%m-%d')

# Step 1: Identify duplicates based on semantic similarity
# Define groups of semantically similar tasks
# Group 1: Write unit tests (auth module)
# Group 2: Update README (setup instructions/steps)
# Group 3: Fix login bug (mobile)
# Group 4: Set up CI/CD pipeline (continuous integration)

def get_semantic_group(todo):
    """Categorize a todo into its semantic group"""
    title = todo['title'].lower()
    
    # Group 1: Write unit tests for auth module
    if 'unit tests' in title and ('auth' in title or 'authentication' in title):
        return 'unit_tests_auth'
    
    # Group 2: Update README with setup instructions/steps
    if 'readme' in title and ('update' in title or 'setup' in title):
        return 'readme_setup'
    
    # Group 3: Fix login bug on mobile
    if 'login' in title and ('bug' in title or 'fix' in title) and ('mobile' in title or 'mobile' in title):
        return 'mobile_login_bug'
    
    # Group 4: Set up CI/CD pipeline / continuous integration
    if ('ci' in title or 'cd' in title or 'continuous integration' in title or 'pipeline' in title):
        return 'ci_cd_pipeline'
    
    return None

# Group todos by semantic category
semantic_groups = {}
for todo in todos:
    group = get_semantic_group(todo)
    if group:
        if group not in semantic_groups:
            semantic_groups[group] = []
        semantic_groups[group].append(todo)

# Mark duplicates (keep lowest id as canonical)
for group, group_todos in semantic_groups.items():
    # Sort by id to find the canonical (lowest id)
    sorted_group = sorted(group_todos, key=lambda x: x['id'])
    canonical_id = sorted_group[0]['id']
    
    for todo in sorted_group:
        if todo['id'] != canonical_id:
            # This is a duplicate, mark as completed
            todo['status'] = 'completed'

# Step 2: Flag overdue items
# For pending items with due_date before reference_date
for todo in todos:
    if todo['status'] == 'pending':
        due_date = datetime.strptime(todo['due_date'], '%Y-%m-%d')
        if due_date < reference_date:
            todo['overdue'] = True
        else:
            # Remove overdue field if it exists and date is not before reference
            if 'overdue' in todo:
                del todo['overdue']

# Step 3: Organize by project
projects = {}
for todo in todos:
    project = todo['project']
    if project not in projects:
        projects[project] = []
    projects[project].append(todo)

# Build output
output = {'projects': projects}

# Write to file
with open('/workspace/todos_cleaned.json', 'w') as f:
    json.dump(output, f, indent=2)

print("Cleanup complete. Output written to /workspace/todos_cleaned.json")
