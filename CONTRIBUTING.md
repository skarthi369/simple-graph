# Contributing to SimpleGraph

We love your input! We want to make contributing to SimpleGraph as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

### Pull Request Process

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/simple-graph.git
cd simple-graph

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install pytest pytest-asyncio black flake8 mypy

# Run tests
pytest tests/ -v

# Run linting
black src/ tests/ examples/
flake8 src/ tests/ examples/
mypy src/
```

## Code Style

### Python Code Style

- We use [Black](https://black.readthedocs.io/) for code formatting
- Line length: 88 characters (Black's default)
- We use [flake8](https://flake8.pycqa.org/) for linting
- We use [mypy](http://mypy-lang.org/) for type checking

### Documentation Style

- All public functions and classes must have docstrings
- Use Google-style docstrings
- Include type hints for all function parameters and return values
- Update README.md for any user-facing changes

### Testing Standards

- Minimum 90% test coverage for new features
- Write both unit tests and integration tests
- Use descriptive test names that explain what is being tested
- Test both success and failure scenarios
- Include performance tests for critical paths

## Reporting Bugs

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/skarthi369/simple-graph/issues).

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Feature Requests

We welcome feature requests! Please:

1. Check if the feature already exists or is planned
2. Open an issue with the `enhancement` label
3. Describe the feature and its use case
4. Provide examples of how it would be used

## Code Review Process

The core team looks at Pull Requests on a regular basis. After feedback has been given we expect responses within two weeks. After two weeks we may close the pull request if it isn't showing any activity.

## Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Focus on constructive feedback
- Celebrate contributions from everyone

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue with the `question` label or reach out to the maintainers directly.