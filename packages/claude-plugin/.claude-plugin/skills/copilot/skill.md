---
name: copilot
description: GitHub Copilot CLI - AI pair programmer for code generation, testing, and debugging in your terminal
when_to_use:
  - Code generation and writing functions
  - Creating unit tests and integration tests
  - Debugging code and analyzing errors
  - Understanding what code does
  - AI-powered code suggestions and explanations
skill_type: executable
---

# GitHub Copilot CLI

AI pair programmer that generates code, tests, and helps debug right from your terminal.

## What is GitHub Copilot?

GitHub Copilot is an AI-powered code assistant that:
- **Generates code** - Write functions, classes, and complete workflows
- **Tests code** - Create unit tests and integration tests
- **Debugs issues** - Analyze errors and suggest fixes
- **Explains code** - Understand what code does

Works in your terminal with the `copilot` command via the `gh copilot` extension.

## How It Differs from GitHub CLI (`gh`)

| Tool | Purpose | Type |
|------|---------|------|
| **GitHub Copilot CLI** (`copilot`) | AI code generation & debugging | AI Assistant |
| **GitHub CLI** (`gh`) | GitHub operations (PRs, issues, auth) | Utility Tool |

**Key Point:** They complement each other. Copilot can suggest what code to write; gh executes GitHub operations.

## Installation

```bash
# Install GitHub CLI first (if not already installed)
# macOS
brew install gh

# Ubuntu/Debian
sudo apt update && sudo apt install gh

# Windows
choco install gh

# Install GitHub Copilot CLI extension
gh extension install github/gh-copilot

# Authenticate with GitHub
gh auth login

# Verify installation
gh copilot --version
copilot --version
```

## How to Invoke

**Use Skill() to invoke Copilot CLI:**

```python
# Ask Copilot to generate code
Skill(skill=".claude-plugin:copilot", args="Write a function that validates email addresses")

# Get code explanation
Skill(skill=".claude-plugin:copilot", args="Explain what this code does: [code snippet]")

# Generate tests
Skill(skill=".claude-plugin:copilot", args="Write unit tests for my function")

# Debug code
Skill(skill=".claude-plugin:copilot", args="Debug this error: Cannot read property 'map' of undefined")
```

**What happens internally:**
1. Check if `copilot` CLI is installed on your system
2. If **YES** → Execute copilot commands: `copilot "Your question"`
3. If **NO** → Return error message with installation instructions

**FALLBACK: Direct Bash execution (when Skill unavailable):**

```bash
# Manual fallback - direct copilot CLI usage
if ! command -v copilot &> /dev/null; then
    echo "ERROR: Copilot CLI not installed"
    echo "Install from: https://github.com/github/gh-copilot"
    exit 1
fi

# Use copilot directly from terminal
copilot "Write a Python function that sorts a list"
copilot "Explain how this JavaScript function works"
copilot "Help me debug this error"
```

## Example Use Cases

### 1. Code Generation

```bash
# Generate a function
copilot "Write a Python function that fetches data from an API with retry logic"

# Generate a class
copilot "Create a JavaScript class for managing user authentication"

# Generate boilerplate
copilot "Create a basic Express.js REST API endpoint"
```

### 2. Writing Tests

```bash
# Generate unit tests
copilot "Write unit tests for my email validation function using pytest"

# Generate integration tests
copilot "Create integration tests for a database connection"

# Generate mock data
copilot "Generate sample test data for user objects"
```

### 3. Debugging Code

```bash
# Analyze an error
copilot "Debug this error: TypeError: Cannot read property 'name' of undefined"

# Fix performance issues
copilot "Why is this code running slowly? [code snippet]"

# Security review
copilot "Are there any security issues in this authentication code?"
```

### 4. Code Explanation

```bash
# Understand existing code
copilot "Explain what this function does: [code snippet]"

# Learn patterns
copilot "How does this async/await pattern work?"

# API documentation
copilot "Explain the parameters and return value of this function"
```

### 5. Code Review

```bash
# Review code for best practices
copilot "Review this code for Python best practices"

# Check error handling
copilot "Are there any edge cases I'm missing in this code?"

# Performance suggestions
copilot "How can I optimize this function for better performance?"
```

## Use Cases

- **Code Generation** - Generate boilerplate code, functions, classes
- **Testing** - Create test cases and mocking code
- **Debugging** - Understand errors and get fix suggestions
- **Learning** - Understand how code works and best practices
- **Documentation** - Generate code comments and docstrings
- **Code Review** - Analyze code for improvements

## Requirements

- GitHub account and authentication
- `gh` CLI installed (GitHub CLI)
- `gh copilot` extension installed
- Copilot subscription (requires GitHub Copilot subscription)

## Integration with HtmlGraph

Track code generation work in features:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Document code generated with Copilot
feature = sdk.features.create(
    title="Authentication Module Implementation",
    description="""
    Generated with GitHub Copilot:
    - Generated user authentication class
    - Created unit tests using pytest
    - Debugged session handling logic

    Copilot prompts used:
    - "Create a Python class for user authentication"
    - "Write unit tests for authentication module"
    - "Debug: TypeError in session validation"
    """
).save()
```

## When to Use

✅ **Use Copilot for:**
- Generating new code
- Writing tests
- Understanding errors
- Learning code patterns
- Code suggestions and explanations
- Debugging complex issues

❌ **Don't use Copilot for:**
- GitHub operations (use `gh` CLI directly or use Bash)
- Exploring existing code (use `/gemini` skill instead)
- Simple scripting (use plain bash/python)
- Replacing human understanding (use for learning, not blind acceptance)

## Tips for Best Results

1. **Be specific** - Provide context and exact requirements
2. **Include code snippets** - When debugging or asking for explanations
3. **Iterate** - Ask follow-up questions for clarification
4. **Verify output** - Don't blindly accept generated code
5. **Test thoroughly** - Always test generated code before using in production
6. **Learn from it** - Understand what Copilot suggests and why

## Common Patterns

### Pattern 1: Generate Then Test

```bash
# 1. Generate a function
copilot "Write a function to calculate factorial"

# 2. Generate tests for it
copilot "Write unit tests for the factorial function"

# 3. Test the code
python -m pytest test_factorial.py
```

### Pattern 2: Debug Then Improve

```bash
# 1. Debug an error
copilot "Debug this error: RecursionError: maximum recursion depth exceeded"

# 2. Request optimization
copilot "How can I optimize this recursive function?"

# 3. Test the improved version
python improved_function.py
```

### Pattern 3: Understand Then Extend

```bash
# 1. Understand existing code
copilot "Explain what this function does: [code]"

# 2. Request extension
copilot "How would I add error handling to this function?"

# 3. Generate the extended version
copilot "Add error handling to this function"
```

## Limitations

- Requires active GitHub Copilot subscription
- Best results with clear, specific prompts
- Not a replacement for human review
- Generated code should be tested before production use
- Performance depends on internet connection

## Related Skills

- `/gemini` - For exploring repository structure and large codebases
- `/codex` - For alternative AI code generation (OpenAI GPT-4)
- `gh` CLI - For GitHub operations (PRs, issues, repos) - use Bash directly
- `/code-quality` - For validating code quality after generation

## When NOT to Use

Avoid GitHub Copilot for:
- GitHub operations (use `gh` CLI or Bash instead)
- Exploratory research (use `/gemini` skill)
- Simple git operations (use git directly)
- Non-development tasks (use appropriate tool)

## Error Handling

### Copilot CLI Not Installed

```bash
Error: "copilot: command not found"

Solution:
1. Install gh CLI: https://cli.github.com/
2. Install copilot extension: gh extension install github/gh-copilot
3. Authenticate: gh auth login
```

### Authentication Required

```bash
Error: "authentication required"

Solution:
gh auth login
# Follow prompts to authenticate with GitHub
```

### Subscription Required

```bash
Error: "Copilot subscription required"

Solution:
1. Ensure you have active GitHub Copilot subscription
2. Visit: https://github.com/features/copilot/signup
3. Subscribe to GitHub Copilot
```

## Advanced Usage

### Custom Prompts

Create effective prompts:

```bash
# Specific task
copilot "Write a TypeScript function that validates credit card numbers using Luhn algorithm"

# With context
copilot "I'm using Express.js. Write a middleware for authentication"

# Multiple requirements
copilot "Create a Python async function that fetches multiple URLs in parallel and returns JSON results with error handling"
```

### Integration with Other Tools

```bash
# Generate code, then commit with git
copilot "Write a README.md for my project" > README.md
git add README.md
git commit -m "docs: add project README"

# Generate tests, then run with pytest
copilot "Write tests for my module" > test_module.py
uv run pytest test_module.py
```

## Key Differences from Other Tools

| Feature | Copilot | Codex | Gemini |
|---------|---------|-------|--------|
| AI Code Generation | ✅ | ✅ | ⚠️ Limited |
| Code Debugging | ✅ | ✅ | ⚠️ Limited |
| Repository Analysis | ⚠️ Limited | ⚠️ Limited | ✅ |
| Subscription Required | ✅ Yes | ✅ Yes | ✅ Yes |
| Terminal Access | ✅ Yes | ✅ Yes | ⚠️ Limited |
| Test Generation | ✅ | ✅ | ⚠️ Limited |
