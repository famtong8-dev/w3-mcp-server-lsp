import json
import subprocess
import threading
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class LSPClient:
    """Wrapper for TypeScript Language Server via LSP protocol."""

    def __init__(self, project_root: str = "."):
        self.project_root = project_root
        self.process: Optional[subprocess.Popen] = None
        self.message_id = 0
        self.lock = threading.Lock()
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization - only start server when first used."""
        if not self._initialized:
            self._start_server()
            # Send initialize on first use
            self._send_initialize()
            self._initialized = True

    def _send_initialize(self):
        """Send LSP initialize request and wait for response."""
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootPath": self.project_root,
                "capabilities": {
                    "textDocument": {
                        "synchronization": {"didSave": True},
                        "completion": {},
                        "hover": {},
                        "definition": {},
                        "references": {},
                    }
                },
            },
        }
        self._send_message(init_msg)
        logger.info("Initialization sent")

        # Wait for initialize response (skip notifications)
        while True:
            response = self._read_response()
            if not response:
                logger.warning("No initialize response received")
                break
            if response.get("id") == 1:
                logger.info("Initialize response received")
                # Send initialized notification
                self._send_message({
                    "jsonrpc": "2.0",
                    "method": "initialized",
                    "params": {}
                })
                break
            else:
                # Skip notifications and other messages
                logger.debug(f"Skipping notification: {response.get('method')}")

    def _start_server(self):
        """Start typescript-language-server process."""
        try:
            self.process = subprocess.Popen(
                ["typescript-language-server", "--stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Use binary mode to avoid text encoding issues with LSP protocol
            )
            logger.info("TypeScript Language Server started")
            # Don't send initialize here - do it lazily on first use
        except FileNotFoundError:
            try:
                self.process = subprocess.Popen(
                    ["npx", "typescript-language-server", "--stdio"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                logger.info("TypeScript Language Server started (via npx)")
            except Exception as e:
                logger.error(f"Failed to start LSP server: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to start LSP server: {e}")
            raise

    def _send_message(self, msg: dict):
        """Send JSON-RPC message to server."""
        content = json.dumps(msg).encode('utf-8')
        header = f"Content-Length: {len(content)}\r\n\r\n".encode('utf-8')

        if self.process and self.process.stdin:
            self.process.stdin.write(header)
            self.process.stdin.write(content)
            self.process.stdin.flush()

    def _read_response(self) -> Optional[dict]:
        """Read JSON-RPC response from server (binary mode)."""
        if not self.process or not self.process.stdout:
            return None

        try:
            # Read headers in binary mode
            headers = {}
            header_data = b""

            # Read until we get \r\n\r\n
            while True:
                byte = self.process.stdout.read(1)
                if not byte:
                    logger.error("EOF while reading headers")
                    return None

                header_data += byte

                if header_data.endswith(b"\r\n\r\n"):
                    break

            # Parse headers
            header_str = header_data.decode('utf-8')
            for line in header_str.split("\r\n"):
                if not line:
                    continue
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

            logger.debug(f"LSP headers: {headers}")

            # Read content
            content_length = int(headers.get("Content-Length", 0))
            if content_length == 0:
                logger.debug("No content length")
                return None

            logger.debug(f"Reading {content_length} bytes")
            content = self.process.stdout.read(content_length)
            logger.debug(f"Got: {content[:100]}")

            return json.loads(content.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error reading response: {e}")
            import traceback
            traceback.print_exc()
            return None

    def goto_definition(self, file_uri: str, line: int, char: int) -> Optional[dict]:
        """Get definition location. Line and char are 0-indexed."""
        self._ensure_initialized()

        # First open the document so the server knows about it
        with open(file_uri, 'r') as f:
            content = f.read()
        self.open_document(file_uri, 'javascript', content)

        with self.lock:
            self.message_id += 1
            msg = {
                "jsonrpc": "2.0",
                "id": self.message_id,
                "method": "textDocument/definition",
                "params": {
                    "textDocument": {"uri": self._normalize_uri(file_uri)},
                    "position": {"line": line, "character": char},
                },
            }
            logger.debug(f"Sending goto_definition request (id={self.message_id})")
            self._send_message(msg)

            # Read responses until we get the one with our message ID
            while True:
                response = self._read_response()
                if not response:
                    logger.warning("No response for goto_definition")
                    return None

                if response.get("id") == self.message_id:
                    logger.debug(f"Got goto_definition response")
                    if "result" in response:
                        result = response["result"]
                        # Result can be a Location or array of Locations
                        if isinstance(result, list) and result:
                            return result[0]
                        return result
                    return None
                else:
                    # Skip notifications and other messages
                    logger.debug(f"Skipping message (id={response.get('id')}, method={response.get('method')})")

    def hover(self, file_uri: str, line: int, char: int) -> Optional[dict]:
        """Get hover information."""
        self._ensure_initialized()

        # First open the document so the server knows about it
        with open(file_uri, 'r') as f:
            content = f.read()
        self.open_document(file_uri, 'javascript', content)

        with self.lock:
            self.message_id += 1
            msg = {
                "jsonrpc": "2.0",
                "id": self.message_id,
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": self._normalize_uri(file_uri)},
                    "position": {"line": line, "character": char},
                },
            }
            logger.debug(f"Sending hover request (id={self.message_id})")
            self._send_message(msg)

            # Read responses until we get the one with our message ID
            while True:
                response = self._read_response()
                if not response:
                    logger.warning("No response for hover")
                    return None

                if response.get("id") == self.message_id:
                    logger.debug(f"Got hover response")
                    if "result" in response:
                        return response["result"]
                    return None
                else:
                    # Skip notifications and other messages
                    logger.debug(f"Skipping message (id={response.get('id')}, method={response.get('method')})")

    def find_references(self, file_uri: str, line: int, char: int) -> Optional[list]:
        """Find all references to symbol."""
        self._ensure_initialized()

        # First open the document so the server knows about it
        with open(file_uri, 'r') as f:
            content = f.read()
        self.open_document(file_uri, 'javascript', content)

        with self.lock:
            self.message_id += 1
            msg = {
                "jsonrpc": "2.0",
                "id": self.message_id,
                "method": "textDocument/references",
                "params": {
                    "textDocument": {"uri": self._normalize_uri(file_uri)},
                    "position": {"line": line, "character": char},
                    "context": {"includeDeclaration": True},
                },
            }
            logger.debug(f"Sending find_references request (id={self.message_id})")
            self._send_message(msg)

            # Read responses until we get the one with our message ID
            while True:
                response = self._read_response()
                if not response:
                    logger.warning("No response for find_references")
                    return None

                if response.get("id") == self.message_id:
                    logger.debug(f"Got find_references response")
                    if "result" in response:
                        return response["result"]
                    return None
                else:
                    # Skip notifications and other messages
                    logger.debug(f"Skipping message (id={response.get('id')}, method={response.get('method')})")

    def open_document(self, file_uri: str, language_id: str, content: str):
        """Notify server of opened document."""
        msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": self._normalize_uri(file_uri),
                    "languageId": language_id,
                    "version": 1,
                    "text": content,
                }
            },
        }
        self._send_message(msg)

    def _normalize_uri(self, path: str) -> str:
        """Convert file path to file:// URI."""
        if path.startswith("file://"):
            return path
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        return f"file://{path}"

    def close(self):
        """Close the server."""
        if self.process:
            self.process.terminate()
