# cf_utils.py

import subprocess
import sys

def get_cf_apps():
    """
    Retrieves the list of app names from Cloud Foundry.
    """
    try:
        result = subprocess.run(['cf', 'apps'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error retrieving apps: {result.stderr}")
            sys.exit(1)

        apps_output = result.stdout
        app_names = []
        lines = apps_output.strip().split('\n')
        # Adjust the index based on your actual `cf apps` output
        for line in lines[4:]:  # Skipping header lines
            if line.strip():
                app_name = line.split()[0]
                app_names.append(app_name)
        return app_names
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
            git_url = input(f"Enter the Git URL for the new app '{app_name}': ").strip()
            apps_data[app_name] = git_url
    save_apps(apps_data)

# git_utils.py

import os
import subprocess
import logging

def clone_or_pull_repo(app_name, git_url, base_dir='repos'):
    """
    Clones the repository if it doesn't exist or pulls the latest changes if it does.
    """
    repo_path = os.path.join(base_dir, app_name)
    try:
        if not os.path.exists(repo_path):
            print(f"Cloning repository for {app_name}...")
            subprocess.run(['git', 'clone', git_url, repo_path], check=True)
        else:
            print(f"Pulling latest changes for {app_name}...")
            subprocess.run(['git', '-C', repo_path, 'pull'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Git command failed for {app_name}: {e}")
    return repo_path

# dependency_parser.py

import os

def find_dependency_files(repo_path, target_dir='dependencies'):
    """
    Searches for dependency files in the specified directory within the repo.
    """
    dependencies = set()
    dependency_dir = os.path.join(repo_path, target_dir)
    if os.path.exists(dependency_dir):
        for root, dirs, files in os.walk(dependency_dir):
            for file in files:
                file_path = os.path.join(root, file)
                deps = parse_dependency_file(file_path)
                dependencies.update(deps)
    else:
        print(f"No dependency directory found in {repo_path}")
    return dependencies

def parse_dependency_file(file_path):
    """
    Parses a dependency file and extracts dependencies.
    """
    deps = set()
    with open(file_path, 'r') as f:
        for line in f:
            dep = line.strip()
            if dep:
                deps.add(dep)
    return deps

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
from git_utils import clone_or_pull_repo
from dependency_parser import find_dependency_files
from dependency_utils import update_dependencies

def main():
    # Step 1: Get app names from Cloud Foundry
    app_names = get_cf_apps()
    if not app_names:
        print("No apps found.")
        return

    # Step 2: Update apps in the apps.json file
    update_apps(app_names)
    apps_data = load_apps()

    # Step 3: Process each app
    for app_name, git_url in apps_data.items():
        # Step 3a: Clone or pull the repository
        repo_path = clone_or_pull_repo(app_name, git_url)

        # Step 3b: Find and parse dependency files
        dependencies = find_dependency_files(repo_path)

        # Step 3c: Update dependencies in the dependencies.json file
        update_dependencies(app_name, dependencies)

if __name__ == "__main__":
    main()
