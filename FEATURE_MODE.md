# Feature Engineering Mode

## Overview

The RFSN Sandbox Controller now supports **Feature Engineering Mode** in addition to its original Repair Mode. This allows the agent to implement new features from scratch, rather than just fixing bugs in existing code.

## Modes Comparison

| Aspect | Repair Mode | Feature Mode |
|--------|-------------|--------------|
| **Goal** | Make tests pass | Implement new functionality |
| **Completion Signal** | Tests pass (exit code 0) | Feature summary with "complete" status |
| **Test Modification** | Never modify test files | Create and modify test files |
| **Workflow** | Fix → Verify → Done | Scaffold → Implement → Test → Document |
| **CLI Flag** | (default) | `--feature-mode` |

## Using Feature Mode

### Basic Command

```bash
python -m rfsn_controller.cli \
  --repo "https://github.com/OWNER/REPO" \
  --feature-mode \
  --feature-description "Add user authentication with JWT tokens" \
  --acceptance-criteria "Users can log in with email/password" \
  --acceptance-criteria "JWT tokens are validated on protected routes" \
  --acceptance-criteria "Tokens expire after 24 hours"
```

### CLI Arguments

| Argument | Description | Required in Feature Mode |
|----------|-------------|--------------------------|
| `--feature-mode` | Enable feature engineering mode | Yes |
| `--feature-description` | Detailed description of the feature to implement | Recommended |
| `--acceptance-criteria` | Acceptance criteria (can be specified multiple times) | Recommended |
| `--steps` | Maximum iterations (default: 12) | No |
| `--model` | LLM model to use (default: deepseek-chat) | No |

### Feature Workflow

The agent automatically breaks down feature implementation into phases:

1. **Scaffold Phase**
   - Analyzes existing project structure
   - Creates necessary directories and files
   - Sets up basic boilerplate

2. **Implementation Phase**
   - Writes core functionality
   - Follows project conventions
   - Handles edge cases and errors

3. **Testing Phase**
   - Creates comprehensive test files
   - Covers happy path and edge cases
   - Ensures tests pass

4. **Documentation Phase**
   - Updates README or relevant docs
   - Adds inline code comments
   - Creates usage examples

### Completion Signals

The agent can report four completion statuses:

- **`complete`**: All acceptance criteria met, feature fully implemented
- **`partial`**: Some progress made but feature incomplete
- **`blocked`**: Cannot proceed due to missing information or dependencies
- **`in_progress`**: Actively working, making progress

### Example: Adding Authentication

```bash
python -m rfsn_controller.cli \
  --repo "https://github.com/myorg/myapp" \
  --feature-mode \
  --feature-description "Implement JWT-based authentication system" \
  --acceptance-criteria "Users can register with email/password" \
  --acceptance-criteria "Users can log in and receive a JWT token" \
  --acceptance-criteria "Protected routes validate JWT tokens" \
  --acceptance-criteria "Tokens expire after 24 hours" \
  --acceptance-criteria "Tests cover authentication flow" \
  --steps 20 \
  --model "deepseek-chat"
```

### Example: Adding API Endpoint

```bash
python -m rfsn_controller.cli \
  --repo "https://github.com/myorg/api-server" \
  --feature-mode \
  --feature-description "Add RESTful endpoint for user profile management" \
  --acceptance-criteria "GET /api/users/:id returns user profile" \
  --acceptance-criteria "PUT /api/users/:id updates user profile" \
  --acceptance-criteria "DELETE /api/users/:id removes user profile" \
  --acceptance-criteria "Endpoints require authentication" \
  --acceptance-criteria "Input validation is implemented" \
  --acceptance-criteria "Tests achieve 90% coverage" \
  --steps 15
```

## Output Format

### Feature Summary

When the feature is complete, the agent outputs a detailed summary:

```json
{
  "ok": true,
  "sandbox": "/tmp/rfsn_sb_abc123",
  "repo_dir": "/tmp/rfsn_sb_abc123/repo",
  "steps_taken": 8,
  "phase": "feature_complete",
  "summary": "Implemented JWT-based authentication system with the following components:\n\n1. Created auth/ module with login/register endpoints\n2. Implemented JWT token generation and validation\n3. Added authentication middleware for protected routes\n4. Created comprehensive test suite with 95% coverage\n5. Updated README with authentication usage guide\n\nFiles changed:\n- src/auth/__init__.py (new)\n- src/auth/jwt_handler.py (new)\n- src/auth/routes.py (new)\n- src/middleware/auth_middleware.py (new)\n- tests/test_auth.py (new)\n- README.md (updated)\n\nAll acceptance criteria have been met.",
  "completion_status": "complete"
}
```

### Partial Completion

If the feature is partially complete:

```json
{
  "ok": true,
  "sandbox": "/tmp/rfsn_sb_abc123",
  "repo_dir": "/tmp/rfsn_sb_abc123/repo",
  "steps_taken": 12,
  "phase": "feature_complete",
  "summary": "Partially implemented authentication system. Completed scaffolding and core login/register functionality, but tests and documentation are incomplete.\n\nCompleted:\n- Created auth module structure\n- Implemented JWT token generation\n- Added login/register endpoints\n\nRemaining:\n- Token validation middleware\n- Comprehensive test suite\n- Documentation updates\n\nBlocked by: Need clarification on password hashing algorithm preference.",
  "completion_status": "partial"
}
```

## Differences from Repair Mode

### Test File Modification

**Repair Mode:**
- NEVER modifies test files
- Only fixes implementation files
- Tests define the correctness criteria

**Feature Mode:**
- CREATES new test files
- MODIFIES existing test files when needed
- Tests are part of the deliverable

### Success Criteria

**Repair Mode:**
- Success = Tests pass (exit code 0)
- Failure = Tests still fail after max steps

**Feature Mode:**
- Success = Agent reports `completion_status: "complete"`
- Partial = Agent reports `completion_status: "partial"`
- Blocked = Agent reports `completion_status: "blocked"`

### Code Changes

**Repair Mode:**
- Minimal edits only
- No refactoring
- No reformatting

**Feature Mode:**
- Necessary changes to implement feature
- Can refactor to integrate properly
- Follows project style conventions

## Integration with Existing Projects

Feature mode respects existing project conventions:

1. **Detects project type** (Python, Node.js, Go, Rust, Java, .NET)
2. **Follows existing patterns** by analyzing similar code
3. **Matches code style** from existing files
4. **Integrates with build system** (uses existing test commands)
5. **Respects dependencies** (uses existing package managers)

## Limitations

1. **No external dependencies**: Agent cannot access external APIs or services during implementation
2. **No manual review**: Agent makes final decisions about implementation details
3. **Limited context**: Only has access to files explicitly read via tools
4. **No database access**: Cannot modify or query databases directly
5. **No network access**: Cannot fetch external resources

## Best Practices

### Writing Clear Feature Descriptions

✅ **Good:**
```
Add RESTful API endpoint for user profile management. 
Include GET, PUT, DELETE operations with authentication.
Use JSON for request/response format.
```

❌ **Bad:**
```
Fix the user stuff
```

### Writing Effective Acceptance Criteria

✅ **Good:**
- Each criterion is specific and testable
- Covers functional and non-functional requirements
- Includes edge cases and error handling

❌ **Bad:**
- Vague requirements like "make it work"
- No verification method
- Missing error cases

### Example Good vs Bad

**Good Feature Request:**
```bash
--feature-description "Implement rate limiting middleware for API endpoints"
--acceptance-criteria "Limit requests to 100 per minute per IP"
--acceptance-criteria "Return 429 status code when limit exceeded"
--acceptance-criteria "Include X-RateLimit-* headers in responses"
--acceptance-criteria "Rate limits are configurable via environment variables"
--acceptance-criteria "Tests verify rate limiting behavior"
```

**Bad Feature Request:**
```bash
--feature-description "Add rate limiting"
--acceptance-criteria "Should limit requests"
```

## Troubleshooting

### Feature Shows "blocked"

**Possible Causes:**
- Missing information in feature description
- Unclear acceptance criteria
- Conflicting requirements
- Technical limitation

**Solution:**
Provide more context in the feature description and clearer acceptance criteria.

### Feature Shows "partial" After Max Steps

**Possible Causes:**
- Feature too complex for step limit
- Unclear requirements
- Technical blockers

**Solutions:**
- Increase `--steps` limit
- Break feature into smaller features
- Clarify acceptance criteria

### Feature Modifies Wrong Files

**Possible Causes:**
- Unclear feature scope
- Misunderstood project structure

**Solutions:**
- Be more specific about which modules to modify
- Provide more context in feature description
- Check controller logs for reasoning

## Advanced Usage

### Custom Subgoals

While the agent automatically creates subgoals, you can influence the process by being specific in your feature description:

```bash
--feature-description "
1. Create new 'auth' module in src/auth/
2. Implement JWT token generation and validation
3. Add authentication middleware
4. Create tests in tests/auth/
5. Update API documentation
"
```

### Combining with Repair Mode

You can run feature mode first to implement a feature, then switch to repair mode to fix any bugs:

```bash
# Step 1: Implement feature
python -m rfsn_controller.cli \
  --repo "..." \
  --feature-mode \
  --feature-description "..." \
  --acceptance-criteria "..."

# Step 2: Fix any bugs (if needed)
python -m rfsn_controller.cli \
  --repo "..." \
  --test "pytest -q"
```

## See Also

- [README.md](README.md) - Main documentation
- [PROMPT_UPGRADE.md](PROMPT_UPGRADE.md) - Model prompting details
- [SETUP_CAPABILITIES.md](SETUP_CAPABILITIES.md) - Setup and dependencies
