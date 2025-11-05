def detect_language(filename: str) -> str:
    """
    Detects programming language based on file extension.
    """
    if filename.endswith(".py"):
        return "python"
    elif filename.endswith((".js", ".jsx")):
        return "javascript"
    elif filename.endswith(".java"):
        return "java"
    elif filename.endswith(".ts"):
        return "typescript"
    elif filename.endswith(".go"):
        return "go"
    else:
        return "unknown"


def generate_language_prompt(language: str, code: str) -> str:
    """
    Creates a language-specific prompt for code review.
    """
    if language == "python":
        focus = "performance, security, and missing unit tests"
    elif language == "javascript":
        focus = "async behavior, memory leaks, and code readability"
    elif language == "java":
        focus = "object-oriented design, exception handling, and thread safety"
    elif language == "go":
        focus = "goroutine safety, error handling, and memory efficiency"
    else:
        focus = "general code quality, maintainability, and performance"

    return f"""
        You are an expert {language} developer reviewing the following code.
        Focus on {focus}. Suggest concise and actionable improvements.

        Code:
        {code}
        """
