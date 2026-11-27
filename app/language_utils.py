import os

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
}

REVIEW_FOCUS = {
    "python": "performance, security, and missing unit tests",
    "javascript": "async behavior, memory leaks, and code readability",
    "typescript": "type safety, async behavior, and code readability",
    "java": "object-oriented design, exception handling, and thread safety",
    "go": "goroutine safety, error handling, and memory efficiency",
}
DEFAULT_FOCUS = "general code quality, maintainability, and performance"


def detect_language(filename: str) -> str:
    """Detect the programming language from the file extension (case-insensitive)."""
    extension = os.path.splitext(filename)[1].lower()
    return LANGUAGE_BY_EXTENSION.get(extension, "unknown")


def generate_language_prompt(language: str, code: str) -> str:
    """Build a language-specific review prompt. The diff is fenced so it reads as data, not instructions."""
    focus = REVIEW_FOCUS.get(language, DEFAULT_FOCUS)
    fence = "```"
    while fence in code:  # a diff containing backticks must not be able to close the fence early
        fence += "`"
    return (
        f"Review this {language} diff. Focus on {focus}. "
        "Suggest concise, actionable improvements, and say so plainly if you find no issues.\n\n"
        f"{fence}diff\n{code}\n{fence}"
    )
