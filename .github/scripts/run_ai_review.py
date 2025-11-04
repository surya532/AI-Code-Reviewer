import os
import openai
import httpx
import subprocess

openai.api_key = os.getenv("OPENAI_API_KEY")
repo = os.getenv("GITHUB_REPOSITORY")
pr_number = os.getenv("GITHUB_REF").split("/")[-1]

changed_files = subprocess.check_output(
    ["git", "diff", "--name-only", "origin/main...HEAD"]
).decode().splitlines()

code_snippets = []
for file in changed_files:
    if file.endswith(".py"):
        with open(file, "r") as f:
            code_snippets.append(f"# File: {file}\n{f.read()}")

if not code_snippets:
    print("No Python files changed")
    exit(0)

prompt = f"""
You are an expert software engineer reviewing Python code.
Review the following code for:
1. Performance improvements
2. Security risks
3. Missing tests
Provide concise comments for each file.

Code:
{"\n\n".join(code_snippets)}
"""

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)

review_comments = response['choices'][0]['message']['content']

url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
token = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"}
httpx.post(url, headers=headers, json={"body": review_comments})

print("Review posted successfully!")
