"""Provide useful tools for ETL classes."""


class DownloadException(Exception):
    """Exception for failures relating to source file downloads."""

    def __init__(self, *args, **kwargs):  # noqa: ANN204
        """Initialize exception."""
        super().__init__(*args, **kwargs)
