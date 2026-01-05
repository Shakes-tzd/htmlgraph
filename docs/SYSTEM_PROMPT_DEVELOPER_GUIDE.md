# Developer Guide: Extending System Prompt Persistence

Guide for developers extending and customizing the system prompt persistence system, adding custom layers, integrating with hooks, and building on top of the SDK.

## Table of Contents
- [Overview](#overview)
- [Adding Custom Layers](#adding-custom-layers)
- [Hooking Into SessionStart](#hooking-into-sessionstart)
- [Creating Custom Skills](#creating-custom-skills)
- [SDK Integration](#sdk-integration)
- [Testing Custom Implementations](#testing-custom-implementations)
- [Performance Optimization](#performance-optimization)
- [Debugging Tips](#debugging-tips)
- [Contributing](#contributing)

---

## Overview

### Extension Points

The system prompt persistence architecture provides several extension points:

```
SessionStart Hook (entry point)
    ├─ Custom layer implementation
    ├─ Environment variable setup
    └─ Skill activation

SDK SessionStateManager
    ├─ State detection
    ├─ Backup restoration
    └─ Validation logic

Orchestrator Skill
    ├─ Decision framework
    ├─ Spawner routing
    └─ Cost tracking

Custom implementations can:
✓ Add new persistence layers
✓ Customize prompt processing
✓ Integrate with external systems
✓ Enhance cost tracking
✓ Implement team-specific patterns
```

### Design Philosophy

**Key principles for extensions:**

1. **Idempotency**: Safe to run multiple times without side effects
2. **Graceful Degradation**: Failures don't break the system
3. **Observability**: Log everything for debugging
4. **Backward Compatibility**: Don't break existing functionality
5. **Test Coverage**: Write tests for all extensions

---

## Adding Custom Layers

### Layer Pattern

All persistence layers follow this pattern:

```python
class CustomPersistenceLayer:
    """
    Custom persistence layer for system prompts.

    Implementation pattern:
    1. Attempt to retrieve system prompt
    2. Return if successful, raise exception if not
    3. Fallback layers handle exceptions gracefully
    """

    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def retrieve(self) -> str:
        """
        Retrieve system prompt.

        Returns:
            System prompt text

        Raises:
            PersistenceLayerError: If retrieval fails
        """
        raise NotImplementedError

    def store(self, prompt: str) -> bool:
        """
        Store system prompt for later retrieval.

        Args:
            prompt: System prompt text

        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """Check if this layer can operate."""
        raise NotImplementedError
```

### Example 1: Remote Storage Layer (Layer 4)

Store system prompts in remote storage (S3, Git, etc.):

```python
from .base import CustomPersistenceLayer
import boto3
import json

class RemoteS3Layer(CustomPersistenceLayer):
    """Persist system prompt to AWS S3."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.bucket = config.get('s3_bucket')
        self.key = config.get('s3_key', '.system-prompt.json')
        self.region = config.get('region', 'us-east-1')
        self.s3_client = boto3.client('s3', region_name=self.region)

    def is_available(self) -> bool:
        """Check if S3 credentials configured."""
        return bool(self.bucket and self.s3_client)

    def retrieve(self) -> str:
        """Fetch from S3."""
        if not self.is_available():
            raise PersistenceLayerError("S3 not configured")

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=self.key
            )
            data = json.loads(response['Body'].read().decode())
            self.logger.info(f"Retrieved system prompt from S3: {self.key}")
            return data.get('system_prompt', '')
        except Exception as e:
            raise PersistenceLayerError(f"S3 retrieval failed: {e}")

    def store(self, prompt: str) -> bool:
        """Store to S3."""
        if not self.is_available():
            self.logger.warning("S3 not configured, skipping storage")
            return False

        try:
            data = {
                'system_prompt': prompt,
                'timestamp': datetime.now().isoformat(),
                'version': '1.0'
            }
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=self.key,
                Body=json.dumps(data),
                ContentType='application/json'
            )
            self.logger.info(f"Stored system prompt to S3: {self.key}")
            return True
        except Exception as e:
            self.logger.error(f"S3 storage failed: {e}")
            return False
```

**Using the layer:**

```python
# In session-start.py hook

from custom_layers.s3_layer import RemoteS3Layer

def retrieve_system_prompt():
    """Retrieve with multi-layer fallback including S3."""

    layers = [
        FileSystemLayer(),           # Layer 1: Primary
        EnvironmentVariableLayer(),  # Layer 2: Backup
        RemoteS3Layer({              # Layer 4: Remote backup
            's3_bucket': 'my-company-prompts',
            's3_key': f'{project_id}/system-prompt.json'
        }),
        FileBackupLayer(),           # Layer 3: Recovery
    ]

    for layer in layers:
        try:
            if layer.is_available():
                prompt = layer.retrieve()
                logger.info(f"Successfully retrieved from {layer.__class__.__name__}")
                return prompt
        except PersistenceLayerError as e:
            logger.debug(f"Layer {layer.__class__.__name__} failed: {e}")
            continue

    # Ultimate fallback
    return PLUGIN_DEFAULT_SYSTEM_PROMPT
```

### Example 2: Database Layer (Layer 4)

Store system prompts in PostgreSQL with versioning:

```python
from .base import CustomPersistenceLayer
import psycopg2
from datetime import datetime

class PostgresLayer(CustomPersistenceLayer):
    """Persist system prompt to PostgreSQL database."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.connection_string = config.get('db_url')
        self.table = config.get('table', 'system_prompts')
        self.project_id = config.get('project_id')

    def is_available(self) -> bool:
        """Check if database connection available."""
        try:
            conn = psycopg2.connect(self.connection_string)
            conn.close()
            return True
        except:
            return False

    def retrieve(self) -> str:
        """Fetch latest version from database."""
        if not self.is_available():
            raise PersistenceLayerError("Database not available")

        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()

            cur.execute(f"""
                SELECT content FROM {self.table}
                WHERE project_id = %s
                ORDER BY version DESC
                LIMIT 1
            """, (self.project_id,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if result:
                self.logger.info(f"Retrieved system prompt from database")
                return result[0]
            else:
                raise PersistenceLayerError("No prompt in database")

        except Exception as e:
            raise PersistenceLayerError(f"Database retrieval failed: {e}")

    def store(self, prompt: str) -> bool:
        """Store new version to database."""
        if not self.is_available():
            self.logger.warning("Database not available, skipping storage")
            return False

        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()

            cur.execute(f"""
                INSERT INTO {self.table}
                (project_id, content, version, created_at)
                VALUES (%s, %s, (
                    SELECT COALESCE(MAX(version), 0) + 1
                    FROM {self.table}
                    WHERE project_id = %s
                ), %s)
            """, (self.project_id, prompt, self.project_id, datetime.now()))

            conn.commit()
            cur.close()
            conn.close()

            self.logger.info("Stored system prompt to database")
            return True

        except Exception as e:
            self.logger.error(f"Database storage failed: {e}")
            return False
```

**Database schema:**

```sql
CREATE TABLE system_prompts (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    version INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    UNIQUE(project_id, version)
);

CREATE INDEX idx_system_prompts_project_version
ON system_prompts(project_id, version DESC);
```

---

## Hooking Into SessionStart

### Hook Extension Pattern

Extend session-start.py with custom logic:

```python
# File: .claude/hooks/scripts/session-start.py
# Append to end of existing hook

def on_custom_event(event_type: str, data: dict):
    """Hook for custom session start logic."""
    if event_type == 'system_prompt_injected':
        handle_prompt_injected(data)
    elif event_type == 'post_compact':
        handle_post_compact(data)

def handle_prompt_injected(data: dict):
    """Called after system prompt successfully injected."""
    print(f"System prompt injected: {data['size']} bytes")

    # Custom logic here
    # Examples:
    # - Log to monitoring system
    # - Update tracking dashboard
    # - Trigger notifications
    # - Run validation checks

def handle_post_compact(data: dict):
    """Called when post-compact detected."""
    print(f"Post-compact session: {data['session_id']}")

    # Custom logic here
    # Examples:
    # - Notify user of persistence status
    # - Reset counters
    # - Update metrics
```

### Adding Hook Validation

Validate system prompt before injection:

```python
class SystemPromptValidator:
    """Validate system prompt before injection."""

    @staticmethod
    def validate_all(prompt: str) -> dict:
        """Run all validations."""
        return {
            'syntax': SystemPromptValidator.validate_syntax(prompt),
            'tokens': SystemPromptValidator.validate_tokens(prompt),
            'content': SystemPromptValidator.validate_content(prompt),
            'security': SystemPromptValidator.validate_security(prompt),
        }

    @staticmethod
    def validate_syntax(prompt: str) -> bool:
        """Check markdown syntax."""
        try:
            import markdown
            markdown.markdown(prompt)
            return True
        except:
            return False

    @staticmethod
    def validate_tokens(prompt: str, max_tokens: int = 1000) -> bool:
        """Check token budget."""
        tokens = len(prompt) // 4  # Rough estimate
        return tokens <= max_tokens

    @staticmethod
    def validate_content(prompt: str) -> bool:
        """Check for required sections."""
        required = [
            'Model',  # Model selection
            'Delegat',  # Delegation pattern
        ]
        return all(section in prompt for section in required)

    @staticmethod
    def validate_security(prompt: str) -> bool:
        """Check for sensitive data."""
        forbidden = [
            'password', 'token', 'secret', 'key',
            'api_key', 'api_secret', 'credentials'
        ]
        prompt_lower = prompt.lower()
        return not any(word in prompt_lower for word in forbidden)
```

**Using validation in hook:**

```python
def inject_system_prompt():
    """Inject with validation."""
    system_prompt = read_file('.claude/system-prompt.md')

    # Validate before injection
    validation = SystemPromptValidator.validate_all(system_prompt)
    if not validation['security']:
        logger.error("SECURITY: System prompt contains sensitive data!")
        # Fallback to default
        system_prompt = PLUGIN_DEFAULT_SYSTEM_PROMPT

    if not validation['tokens']:
        logger.warning("System prompt exceeds token budget, truncating")
        system_prompt = truncate_smart(system_prompt)

    # Proceed with injection
    os.environ['CLAUDE_SYSTEM_PROMPT'] = system_prompt
```

---

## Creating Custom Skills

### Skill Extension Pattern

Create custom skills that interact with system prompt:

```python
# File: packages/claude-plugin/skills/my-custom-skill/SKILL.md

---
id: my-custom-skill
name: My Custom Skill
description: Custom skill that uses system prompt guidance
trigger: "when user asks about [topic]"
visibility: "always"
tags: ["custom", "extension"]
---

# My Custom Skill

This skill extends system prompt persistence with custom functionality.

## How It Works

1. Reads current system prompt from environment
2. Analyzes delegation patterns in prompt
3. Provides custom guidance based on patterns

## Usage

```bash
/my-custom-skill
```

## Examples

[Examples here]
```

**Python implementation:**

```python
# File: packages/claude-plugin/skills/my-custom-skill/skill.py

import os
from typing import Optional

class MyCustomSkill:
    """Custom skill using system prompt guidance."""

    def __init__(self):
        self.system_prompt = os.getenv('CLAUDE_SYSTEM_PROMPT', '')
        self.delegation_enabled = os.getenv('CLAUDE_DELEGATION_ENABLED') == 'true'

    def analyze_prompt(self) -> dict:
        """Analyze system prompt for patterns."""
        if not self.system_prompt:
            return {'status': 'no_prompt'}

        patterns = {
            'model_guidance': self._extract_model_guidance(),
            'delegation_rules': self._extract_delegation_rules(),
            'quality_gates': self._extract_quality_gates(),
            'key_rules': self._extract_key_rules(),
        }

        return patterns

    def _extract_model_guidance(self) -> list:
        """Extract model selection guidance."""
        lines = self.system_prompt.split('\n')
        models = []
        current_model = None

        for line in lines:
            if 'Use Haiku' in line or 'Use Sonnet' in line or 'Use Opus' in line:
                current_model = line.strip()
                models.append(current_model)

        return models

    def _extract_delegation_rules(self) -> list:
        """Extract delegation patterns."""
        if 'Delegation' not in self.system_prompt:
            return []

        lines = self.system_prompt.split('\n')
        rules = []
        in_delegation = False

        for line in lines:
            if 'Delegation' in line:
                in_delegation = True
            elif in_delegation:
                if line.startswith('##'):
                    break
                if line.strip() and not line.startswith('#'):
                    rules.append(line.strip())

        return rules

    def _extract_quality_gates(self) -> list:
        """Extract quality gate commands."""
        if 'Quality' not in self.system_prompt:
            return []

        lines = self.system_prompt.split('\n')
        gates = []

        for line in lines:
            if 'uv run' in line or 'pytest' in line or 'mypy' in line:
                gates.append(line.strip())

        return gates

    def _extract_key_rules(self) -> list:
        """Extract numbered rules."""
        lines = self.system_prompt.split('\n')
        rules = []

        for line in lines:
            if line.strip() and line[0].isdigit() and line[1] == '.':
                rules.append(line.strip())

        return rules

    def provide_guidance(self, query: str) -> str:
        """Provide guidance based on system prompt."""
        patterns = self.analyze_prompt()

        if 'model' in query.lower():
            return self._guidance_for_models(patterns)
        elif 'delegat' in query.lower():
            return self._guidance_for_delegation(patterns)
        elif 'quality' in query.lower() or 'test' in query.lower():
            return self._guidance_for_quality(patterns)
        else:
            return self._general_guidance(patterns)

    def _guidance_for_models(self, patterns: dict) -> str:
        """Model selection guidance."""
        guidance = "## Model Selection from System Prompt\n\n"
        for model in patterns['model_guidance']:
            guidance += f"- {model}\n"
        return guidance

    def _guidance_for_delegation(self, patterns: dict) -> str:
        """Delegation pattern guidance."""
        if not self.delegation_enabled:
            return "Delegation is not enabled in this project."

        guidance = "## Delegation Rules from System Prompt\n\n"
        for rule in patterns['delegation_rules']:
            guidance += f"- {rule}\n"
        return guidance

    def _guidance_for_quality(self, patterns: dict) -> str:
        """Quality gate guidance."""
        guidance = "## Quality Gates from System Prompt\n\n"
        for gate in patterns['quality_gates']:
            guidance += f"```bash\n{gate}\n```\n"
        return guidance

    def _general_guidance(self, patterns: dict) -> str:
        """General system prompt summary."""
        guidance = "## System Prompt Summary\n\n"
        guidance += f"Models: {len(patterns['model_guidance'])} defined\n"
        guidance += f"Delegation rules: {len(patterns['delegation_rules'])} rules\n"
        guidance += f"Quality gates: {len(patterns['quality_gates'])} gates\n"
        guidance += f"Key rules: {len(patterns['key_rules'])} rules\n"
        return guidance
```

---

## SDK Integration

### SessionStateManager Extension

Extend SDK with custom state management:

```python
from htmlgraph.session import SessionStateManager

class CustomSessionStateManager(SessionStateManager):
    """Extended session management with custom logic."""

    def __init__(self):
        super().__init__()
        self.custom_state = {}

    def load_custom_state(self, key: str) -> Optional[dict]:
        """Load custom state from backup."""
        state_file = Path('.htmlgraph/.custom-state.json')
        if state_file.exists():
            data = json.loads(state_file.read_text())
            return data.get(key)
        return None

    def save_custom_state(self, key: str, value: dict) -> bool:
        """Save custom state for recovery."""
        state_file = Path('.htmlgraph/.custom-state.json')
        state_file.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        if state_file.exists():
            data = json.loads(state_file.read_text())

        data[key] = value
        state_file.write_text(json.dumps(data, indent=2))
        return True

    def get_post_compact_context(self) -> str:
        """Get enhanced post-compact context."""
        base_context = super().get_post_compact_context()

        # Add custom context
        custom = self.load_custom_state('post_compact_context')
        if custom:
            base_context += f"\n\nCustom state: {custom}"

        return base_context
```

**Using extended manager:**

```python
from htmlgraph import SDK
from custom.session_manager import CustomSessionStateManager

sdk = SDK(agent="extended")
manager = CustomSessionStateManager()

# Check if post-compact
if manager.is_post_compact():
    print("Post-compact session detected")
    custom_context = manager.get_post_compact_context()
    print(f"Enhanced context: {custom_context}")
```

---

## Testing Custom Implementations

### Unit Test Pattern

```python
import pytest
from custom_layers.my_layer import MyPersistenceLayer

class TestMyPersistenceLayer:
    """Test custom persistence layer."""

    @pytest.fixture
    def layer(self):
        """Create test layer instance."""
        return MyPersistenceLayer({
            'test_mode': True,
            'config_value': 'test'
        })

    def test_is_available(self, layer):
        """Test availability check."""
        assert layer.is_available()

    def test_store_and_retrieve(self, layer):
        """Test store and retrieve cycle."""
        prompt = "# Test Prompt\n\nTest content"

        # Store
        assert layer.store(prompt) is True

        # Retrieve
        retrieved = layer.retrieve()
        assert retrieved == prompt

    def test_retrieve_missing(self, layer):
        """Test retrieval of missing prompt."""
        with pytest.raises(PersistenceLayerError):
            layer.retrieve()

    def test_error_handling(self, layer):
        """Test error handling."""
        layer.config['invalid'] = True  # Break configuration
        assert layer.is_available() is False
```

**Run tests:**

```bash
uv run pytest tests/custom_layers/test_my_layer.py -v
```

### Integration Test Pattern

```python
def test_custom_layer_in_session():
    """Test custom layer in real session."""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        # Setup
        os.makedirs('.claude/hooks/scripts', exist_ok=True)
        prompt_file = Path('.claude/system-prompt.md')
        prompt_file.write_text("# Test Prompt")

        # Mock environment
        os.environ['CLAUDE_SESSION_ID'] = 'test-session'
        os.environ['CLAUDE_DELEGATION_ENABLED'] = 'true'

        # Import and test
        from custom.session_integration import setup_custom_layers

        result = setup_custom_layers()
        assert result.success is True
        assert result.layers_initialized == 3  # File, env, custom
```

---

## Performance Optimization

### Caching Strategies

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedPersistenceLayer:
    """Layer with intelligent caching."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache = None
        self._cache_time = None

    @property
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache is None:
            return False
        return datetime.now() - self._cache_time < self.ttl

    def retrieve(self) -> str:
        """Retrieve with caching."""
        if self._is_cache_valid:
            logger.debug("Using cached system prompt")
            return self._cache

        # Fetch fresh
        prompt = self._fetch_uncached()
        self._cache = prompt
        self._cache_time = datetime.now()
        return prompt

    def _fetch_uncached(self) -> str:
        """Actual fetch implementation."""
        raise NotImplementedError

    def invalidate_cache(self):
        """Invalidate cache (call after updates)."""
        self._cache = None
        self._cache_time = None
```

### Lazy Loading

```python
class LazyPersistenceLayer:
    """Lazy load persistence layer on first use."""

    def __init__(self, config: dict):
        self.config = config
        self._initialized = False
        self._layer = None

    @property
    def layer(self):
        """Lazy initialize layer."""
        if not self._initialized:
            self._layer = self._create_layer()
            self._initialized = True
        return self._layer

    def _create_layer(self):
        """Create actual layer (expensive operation)."""
        # Heavy initialization here
        # e.g., database connection, file system setup
        return ActualPersistenceLayer(self.config)

    def retrieve(self) -> str:
        """Retrieve via lazy-loaded layer."""
        return self.layer.retrieve()
```

---

## Debugging Tips

### Enable Debug Logging

```python
import logging

# Set debug level
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('system_prompt')

# Add detailed logging
logger.debug("System prompt retrieval started")
logger.debug(f"Trying layer 1: {layer1.__class__.__name__}")
logger.debug(f"Layer 1 available: {layer1.is_available()}")
```

### Inspect Environment Variables

```bash
# Check all CLAUDE_* variables
env | grep CLAUDE_

# Check specific variable
echo $CLAUDE_SYSTEM_PROMPT | head -50

# Check session ID
echo "Session ID: $CLAUDE_SESSION_ID"
echo "Is post-compact: $CLAUDE_IS_POST_COMPACT"
```

### Test Hook Execution

```bash
# Add verbose output to hook
# In .claude/hooks/scripts/session-start.py:

def inject_system_prompt():
    print("DEBUG: Session start hook running...")
    print(f"DEBUG: System prompt file exists: {exists('.claude/system-prompt.md')}")
    print(f"DEBUG: Environment variable set: {bool(os.getenv('CLAUDE_SYSTEM_PROMPT'))}")
    print("DEBUG: Hook execution complete")
```

### Verify Injection Worked

```python
# Check in Python
import os

system_prompt = os.getenv('CLAUDE_SYSTEM_PROMPT')
if system_prompt:
    print(f"System prompt loaded: {len(system_prompt)} characters")
    print(f"First 100 chars: {system_prompt[:100]}")
else:
    print("ERROR: System prompt not loaded!")
```

---

## Contributing

### Pull Request Guidelines

When contributing extensions:

1. **Follow patterns**: Use layer, hook, and skill patterns above
2. **Add tests**: 100% coverage for new code
3. **Document**: Include docstrings and README
4. **Backward compatible**: Don't break existing code
5. **Performance**: Profile and optimize hot paths

### Code Review Checklist

```
- [ ] Follows idempotency pattern
- [ ] Handles errors gracefully
- [ ] Has comprehensive logging
- [ ] Includes unit tests (>80% coverage)
- [ ] Includes integration tests
- [ ] Updated documentation
- [ ] Performance impact assessed
- [ ] Backward compatible
- [ ] Security review passed
```

### Example PR Template

```markdown
## What does this PR do?

[Description of extension/feature]

## Type of change

- [ ] New persistence layer
- [ ] Hook extension
- [ ] Skill addition
- [ ] SDK enhancement
- [ ] Bug fix
- [ ] Performance optimization

## Testing

- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Manual testing done
- [ ] Performance impact: [minimal/moderate/significant]

## Breaking changes

- [ ] Yes (describe below)
- [ ] No

## Checklist

- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests passing locally
```

---

## Next Steps

1. **Choose extension point**: Layer, hook, or skill
2. **Follow pattern**: Use pattern from section above
3. **Write tests**: Unit + integration tests
4. **Document**: README and docstrings
5. **Submit PR**: Follow contributing guidelines

For architecture details, see [System Prompt Architecture](SYSTEM_PROMPT_ARCHITECTURE.md).

For admin setup, see [Delegation Enforcement Guide](DELEGATION_ENFORCEMENT_ADMIN_GUIDE.md).
