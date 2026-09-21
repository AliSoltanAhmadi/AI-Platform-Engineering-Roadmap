# Contributing to AI Platform Engineering Roadmap

Thank you for your interest in contributing! This repository serves as a public learning roadmap for DevOps/Platform engineers transitioning into AI Platform Engineering (MLOps + LLMOps).

## How to Contribute

### Reporting Issues
- Found a broken link? Create an issue with the URL and expected behavior.
- Notice outdated content? Describe what's missing and why it matters.

### Suggesting Improvements
1. **Fork** this repository
2. **Create a branch**: `git checkout -b feature/improvement-name`
3. **Make changes**: Update markdown files in `RoadMap/` or add new content
4. **Test**: Verify links work and formatting is correct
5. **Commit**: Use clear commit messages (e.g., `"docs: update GPU scheduling section"`)
6. **Pull Request**: Submit with a short description of the change

### Adding New Content
- **Roadmap additions**: Add sections to `RoadMap/ai_platform_roadmap.md` following existing format
- **Feature implementations**: Create feature directories under `specs/FEATURE-NOMINALIZATION/`
- **Examples and tutorials**: Add to relevant phase folders with clear prerequisites

## Code Style (for scripts/tools)

### PowerShell Scripts
- Use `param()` for function arguments
- Include error handling with `try/catch`
- Add comments explaining non-obvious logic

### Python Files  
- Follow PEP 8 style guide
- Include type hints where appropriate
- Write unit tests for core functions

## Development Workflow

1. **Check existing issues**: See if someone else is working on it
2. **Branch early**: Don't work on main directly
3. **Small commits**: Each commit should do one thing well
4. **Validate locally**: Test before pushing
5. **Review guidelines**: Ensure changes match project style

## What We're Building

### Current Focus: CLI Learning Tool (Feature 001)
An interactive command-line tool that guides learners through the AI Platform Engineering roadmap using local LLM inference.

**Status**: MVP in development under `specs/001-cli-learning-tool/`

- `/learn start` - Begin onboarding and first lesson
- `/learn overview` - View progress and available paths

### Future Features (TBD)
- Interactive challenges with scoring
- Knowledge base queries powered by local LLM
- Progress tracking across sessions
- Portfolio project generation

## Questions?

Open an issue or discuss in the repository. We welcome all contributions!

---

**Maintainer**: [Ali SoltanAhmadi](https://github.com/AliSoltanAhmadi)
