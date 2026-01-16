"""Ensure CLI and SDK call same operations layer."""

from pathlib import Path

from htmlgraph import SDK, operations


def test_server_operations_exist():
    """Verify server operations are available in operations module."""
    assert hasattr(operations, "start_server")
    assert hasattr(operations, "stop_server")
    assert hasattr(operations, "get_server_status")


def test_hooks_operations_exist():
    """Verify hooks operations are available in operations module."""
    assert hasattr(operations, "install_hooks")
    assert hasattr(operations, "list_hooks")
    assert hasattr(operations, "validate_hook_config")


def test_events_operations_exist():
    """Verify events operations are available in operations module."""
    assert hasattr(operations, "export_sessions")
    assert hasattr(operations, "query_events")
    assert hasattr(operations, "rebuild_index")
    assert hasattr(operations, "get_event_stats")


def test_analytics_operations_exist():
    """Verify analytics operations are available in operations module."""
    assert hasattr(operations, "analyze_session")
    assert hasattr(operations, "analyze_project")


def test_sdk_has_server_methods():
    """SDK should have server management methods."""
    sdk = SDK()
    assert hasattr(sdk, "start_server")
    assert hasattr(sdk, "stop_server")
    assert hasattr(sdk, "get_server_status")


def test_sdk_has_hooks_methods():
    """SDK should have hooks management methods."""
    sdk = SDK()
    assert hasattr(sdk, "install_hooks")
    assert hasattr(sdk, "list_hooks")
    assert hasattr(sdk, "validate_hook_config")


def test_sdk_has_events_methods():
    """SDK should have event management methods."""
    sdk = SDK()
    assert hasattr(sdk, "export_sessions")
    assert hasattr(sdk, "query_events")
    assert hasattr(sdk, "rebuild_event_index")
    assert hasattr(sdk, "get_event_stats")


def test_sdk_has_analytics_methods():
    """SDK should have analytics methods."""
    sdk = SDK()
    assert hasattr(sdk, "analyze_session")
    assert hasattr(sdk, "analyze_project")


def test_operations_return_types():
    """Verify operations return correct types."""
    # Server operations
    assert hasattr(operations.ServerStartResult, "__dataclass_fields__")
    assert hasattr(operations.ServerStatus, "__dataclass_fields__")
    assert hasattr(operations.ServerHandle, "__dataclass_fields__")

    # Hooks operations
    assert hasattr(operations.HookInstallResult, "__dataclass_fields__")
    assert hasattr(operations.HookListResult, "__dataclass_fields__")
    assert hasattr(operations.HookValidationResult, "__dataclass_fields__")

    # Events operations
    assert hasattr(operations.EventExportResult, "__dataclass_fields__")
    assert hasattr(operations.EventQueryResult, "__dataclass_fields__")
    assert hasattr(operations.EventRebuildResult, "__dataclass_fields__")
    assert hasattr(operations.EventStats, "__dataclass_fields__")

    # Analytics operations
    assert hasattr(operations.AnalyticsSessionResult, "__dataclass_fields__")
    assert hasattr(operations.AnalyticsProjectResult, "__dataclass_fields__")


def test_operations_module_exports():
    """Verify operations module exports all expected symbols."""
    expected_exports = [
        # Server operations
        "start_server",
        "stop_server",
        "get_server_status",
        "ServerHandle",
        "ServerStatus",
        "ServerStartResult",
        # Hooks operations
        "install_hooks",
        "list_hooks",
        "validate_hook_config",
        "HookInstallResult",
        "HookListResult",
        "HookValidationResult",
        # Events operations
        "export_sessions",
        "query_events",
        "rebuild_index",
        "get_event_stats",
        "EventExportResult",
        "EventQueryResult",
        "EventRebuildResult",
        "EventStats",
        # Analytics operations
        "analyze_session",
        "analyze_project",
        "AnalyticsSessionResult",
        "AnalyticsProjectResult",
    ]

    for symbol in expected_exports:
        assert hasattr(operations, symbol), f"operations module missing {symbol}"


def test_cli_sdk_both_use_operations(tmp_path):
    """
    Verify both CLI and SDK use operations layer by checking imports.

    This is a static analysis test - we verify the code structure,
    not the runtime behavior (which would require full setup).
    """
    import htmlgraph.cli as cli_module
    import htmlgraph.sdk as sdk_module

    # Read CLI source - check the package directory for any submodule using operations
    cli_dir = Path(cli_module.__file__).parent
    cli_uses_operations = False
    for py_file in cli_dir.glob("*.py"):
        content = py_file.read_text()
        if (
            "from htmlgraph.operations import" in content
            or "import htmlgraph.operations" in content
        ):
            cli_uses_operations = True
            break
    assert cli_uses_operations, "CLI should import from operations module"

    # Read SDK source - check the package directory for any submodule using operations
    sdk_dir = Path(sdk_module.__file__).parent
    sdk_uses_operations = False
    for py_file in sdk_dir.glob("*.py"):
        content = py_file.read_text()
        if (
            "from htmlgraph.operations import" in content
            or "import htmlgraph.operations" in content
        ):
            sdk_uses_operations = True
            break
    assert sdk_uses_operations, "SDK should import from operations module"


def test_operations_errors_exported():
    """Verify operations module exports error classes."""
    from htmlgraph.operations.hooks import HookConfigError, HookInstallError
    from htmlgraph.operations.server import PortInUseError, ServerStartError

    # These should be importable and be Exception subclasses
    assert issubclass(ServerStartError, RuntimeError)
    assert issubclass(PortInUseError, ServerStartError)
    assert issubclass(HookConfigError, ValueError)
    assert issubclass(HookInstallError, RuntimeError)
