#!/bin/bash

# --- USAGE EXAMPLES ---
: <<'END_OF_EXAMPLES'

# Option: Commit with a message and push to the default branch ('main').
# This is the most basic usage of the script.
./_git_update.sh -m "Add documentation for the new API endpoint"
./_git_update.sh -m "20250904 Update!"

# ---

# Option: Commit and push to a specific branch.
# Useful for working on feature or hotfix branches.
./_git_update.sh -m "Implement new user profile page" -b feature/user-profile

# ---

# Option: Commit locally but do NOT push to the remote server.
# Ideal for saving work-in-progress that isn't ready to be shared.
./_git_update.sh -m "WIP: Still refactoring the settings module" --no-push

# ---

# Option: Have the script ask for confirmation before acting.
# A safety measure to prevent accidental commits or pushes.
./_git_update.sh -m "Final changes before v2.0 release" --ask

# ---

# Option: Combine multiple arguments.
# Example: Commit to a specific 'hotfix' branch, but ask for confirmation first.
./_git_update.sh -m "CRITICAL: Fix login security vulnerability" -b hotfix/login-exploit --ask

# ---

# Option: Combine arguments in a different order.
# The order of optional flags does not matter.
./_git_update.sh -m "Update styling on homepage" --ask -b main

END_OF_EXAMPLES
# The comment block ends here. The script continues normally.


# --- Configuration ---
DEFAULT_BRANCH="main"
DEFAULT_PUSH=true
ASK_MODE=false
SCRIPT_SUCCESS=false

# --- Function to print usage ---
usage() {
    echo
    echo "Usage: $0 -m \"Your commit message\" [-b <branch_name>] [--no-push] [--ask]"
    echo "  -m <message> : (Required) The commit message."
    echo "  -b <branch>  : (Optional) The branch to push to. Defaults to '$DEFAULT_BRANCH'."
    echo "  --no-push    : (Optional) If set, will commit but not push."
    echo "  --ask        : (Optional) If set, will ask for confirmation before acting."
    exit 1
}

# --- Cleanup function to be called by trap ---
# All cleanup logic is now in one place.
cleanup() {
    # Only run the extra status check if the script finished successfully.
    if [ "$SCRIPT_SUCCESS" = true ]; then
        echo
        echo "--- Checking for ignored files ---"
        git status --ignored
        echo "------------------------------"
    fi

    # This part ALWAYS runs to ensure the user is returned to their branch.
    # The check for ORIGINAL_BRANCH prevents an error if the script fails before it's set.
    if [ -n "$ORIGINAL_BRANCH" ]; then
        echo
        echo "--- Returning to original branch: $ORIGINAL_BRANCH ---"
        # Use --quiet on the switch back to make the exit cleaner.
        git switch --quiet "$ORIGINAL_BRANCH"
    fi
}

# --- Parse Command-Line Arguments ---
COMMIT_MSG=""
BRANCH=$DEFAULT_BRANCH
DO_PUSH=$DEFAULT_PUSH

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -m) COMMIT_MSG="$2"; shift ;;
        -b) BRANCH="$2"; shift ;;
        --no-push) DO_PUSH=false ;;
        --ask) ASK_MODE=true ;;
        *) usage ;;
    esac
    shift
done

# --- Validate required arguments ---
if [ -z "$COMMIT_MSG" ]; then
    echo "Error: Commit message is required."
    usage
fi

# --- GRACEFUL BRANCH SWITCHING ---
# 1. Save the current branch name
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "--- Currently on branch '$ORIGINAL_BRANCH' ---"

# 2. Set up a trap to switch back on exit, no matter what.
#    This ensures we always return the user to their original branch.
#    The trap now calls our smart cleanup function.
trap cleanup EXIT

# 3. Switch to target branch before doing anything else
echo
echo "--- Ensuring we are on branch '$BRANCH' ---"
# Use 'git switch' (modern) or 'git checkout'
if ! git switch "$BRANCH"; then
    echo "Error: Could not switch to branch '$BRANCH'."
    echo "Please resolve any conflicts or ensure the branch exists."
    # The trap will still run on exit, returning you to ORIGINAL_BRANCH
    exit 1
fi

# --- Main Logic ---
echo
echo "--- Checking Git status on branch '$BRANCH' ---"
git status

# # Check if there are any changes to be committed
# if git diff-index --quiet HEAD --; then
#     echo "Working directory is clean. Nothing to commit."
#     echo "--- Checking for untracked files ---"
#     git status --porcelain | grep "^??"
#     echo "----------------------------------"

#     SCRIPT_SUCCESS=true # Set flag to true on successful "clean" exit
#     exit 0 # The trap will still run on exit!
# fi

# Check if there are any changes to be committed
if [ -z "$(git status --porcelain)" ]; then
    echo "Working directory is clean. Nothing to commit."
    echo "--- Checking for untracked files ---"
    git status --porcelain | grep "^??"
    echo "----------------------------------"

    SCRIPT_SUCCESS=true # Set flag to true on successful "clean" exit
    exit 0 # The trap will still run on exit!
fi

echo
echo "Changes detected in the working directory."

# --- Confirmation Step (if --ask is used) ---
if [ "$ASK_MODE" = true ]; then
    read -p "Do you want to add, commit, and push these changes? (y/n) " -n 1 -r
    echo # move to a new line
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operation cancelled."
        exit 1
    fi
fi

# --- Git Operations ---
echo
echo "--- Clearing any previous staging (reset) ---"
git reset

echo
echo "--- Staging all changes ---"
git add -A

echo
echo "--- Committing changes ---"
git commit -m "$COMMIT_MSG"

if [ "$DO_PUSH" = true ]; then
    echo ""
    echo "--- Pushing to branch '$BRANCH' ---"
    git push origin "$BRANCH"
else
    echo ""
    echo "Skipping push as per '--no-push' flag."
fi

echo
echo "--- Git update complete! ---"

SCRIPT_SUCCESS=true # Set flag to true on successful "commit" exit

# The script ends here. The `trap` command will now execute automatically.
