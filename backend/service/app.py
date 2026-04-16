"""
Compatibility module.

This keeps legacy startup commands working while ensuring the real
analysis pipeline is always used instead of a placeholder endpoint.
"""

from backend.service.fastapi_server import app
