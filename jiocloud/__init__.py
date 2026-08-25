"""
Unofficial Jio AI Cloud Python SDK

LEGAL NOTICE: This is an independent, unofficial project. It is NOT affiliated
with, associated with, authorized by, endorsed by, or in any way officially
connected with Reliance Jio Infocomm Ltd. or any of its subsidiaries.
"Jio" and "Jio AI Cloud" are trademarks of their respective owners; they are
used here solely for nominative reference to the service this tool
interoperates with. See docs/DISCLAIMER.md and docs/LEGAL.md.

This software is provided for personal data portability, interoperability,
and educational backup purposes under fair-use guidelines, "AS IS", without
warranty of any kind. Credentials stay on your machine and are sent only to
official Jio AI Cloud endpoints over TLS.
"""

__version__ = "2.0.0"
__author__ = "Unofficial Jio Cloud API Project"

from .client import JioCloudClient
from .auth import JioCloudAuth
from .agent_tools import AGENT_TOOLS_SCHEMA, JioAgentBridge, handle_tool_call
from .models import (
    JioFile,
    JioFolder,
    JioStorageQuota,
    JioUserProfile,
    JioShareLink,
    JioBoard,
    JioBoardMember,
    JioFileVersion,
    format_bytes
)
from .exceptions import (
    JioCloudError,
    AuthenticationError,
    ForbiddenError,
    ObjectNotFoundError,
    InvalidRequestError,
    QuotaExceededError,
    RateLimitError,
    ConflictError,
    PayloadTooLargeError,
    ServerError,
    NetworkError
)

__all__ = [
    "JioCloudClient",
    "JioCloudAuth",
    "AGENT_TOOLS_SCHEMA",
    "JioAgentBridge",
    "handle_tool_call",
    "JioFile",
    "JioFolder",
    "JioStorageQuota",
    "JioUserProfile",
    "JioShareLink",
    "JioBoard",
    "JioBoardMember",
    "JioFileVersion",
    "format_bytes",
    "JioCloudError",
    "AuthenticationError",
    "ForbiddenError",
    "ObjectNotFoundError",
    "InvalidRequestError",
    "QuotaExceededError",
    "RateLimitError",
    "ConflictError",
    "PayloadTooLargeError",
    "ServerError",
    "NetworkError"
]
