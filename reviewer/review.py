import os, requests
from github import Github

repo_name = os.environ["GITHUB_REPOSITORY"]
pr_number = os.environ["GITHUB_REF"].split("/")[-1]
gh = Github(os.environ["GITHUB_TOKEN"])
repo = gh.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

diff = requests.get(pr.patch_url, headers={"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}).text

prompt = f"Review this Git diff for bugs and style issues:\n{diff}\nReply in concise bullet points."

# Call a free Hugging Face hosted model
hf_token = os.environ["HF_TOKEN"]
resp = requests.post(
    "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta",
    headers={"Authorization": f"Bearer {hf_token}"},
    json={"inputs": prompt},
    timeout=60,
)

review = resp.json()[0]["generated_text"]
pr.create_issue_comment(f"### 🤖 AI Code Review\n{review}")
