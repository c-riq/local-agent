import subprocess
import importlib
import pydoc
import sys
from loguru import logger

def get_package_version(package_name):
    logger.info(f"Checking version of package '{package_name}'")
    result = subprocess.run([sys.executable, '-m', 'pip', 'show', package_name], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Failed to get version of package '{package_name}'")
        return None
    for line in result.stdout.split('\n'):
        if line.startswith('Version:'):
            logger.info(f"Found version: {line.split()[-1]}")
            return line.split()[-1]
    return None

def get_latest_version(package_name):
    logger.info(f"Checking if there's a newer version available for package '{package_name}'")
    result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--outdated', '--format=columns'], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Failed to check for newer versions of package '{package_name}'")
        return None
    for line in result.stdout.split('\n'):
        if line.startswith(package_name):
            latest_version = line.split()[2]
            logger.info(f"Newer version available: {latest_version}")
            return latest_version
    logger.info(f"No newer version available for package '{package_name}'")
    return None

def update_package(package_name):
    logger.info(f"Updating package '{package_name}' to the latest version")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', package_name])

def dynamic_import(package_name, method_path):
    logger.info(f"Importing '{method_path}' from package '{package_name}'")
    try:
        package = importlib.import_module(package_name)
        method = package
        for part in method_path.split('.')[1:]:
            method = getattr(method, part)
        return method
    except (ImportError, AttributeError) as e:
        logger.error(f"Error: Could not import method '{method_path}' from package '{package_name}'. {e}")
        return None

def inspect_method(package_name, method_path, init_args=None, class_instance=None, check_update=False):
    current_version = get_package_version(package_name)
    
    if not current_version:
        logger.error(f"Package '{package_name}' is not installed.")
        return

    logger.info(f"Current version of '{package_name}' is {current_version}.")

    if check_update:
        latest_version = get_latest_version(package_name)
        if latest_version and latest_version != current_version:
            logger.info(f"A newer version ({latest_version}) of '{package_name}' is available.")
            update = input("Do you want to update the package to the latest version? (yes/no): ").strip().lower()
            if update == 'yes':
                update_package(package_name)
                logger.info(f"Package '{package_name}' updated to the latest version.")
            else:
                logger.info("Proceeding with the current version.")
        else:
            logger.info("You have the latest version.")

    if class_instance:
        method = class_instance
        for part in method_path.split('.'):
            method = getattr(method, part)
    else:
        method = dynamic_import(package_name, method_path)
        if method is None:
            return

    if init_args and callable(method):
        try:
            instance = method(**init_args)
            method = instance
        except TypeError as e:
            logger.error(f"Error: Could not initialize method '{method_path}' with arguments {init_args}. {e}")
            return
    elif init_args and not callable(method):
        logger.error(f"Error: '{method_path}' is not callable and cannot be initialized with arguments {init_args}.")
        return

    # Use pydoc to get the documentation
    docs = pydoc.render_doc(method, "Help on %s")
    return docs

# Example usage with logging
from openai import OpenAI

client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama'
)

# Inspect the specific method on the instance
docs = inspect_method('openai', 'chat.completions.create', class_instance=client, check_update=False)
print(docs)

# Another example for a different package
docs = inspect_method('requests', 'requests.get', check_update=False)
print(docs)
