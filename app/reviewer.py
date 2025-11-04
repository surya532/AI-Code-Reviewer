import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def review_code_with_llm(code_snippets: list[str]) -> str:
    code_text = "\n\n".join(code_snippets)
    prompt = f"""
You are an expert software engineer reviewing Python code.
Review the following code for:
1. Performance improvements
2. Security risks
3. Missing tests
Provide concise comments for each file.

Code:
{code_text}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']
