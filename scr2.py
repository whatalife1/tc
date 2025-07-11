import subprocess
import os
import shutil
import time
import threading

def print_dots(stop_event):
    """Print dots as feedback during the push operation."""
    while not stop_event.is_set():
        print('.', end='', flush=True)
        time.sleep(0.5)

def run_git_command(command, cwd, capture=False, text=True, check=True):
    """
    Helper function to run Git commands and handle potential errors.
    """
    full_command = ' '.join(command)
    print(f"Running: {full_command}")
    try:
        if capture:
            result = subprocess.run(command, cwd=cwd, capture_output=capture, text=text, check=check)
            return result
        else:
            subprocess.run(command, cwd=cwd, check=check)
            return None
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip() if e.stderr else "No stderr message."
        print(f"Git command failed: {full_command}")
        if e.stdout:
            print(f"STDOUT:\n{e.stdout}")
        print(f"STDERR:\n{error_message}")
        raise e # Re-raise to be caught by the main try-except block

def main():
    print("Starting upload process...")

    # Step 1: Get the repository root
    repository_root = os.getcwd()

    # Check if the repository exists
    try:
        subprocess.check_output(
            ['git', 'rev-parse', '--is-inside-work-tree'], cwd=repository_root
        )
    except subprocess.CalledProcessError:
        print("Error: This script must be run from within a Git repository.")
        print("Upload failed.")
        exit(1)

    # Step 2: Define source and destination file paths for tc_database2.txt
    parent_dir = os.path.dirname(repository_root)
    source_file_name = 'tc_database2.txt'
    source_file_path = os.path.join(parent_dir, source_file_name)
    dest_file_path = os.path.join(repository_root, source_file_name)
    diff_output_file = os.path.join(repository_root, 'abc.txt') # Define where to save the diff

    # Check if the NEW source file exists
    if not os.path.exists(source_file_path):
        print(f"Error: File '{source_file_path}' not found in the parent directory.")
        print("Upload failed.")
        exit(1)

    # Step 3: Copy the NEW file to the repository root
    try:
        os.makedirs(repository_root, exist_ok=True) # Ensure repo dir exists
        shutil.copy2(source_file_path, dest_file_path)
        print(f"Copied '{source_file_path}' to '{dest_file_path}'")
    except Exception as e:
        print(f"Error copying file: {e}")
        print("Upload failed.")
        exit(1)

    # Step 3.5: Configure Git identity
    user_name = "whatalife1"
    user_email = "new.life.786.786.786@gmail.com"
    try:
        run_git_command(['git', 'config', 'user.name', user_name], cwd=repository_root)
        run_git_command(['git', 'config', 'user.email', user_email], cwd=repository_root)
        print(f"Set Git user.name to '{user_name}' and user.email to '{user_email}' for this repository.")
    except Exception:
        print("Upload failed.")
        exit(1)

    # Step 4: Get GitHub token from environment variable
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set.")
        print("Please set it with your GitHub Personal Access Token.")
        print("Upload failed.")
        exit(1)

    repo_name = "whatalife1/tc"  # Adjust this to your repository
    repo_url = f"https://{github_token}@github.com/{repo_name}.git"

    # Step 5: Set the Git remote URL with GitHub token
    try:
        run_git_command(['git', 'remote', 'set-url', 'origin', repo_url], cwd=repository_root)
        print("Successfully set Git remote URL with GitHub token.")
    except Exception:
        print("Upload failed.")
        exit(1)

    # Step 6: Get Git status before adding/committing
    try:
        status_result = run_git_command(['git', 'status'], cwd=repository_root, capture=True)
        print("\n--- Git Status Before Operations ---")
        print(status_result.stdout)
        print("----------------------------------\n")
    except Exception:
        print("Could not get initial Git status.")

    # Step 7: Add the NEW file to Git
    try:
        run_git_command(['git', 'add', '.'], cwd=repository_root)
        print("Attempted to stage all changes using 'git add .'")
    except Exception as e:
        print(f"Error during 'git add .': {e}")
        print("Upload failed.")
        exit(1)

    # Step 8: Get Git status after adding
    try:
        status_result = run_git_command(['git', 'status'], cwd=repository_root, capture=True)
        print("\n--- Git Status After Add ---")
        print(status_result.stdout)
        print("--------------------------\n")

        if source_file_name not in status_result.stdout or \
           ("new file:" not in status_result.stdout and "modified:" not in status_result.stdout):
            print(f"Warning: '{source_file_name}' does not appear to be staged after 'git add .'.")
            print("This might be because the file content is identical to what Git already tracks, or it's not being recognized as new/modified.")

    except Exception:
        print("Could not get Git status after add.")

    # Step 9: Commit the changes
    commit_message = f"Update {source_file_name} via script"
    try:
        commit_result = run_git_command(
            ['git', 'commit', '-m', commit_message],
            cwd=repository_root,
            capture=True,
            check=False # We will check returncode manually
        )

        if commit_result and commit_result.returncode == 0:
            print("Commit command executed successfully.")
            if "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
                print("No changes to commit.")
            else:
                print("Changes committed successfully.")
                if commit_result.stdout:
                    print(f"Commit STDOUT:\n{commit_result.stdout}")
                if commit_result.stderr:
                    print(f"Commit STDERR:\n{commit_result.stderr}")
        elif commit_result and ("nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr):
            print("No changes to commit.")
        else:
            print(f"Git commit failed with return code {commit_result.returncode}.")
            print(f"Git commit stderr:\n{commit_result.stderr.strip()}")
            print("Upload failed.")
            exit(1)

    except Exception as e:
        print(f"An unexpected error occurred during commit: {e}")
        print("Upload failed.")
        exit(1)

    # --- NEW STEP: Generate Diff ---
    print("\nGenerating diff for the latest commit...")
    try:
        # We want the diff between the HEAD commit (which is the one just made)
        # and the HEAD^ (the commit before it).
        # We also need to specify the file(s) for which we want the diff.
        # If you only want the diff for tc_database2.txt:
        diff_command = ['git', 'diff', 'HEAD^', '--', source_file_name]
        # If you want the diff of ALL changed files in the last commit, you'd need to get the commit SHA
        # and then diff against HEAD^, or use a broader diff if possible.
        # For simplicity, let's assume you want the diff for the specific file just added.

        diff_result = run_git_command(diff_command, cwd=repository_root, capture=True)

        if diff_result:
            with open(diff_output_file, 'w', encoding='utf-8') as f:
                f.write(diff_result.stdout)
            print(f"Differences saved to '{diff_output_file}'")
        else:
            print("Could not generate diff for the commit.")

    except Exception as e:
        print(f"An error occurred while generating the diff: {e}")
    # --- END NEW STEP ---


    # Step 10: Pull remote changes before pushing
    print("\nAttempting to pull remote changes before pushing...", flush=True)
    try:
        # Use 'main' as the default branch. Adjust if your repo uses 'master'.
        pull_result = run_git_command(['git', 'pull', 'origin', 'main'], cwd=repository_root, capture=True, check=False)

        if pull_result.returncode != 0:
            if "Already up to date." in pull_result.stdout:
                print("Already up to date with remote.")
            elif "fatal: The current branch main has no upstream branch" in pull_result.stderr:
                print("Warning: Current branch 'main' has no upstream. Pushing without pull.")
            else:
                print(f"Git pull failed. Please resolve conflicts manually if any. Error:\n{pull_result.stderr}")
                print("Upload failed.")
                exit(1)
        else:
            print("Pull successful. Remote changes integrated.")
            if pull_result.stdout:
                print(f"Pull STDOUT:\n{pull_result.stdout}")

    except Exception as e:
        print(f"An unexpected error occurred during pull: {e}")
        print("Upload failed.")
        exit(1)

    # Step 11: Push to GitHub with feedback
    print("\nPushing changes to GitHub...", flush=True)
    stop_event = threading.Event()
    dot_thread = threading.Thread(target=print_dots, args=(stop_event,))
    dot_thread.start()
    try:
        run_git_command(['git', 'push'], cwd=repository_root)

    except Exception:
        print("\nGit push failed.")
        print("Upload failed.")
        exit(1)
    finally:
        stop_event.set()
        dot_thread.join()
    print("\nUpload successful!")

if __name__ == "__main__":
    main()