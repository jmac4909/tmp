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

        # Skip header lines (adjust based on actual output)
        # Typically, the first 3 lines are headers
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

            # Skip header lines (adjust based on actual output)
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

                # Skip header lines (adjust based on actual output)
                for line in lines[4:]:
                    if line.strip():
                        app_name = line.split()[0]
                        all_app_names.append(app_name)

        return all_app_names
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
