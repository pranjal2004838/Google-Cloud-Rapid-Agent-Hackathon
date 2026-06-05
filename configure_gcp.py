import os
import sys
import subprocess
import shutil
import re

# ANSI colors for nice console outputs
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_step(msg):
    print(f"\n{BLUE}{BOLD}==>{RESET} {BOLD}{msg}{RESET}")

def print_success(msg):
    print(f"  {GREEN}✓{RESET} {msg}")

def print_warning(msg):
    print(f"  {YELLOW}⚠{RESET} {msg}")

def print_error(msg):
    print(f"  {RED}✗{RESET} {msg}")

def run_cmd(args, check=True, capture_output=True):
    """Runs a shell command and returns the stdout and return code."""
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, args, result.stdout, result.stderr
            )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        if check:
            print_error(f"Failed to execute command: {' '.join(args) if isinstance(args, list) else args}")
            print_error(str(e))
            sys.exit(1)
        return "", -1

def check_gcloud():
    """Verify that gcloud CLI is installed and configured."""
    print_step("Checking gcloud CLI installation")
    if not shutil.which("gcloud"):
        print_error("gcloud CLI not found in PATH.")
        print_warning("Please install the Google Cloud SDK first: https://cloud.google.com/sdk/docs/install")
        sys.exit(1)
    
    # Check if user is authenticated
    try:
        accounts, _ = run_cmd("gcloud auth list --format=value(account)")
        if not accounts or len(accounts.strip()) == 0:
            print_error("No authenticated gcloud accounts found.")
            print_warning("Please run 'gcloud auth login' in your terminal before running this script.")
            sys.exit(1)
        active_account = accounts.splitlines()[0]
        print_success(f"Authenticated as {active_account}")
    except Exception:
        print_error("gcloud auth check failed.")
        print_warning("Please run 'gcloud auth login' and try again.")
        sys.exit(1)

def get_project():
    """Gets the active Google Cloud project ID."""
    print_step("Fetching active GCP project")
    project, code = run_cmd("gcloud config get-value project", check=False)
    if code != 0 or not project or project == "(unset)":
        print_error("No GCP project is currently set in gcloud config.")
        print_warning("Please run: gcloud config set project YOUR_PROJECT_ID")
        sys.exit(1)
    print_success(f"Active GCP project: {BOLD}{project}{RESET}")
    return project

def enable_apis():
    """Enables required GCP APIs."""
    apis = [
        "kms.googleapis.com",
        "pubsub.googleapis.com",
        "cloudtasks.googleapis.com",
        "storage.googleapis.com"
    ]
    print_step("Enabling required Google Cloud APIs")
    print(f"  Enabling APIs (this can take a minute): {', '.join(apis)}")
    run_cmd(f"gcloud services enable {' '.join(apis)}")
    print_success("All required APIs enabled successfully.")

def setup_gcs_bucket(project, location):
    """Creates a GCS bucket for uploads."""
    print_step("Configuring Google Cloud Storage")
    bucket_name = f"{project}-cliniqai-uploads"
    
    # Check if bucket already exists
    stdout, code = run_cmd(f"gcloud storage buckets describe gs://{bucket_name}", check=False)
    if code == 0:
        print_success(f"GCS bucket already exists: gs://{bucket_name}")
    else:
        print(f"  Creating GCS bucket: gs://{bucket_name} in {location}")
        # Standard buckets are regional, but us-central1 or asia-south1 can be specified
        run_cmd(f"gcloud storage buckets create gs://{bucket_name} --location={location}")
        print_success(f"GCS bucket created successfully: gs://{bucket_name}")
    
    return bucket_name

def setup_kms(project, location):
    """Creates KMS Keyring and CryptoKey."""
    print_step("Configuring Google Cloud KMS (Symmetric Encryption)")
    keyring = "cliniqai-keyring"
    key_name = "patient-data-key"
    
    # Check if keyring exists
    keyring_full = f"projects/{project}/locations/{location}/keyRings/{keyring}"
    _, keyring_code = run_cmd(f"gcloud kms keyrings describe {keyring} --location={location}", check=False)
    
    if keyring_code == 0:
        print_success(f"KMS Keyring already exists: {keyring}")
    else:
        print(f"  Creating KMS Keyring: {keyring} in {location}")
        run_cmd(f"gcloud kms keyrings create {keyring} --location={location}")
        print_success(f"KMS Keyring created: {keyring}")
        
    # Check if key exists
    _, key_code = run_cmd(
        f"gcloud kms keys describe {key_name} --location={location} --keyring={keyring}",
        check=False
    )
    
    if key_code == 0:
        print_success(f"KMS CryptoKey already exists: {key_name}")
    else:
        print(f"  Creating KMS CryptoKey: {key_name} (Purpose: encryption)")
        run_cmd(
            f"gcloud kms keys create {key_name} --location={location} --keyring={keyring} --purpose=encryption"
        )
        print_success(f"KMS CryptoKey created: {key_name}")
        
    return keyring, key_name

def setup_pubsub():
    """Creates Pub/Sub topic and subscription."""
    print_step("Configuring Cloud Pub/Sub")
    topic = "cliniqai-alerts"
    sub = "cliniqai-alerts-sub"
    
    # Check topic
    _, topic_code = run_cmd(f"gcloud pubsub topics describe {topic}", check=False)
    if topic_code == 0:
        print_success(f"Pub/Sub Topic already exists: {topic}")
    else:
        print(f"  Creating Pub/Sub Topic: {topic}")
        run_cmd(f"gcloud pubsub topics create {topic}")
        print_success(f"Pub/Sub Topic created: {topic}")
        
    # Check subscription
    _, sub_code = run_cmd(f"gcloud pubsub subscriptions describe {sub}", check=False)
    if sub_code == 0:
        print_success(f"Pub/Sub Subscription already exists: {sub}")
    else:
        print(f"  Creating Pub/Sub Subscription: {sub} bound to {topic}")
        run_cmd(f"gcloud pubsub subscriptions create {sub} --topic={topic}")
        print_success(f"Pub/Sub Subscription created: {sub}")
        
    return topic, sub

def setup_cloud_tasks(location):
    """Creates Cloud Tasks queue."""
    print_step("Configuring Cloud Tasks Queue")
    queue_name = "cliniqai-processing-queue"
    
    # Check queue
    _, queue_code = run_cmd(f"gcloud tasks queues describe {queue_name} --location={location}", check=False)
    if queue_code == 0:
        print_success(f"Cloud Tasks Queue already exists: {queue_name}")
    else:
        print(f"  Creating Cloud Tasks Queue: {queue_name} in {location}")
        # Sometimes Cloud Tasks requires an App Engine app or can be created directly.
        # Starting with gcloud tasks queues create:
        run_cmd(f"gcloud tasks queues create {queue_name} --location={location}")
        print_success(f"Cloud Tasks Queue created: {queue_name}")
        
    return queue_name

def update_env_file(project, location, bucket, keyring, key, topic, queue):
    """Updates cliniqai/.env with the created resources."""
    print_step("Updating cliniqai/.env file configuration")
    env_path = os.path.join("cliniqai", ".env")
    
    if not os.path.exists(env_path):
        print_warning(f".env file not found at {env_path}. Skipping update.")
        return
        
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Define variables to modify or add
    vars_to_set = {
        "GOOGLE_CLOUD_PROJECT": project,
        "GOOGLE_CLOUD_LOCATION": location,
        "GCS_UPLOAD_BUCKET": bucket,
        "KMS_KEY_RING": keyring,
        "KMS_KEY_NAME": key,
        "PUBSUB_ALERT_TOPIC": topic,
        "TASKS_QUEUE_NAME": queue
    }
    
    modified = False
    for var, val in vars_to_set.items():
        pattern = rf"^({var}\s*=.*)$"
        replacement = f"{var}={val}"
        
        if re.search(pattern, content, re.MULTILINE):
            content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
            if count > 0:
                modified = True
        else:
            # Append if it doesn't exist
            content += f"\n{var}={val}"
            modified = True
            
    if modified:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
        print_success(f"Successfully updated environment variables in {env_path}")
    else:
        print_success("No changes needed in .env file.")

def main():
    print(f"\n{BOLD}===================================================={RESET}")
    print(f"{GREEN}{BOLD}      CliniqAI GCP Configuration Setup Script       {RESET}")
    print(f"{BOLD}===================================================={RESET}")
    
    # 1. Verification
    check_gcloud()
    project_id = get_project()
    
    # Read location from cliniqai/.env or default to us-central1
    location = "us-central1"
    env_path = os.path.join("cliniqai", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GOOGLE_CLOUD_LOCATION"):
                    parts = line.strip().split("=")
                    if len(parts) > 1 and parts[1]:
                        location = parts[1].strip()
                        break
    
    print(f"Using location: {BOLD}{location}{RESET} (defined in .env)")
    
    # 2. Provisioning
    enable_apis()
    bucket_name = setup_gcs_bucket(project_id, location)
    keyring, key_name = setup_kms(project_id, location)
    topic, _ = setup_pubsub()
    queue = setup_cloud_tasks(location)
    
    # 3. Environment update
    update_env_file(project_id, location, bucket_name, keyring, key_name, topic, queue)
    
    print(f"\n{GREEN}{BOLD}Setup complete! All GCP services are now configured.{RESET}")
    print("You can run your FastAPI server with all production-grade features integrated.")
    print("Make sure you also deploy your container using 'gcloud run deploy' if launching live!\n")

if __name__ == "__main__":
    main()
