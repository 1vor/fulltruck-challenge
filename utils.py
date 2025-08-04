# utils.py
import asyncio
from email.message import Message
import json
import httpx
from pydantic import TypeAdapter

async def api_call(method, url, payload=None, params=None, headers=None, files=None, base_url='',
                   timeout: int = 10, retries: int = 3, backoff_factor: float = 0.5, app=None):
    transport = None if not app else httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(base_url=base_url, transport=transport) as ac:
        call_map = {
            "get": ac.get,
            "post": ac.post,
            "put": ac.put,
            "delete": ac.delete,
            "patch": ac.patch
        }
        
        if method not in call_map:
            raise ValueError(f"Unsupported API type: {method}")

        # Some methods might not accept 'json' argument when it's None (like GET, DELETE). so i conditionally pass arguments based on the method.
        for attempt in range(retries):
            try:
                if files is not None:
                    data = None
                    if payload:
                        data = payload
                    response = await call_map[method](url, headers=headers, data=data, files=files, timeout=timeout)
                elif payload is not None:
                    if isinstance(payload, dict):
                        payload = TypeAdapter(dict).dump_python(payload)
                    elif isinstance(payload, (list, tuple)) and len(payload) and isinstance(payload[0], dict):
                        payload = [TypeAdapter(dict).dump_python(d) for d in payload]
                    response = await call_map[method](url, headers=headers, json=payload, timeout=timeout)
                else:
                    response = await call_map[method](url, headers=headers, params=params, timeout=timeout)
                break
            except httpx.HTTPStatusError as e:
                print(f"Attempt {attempt + 1}/{retries} failed with status {e.response.status_code}: {e.response.text}")
                if attempt + 1 == retries:
                    raise
                await asyncio.sleep(backoff_factor) 

        if 'application/json' in response.headers.get('Content-Type', ''):
            try:
                if 'application/json' in response.headers.get('Content-Type', ''):
                    data = response.json()
                else:
                    print(f"Unexpected Content-Type: {response.headers.get('Content-Type')}")
            except json.JSONDecodeError as e:
                data = None
        else:
            # Handle binary response
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                # Extract filename from Content-Disposition header if present
                msg = Message()
                msg['content-disposition'] = content_disposition
                filename = msg.get_filename()
            else:
                filename = None
            data = {"filename":filename, "content":response.content}

    return response, data