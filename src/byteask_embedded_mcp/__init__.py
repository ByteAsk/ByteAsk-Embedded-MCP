"""byteask-embedded-mcp: the open-source MCP server behind ByteAsk Embedded Docs.

A source-grounded, page-cited evidence-retrieval MCP server for coding agents.
This package ships the *server* — tools, transports, auth, rendering — plus a
pluggable :class:`~byteask_embedded_mcp.backend.SearchBackend` interface and a
small in-memory :class:`~byteask_embedded_mcp.backend.SampleBackend` so it runs
out of the box. The hosted ByteAsk endpoint plugs in a private retrieval backend
and a licensed corpus; neither is part of this repository.

The server object and CLI entrypoint live in :mod:`byteask_embedded_mcp.server`.
"""

__version__ = "0.1.0"
