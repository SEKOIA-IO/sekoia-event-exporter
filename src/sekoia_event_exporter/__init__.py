"""Sekoia.io Event Exporter - Export search job results from Sekoia.io API."""

from importlib.metadata import version

__version__ = version("sekoia-event-exporter")
__author__ = "Sekoia.io"
__license__ = "MIT"

from .cli import main

__all__ = ["main"]
