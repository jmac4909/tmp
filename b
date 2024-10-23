# cf_utils.py

import subprocess
import sys
import os

def get_cf_apps():
    """
    Retrieves the list of app names from all orgs and spaces in Cloud Foundry.
    """
    try:
        # Set the HOMEDRIVE environment variable to 'C:'
        os.environ['HOMEDRIVE'] = 'C:'

        # Get the list of orgs
        orgs_result = subprocess.run(['cf', 'orgs'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if orgs_result.returncode != 0:
            print(f"Error retrieving orgs: {orgs_result.stderr}")
            sys.exit(1)

        orgs_output = orgs_result.stdout
        org_names = []
        lines = orgs_output.strip().split('\n')

        # Adjust index based on actual output
        for line in lines[3:]:
            org_name = line.strip()
            if org_name:
                org_names.append(org_name)

        all_app_names = []

        for org in org_names:
            # Target the org
            target_org_result = subprocess.run(['cf', 'target', '-o', org], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if target_org_result.returncode != 0:
                print(f"Error targeting org {org}: {target_org_result.stderr}")
                continue  # Skip to the next org

            # Get the list of spaces in this org
            spaces_result = subprocess.run(['cf', 'spaces'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if spaces_result.returncode != 0:
                print(f"Error retrieving spaces in org {org}: {spaces_result.stderr}")
                continue  # Skip to the next org

            spaces_output = spaces_result.stdout
            space_names = []
            lines = spaces_output.strip().split('\n')

            for line in lines[3:]:
                space_name = line.strip()
                if space_name:
                    space_names.append(space_name)

            for space in space_names:
                # Target the org and space
                target_space_result = subprocess.run(['cf', 'target', '-o', org, '-s', space], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if target_space_result.returncode != 0:
                    print(f"Error targeting space {space} in org {org}: {target_space_result.stderr}")
                    continue  # Skip to the next space

                # Get the apps in this space
                apps_result = subprocess.run(['cf', 'apps'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if apps_result.returncode != 0:
                    print(f"Error retrieving apps in org {org}, space {space}: {apps_result.stderr}")
                    continue  # Skip to the next space

                apps_output = apps_result.stdout
                lines = apps_output.strip().split('\n')

                for line in lines[4:]:
                    if line.strip():
                        app_name = line.split()[0]
                        all_app_names.append(app_name)

        return all_app_names
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

# app_utils.py

import json
import os

APPS_FILE = 'apps.json'

def load_apps():
    """
    Loads the apps data from the JSON file.
    """
    if os.path.exists(APPS_FILE):
        with open(APPS_FILE, 'r') as f:
            return json.load(f)
    else:
        return {}

def save_apps(apps_data):
    """
    Saves the apps data to the JSON file.
    """
    with open(APPS_FILE, 'w') as f:
        json.dump(apps_data, f, indent=4)

def update_apps(app_names):
    """
    Updates the apps data by adding new apps and prompting for their Git URLs.
    """
    apps_data = load_apps()
    for app_name in app_names:
        if app_name not in apps_data:
            # Use the placeholder URL
            placeholder_url = f"cloud.com/{app_name}"
            git_url = input(f"Enter the Git URL for the new app '{app_name}' (e.g., {placeholder_url}): ").strip()
            apps_data[app_name] = git_url
    save_apps(apps_data)

# dependency_parser.py

import os
import urllib.request
import urllib.parse
import json

def fetch_dependency_files(app_name, git_url, target_dir='dependencies', private_token=None):
    """
    Fetches dependency files from the repository using the GitLab API.
    """
    dependencies = set()

    # Extract repository information from the git_url
    repo_path = extract_repo_path(git_url)

    # Build the API URL
    api_url = f"https://gitlab.com/api/v4/projects/{urllib.parse.quote(repo_path, safe='')}"

    # Prepare the request headers
    headers = {}
    if private_token:
        headers['PRIVATE-TOKEN'] = private_token

    # Get a list of files in the target directory
    tree_url = f"{api_url}/repository/tree?path={urllib.parse.quote(target_dir)}&recursive=true"
    request = urllib.request.Request(tree_url, headers=headers)

    try:
        with urllib.request.urlopen(request) as response:
            if response.status != 200:
                print(f"Error fetching file list from {git_url}: {response.status}")
                return dependencies

            files = json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching file list from {git_url}: {e}")
        return dependencies

    for file_info in files:
        if file_info['type'] == 'blob':
            file_path = file_info['path']
            # Fetch the file content
            file_url = f"{api_url}/repository/files/{urllib.parse.quote(file_path, safe='')}/raw?ref=master"  # Adjust branch if necessary
            file_request = urllib.request.Request(file_url, headers=headers)
            try:
                with urllib.request.urlopen(file_request) as file_response:
                    if file_response.status == 200:
                        file_content = file_response.read().decode()
                        deps = parse_dependency_content(file_content)
                        dependencies.update(deps)
                    else:
                        print(f"Error fetching file {file_path}: {file_response.status}")
            except Exception as e:
                print(f"Error fetching file {file_path}: {e}")

    return dependencies

def parse_dependency_content(file_content):
    """
    Parses the content of a dependency file and extracts dependencies.
    """
    deps = set()
    for line in file_content.splitlines():
        dep = line.strip()
        if dep:
            deps.add(dep)
    return deps

def extract_repo_path(git_url):
    """
    Extracts the repository path from the Git URL.
    """
    if git_url.startswith('git@'):
        # git@gitlab.com:user/repo.git
        repo_path = git_url.replace('git@gitlab.com:', '').replace('.git', '')
    elif git_url.startswith('https://'):
        # https://gitlab.com/user/repo.git
        repo_path = git_url.replace('https://gitlab.com/', '').replace('.git', '')
    else:
        # Placeholder URL or other format
        repo_path = git_url.replace('cloud.com/', '')
    return repo_path
# dependency_utils.py

import json
import os

DEPS_FILE = 'dependencies.json'

def load_dependencies():
    """
    Loads the dependencies data from the JSON file.
    """
    if os.path.exists(DEPS_FILE):
        with open(DEPS_FILE, 'r') as f:
            return json.load(f)
    else:
        return {}

def save_dependencies(deps_data):
    """
    Saves the dependencies data to the JSON file.
    """
    with open(DEPS_FILE, 'w') as f:
        json.dump(deps_data, f, indent=4)

def update_dependencies(app_name, dependencies):
    """
    Updates the dependencies data by adding new dependencies and prompting if necessary.
    """
    deps_data = load_dependencies()
    existing_deps = set(deps_data.get(app_name, []))
    new_deps = dependencies - existing_deps
    for dep_name in new_deps:
        create_dep = input(f"Dependency '{dep_name}' not found for app '{app_name}'. Do you want to create it? (y/n): ").strip().lower()
        if create_dep == 'y':
            existing_deps.add(dep_name)
    deps_data[app_name] = list(existing_deps)
    save_dependencies(deps_data)
# main.py

from cf_utils import get_cf_apps
from app_utils import update_apps, load_apps
from dependency_parser import fetch_dependency_files
from dependency_utils import update_dependencies
import os

def main():
    # Step 1: Get app names from Cloud Foundry
    app_names = get_cf_apps()
    if not app_names:
        print("No apps found.")
        return

    # Remove duplicates if any
    app_names = list(set(app_names))

    # Step 2: Update apps in the apps.json file
    update_apps(app_names)
    apps_data = load_apps()

    # Add your GitLab personal access token if required
    private_token = os.getenv('GITLAB_PRIVATE_TOKEN')  # Replace with your token or set to None if not needed

    # Step 3: Process each app
    for app_name, git_url in apps_data.items():
        # Fetch and parse dependency files directly from GitLab
        dependencies = fetch_dependency_files(app_name, git_url, private_token=private_token)

        # Update dependencies in the dependencies.json file
        update_dependencies(app_name, dependencies)

if __name__ == "__main__":
    main()
