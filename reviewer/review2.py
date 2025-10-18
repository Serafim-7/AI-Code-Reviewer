# ...existing code...
import os
import sys
import logging
import requests
from github import Github

logging.basicConfig(level=logging.INFO)

def get_env(name, required=True):
    val = os.environ.get(name)
    if required and not val:
        logging.error("Missing required environment variable: %s", name)
        sys.exit(1)
    return val

# -----------------------------
# GitHub PR info
# -----------------------------
repo_name = get_env("GITHUB_REPOSITORY")
gh_token = get_env("GITHUB_TOKEN")
gh = Github(gh_token)

# GITHUB_REF may not be in the pull/xx/merge form in all workflows; guard parsing.
ref = get_env("GITHUB_REF")
try:
    pr_number = int(ref.split("/")[-1])
except Exception:
    logging.error("Could not parse PR number from GITHUB_REF=%s", ref)
    sys.exit(1)

repo = gh.get_repo(repo_name)
pr = repo.get_pull(pr_number)

# -----------------------------
# Get PR diff (safe fetch)
# -----------------------------
diff_url = pr.patch_url
headers = {"Authorization": f"token {gh_token}"}
try:
    diff_resp = requests.get(diff_url, headers=headers, timeout=15)
    diff_resp.raise_for_status()
    diff = diff_resp.text or ""
except Exception as e:
    logging.exception("Failed to fetch PR diff: %s", e)
    try:
        pr.create_issue_comment("🤖 AI Reviewer: Could not fetch diff for review.")
    except Exception:
        pass
    sys.exit(0)

if not diff.strip():
    try:
        pr.create_issue_comment("🤖 AI Reviewer: Could not fetch diff for review.")
    except Exception:
        pass
    logging.info("No diff found.")
    sys.exit(0)

# Truncate diff to avoid exceeding model/context limits and comment size limits
MAX_DIFF_CHARS = 45_000
truncated_notice = ""
if len(diff) > MAX_DIFF_CHARS:
    truncated_notice = f"\n\n[Truncated diff to first {MAX_DIFF_CHARS} characters for model input]\n"
    diff_for_model = diff[:MAX_DIFF_CHARS]
else:
    diff_for_model = diff

# -----------------------------
# Hugging Face model API call
# -----------------------------
HF_MODEL = os.environ.get("HF_MODEL", "HuggingFaceH4/zephyr-7b-beta")
HF_TOKEN = get_env("HF_TOKEN")

prompt = (
    "Review this Git diff for potential bugs, style issues, and missing docstrings. "
    "Respond in concise bullet points.\n\nDiff:\n" + diff_for_model
)

hf_headers = {"Authorization": f"Bearer {HF_TOKEN}"}
json_data = {"inputs": prompt, "options": {"wait_for_model": True}}

review_text = ""
try:
    response = requests.post(
        f"https://api-inference.huggingface.co/models/{HF_MODEL}",
        headers=hf_headers,
        json=json_data,
        timeout=60,
    )
    response.raise_for_status()
    output = response.json()

    # Handle different possible HF response shapes
    if isinstance(output, list) and output:
        first = output[0]
        review_text = first.get("generated_text") or first.get("summary_text") or str(first)
    elif isinstance(output, dict):
        review_text = output.get("generated_text") or output.get("summary_text") or str(output)
    else:
        review_text = str(output)

except Exception as e:
    logging.exception("HF model call failed: %s", e)
    review_text = f"🤖 AI Reviewer encountered an error calling the model: {e}"

# Prepend note if we truncated the diff
if truncated_notice:
    review_text = truncated_notice + "\n" + review_text

comment_body = f"### 🤖 AI Code Review\n\n{review_text}"

# -----------------------------
# Post or update comment to the PR
# -----------------------------
try:
    bot_login = gh.get_user().login
    existing = None
    for c in pr.get_issue_comments():
        if c.user and c.user.login == bot_login and c.body.startswith("### 🤖 AI Code Review"):
            existing = c
            break

    if existing:
        existing.edit(comment_body)
        logging.info("Updated existing AI review comment.")
    else:
        pr.create_issue_comment(comment_body)
        logging.info("Created new AI review comment.")
except Exception as e:
    logging.exception("Failed to post comment to PR: %s", e)
    # If posting fails, still exit gracefully
    sys.exit(0)

print("AI review posted successfully.")
# ...existing code...