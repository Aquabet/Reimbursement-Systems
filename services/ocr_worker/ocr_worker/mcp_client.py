import httpx
import json
import base64


class McpClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=60.0)

    def extract_text(self, image_bytes, mime_type="image/jpeg"):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "ocr/extract_text",
            "params": {
                "image": {
                    "data": base64.b64encode(image_bytes).decode('utf-8'),
                    "mime_type": mime_type
                }
            }
        }

        response = self.client.post(
            f"{self.base_url}/mcp",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        result = response.json()
        if "error" in result:
            raise Exception(f"MCP OCR error: {result['error']}")

        return result.get("result", {}).get("text", "")

    def close(self):
        self.client.close()
