import os
import requests
from github import Github

# -----------------------------
# GitHub PR info
# -----------------------------
repo_name = os.environ["GITHUB_REPOSITORY"]
pr_number = os.environ["GITHUB_REF"].split("/")[-1]  # e.g., refs/pull/23/merge
gh = Github(os.environ["GITHUB_TOKEN"])
repo = gh.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

# -----------------------------
# Get PR diff
# -----------------------------
diff_url = pr.patch_url
diff_resp = requests.get(diff_url, headers={"Authorization": f"token {os.environ['GITHUB_TOKEN']}"})
diff = diff_resp.text

if not diff.strip():
    pr.create_issue_comment("🤖 AI Reviewer: Could not fetch diff for review.")
    print("No diff found.")
    exit(0)

# -----------------------------
# Hugging Face model API call
# -----------------------------
HF_MODEL = "HuggingFaceH4/zephyr-7b-beta"  # Free hosted model
HF_TOKEN = os.environ["HF_TOKEN"]

prompt = f"Review this Git diff for potential bugs, style issues, and missing docstrings. Respond in concise bullet points.\n\nDiff:\n{diff}"

headers = {"Authorization": f"Bearer {HF_TOKEN}"}
json_data = {"inputs": prompt, "options": {"wait_for_model": True}}

try:
    response = requests.post(f"https://api-inference.huggingface.co/models/{HF_MODEL}", headers=headers, json=json_data, timeout=60)
    response.raise_for_status()
    output = response.json()
    review_text = output[0]["generated_text"] if isinstance(output, list) else str(output)
except Exception as e:
    review_text = f"🤖 AI Reviewer encountered an error: {e}"

# -----------------------------
# Post comment to the PR
# -----------------------------
pr.create_issue_comment(f"### 🤖 AI Code Review\n{review_text}")
print("AI review posted successfully.")
