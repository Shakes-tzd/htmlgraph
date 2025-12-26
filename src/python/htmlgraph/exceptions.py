"""Custom exceptions for HtmlGraph."""


class HtmlGraphError(Exception):
    """Base exception for all HtmlGraph errors."""
    pass


class NodeNotFoundError(HtmlGraphError):
    """Raised when a node cannot be found."""

    def __init__(self, node_type: str, node_id: str):
        self.node_type = node_type
        self.node_id = node_id
        super().__init__(f"{node_type.capitalize()} not found: {node_id}")


class SessionNotFoundError(HtmlGraphError):
    """Raised when a session cannot be found."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class ClaimConflictError(HtmlGraphError):
    """Raised when a claim operation conflicts with existing claim."""

    def __init__(self, node_id: str, current_owner: str):
        self.node_id = node_id
        self.current_owner = current_owner
        super().__init__(f"Node {node_id} already claimed by {current_owner}")


class ValidationError(HtmlGraphError):
    """Raised when validation fails."""
    pass
