"""Small forward proxy that permits browser connections only to public IPs."""

import asyncio
import ipaddress
import logging
from urllib.parse import urlsplit

LOG = logging.getLogger(__name__)
HEADER_LIMIT = 64 * 1024


async def _public_address(host: str, port: int) -> tuple[str, int]:
    loop = asyncio.get_running_loop()
    addresses = await asyncio.wait_for(loop.getaddrinfo(host, port, type=0), timeout=10)
    candidates = []
    for _, _, _, _, address in addresses:
        ip = ipaddress.ip_address(address[0])
        if not ip.is_global:
            raise ValueError("Destination resolves to a non-public address")
        candidates.append(address)
    if not candidates:
        raise ValueError("Destination has no addresses")
    return candidates[0][0], port


async def _relay(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    upstream = None
    try:
        header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=10)
        if len(header) > HEADER_LIMIT:
            raise ValueError("Headers too large")
        first_line = header.split(b"\r\n", 1)[0].decode("ascii")
        method, target, version = first_line.split(" ", 2)
        if version not in {"HTTP/1.0", "HTTP/1.1"}:
            raise ValueError("Unsupported HTTP version")
        if method == "CONNECT":
            parsed = urlsplit(f"//{target}")
            host, port = parsed.hostname, parsed.port
            if parsed.username or parsed.password or parsed.path or parsed.query:
                raise ValueError("Invalid CONNECT target")
        else:
            parsed = urlsplit(target)
            host, port = (
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
            )
            if parsed.scheme != "http" or parsed.username or parsed.password:
                raise ValueError("Only HTTP proxy requests are supported")
        if not host or not 1 <= port <= 65535:
            raise ValueError("Invalid destination")
        address, port = await _public_address(host, port)
        upstream_reader, upstream = await asyncio.wait_for(
            asyncio.open_connection(address, port), timeout=10
        )
        if method == "CONNECT":
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        else:
            path = parsed.path or "/"
            if parsed.query:
                path += f"?{parsed.query}"
            _, remaining = header.split(b"\r\n", 1)
            fields = [
                line
                for line in remaining.split(b"\r\n")
                if line
                and line.split(b":", 1)[0].lower()
                not in {b"connection", b"proxy-connection", b"proxy-authorization"}
            ]
            upstream.write(
                f"{method} {path} {version}\r\n".encode()
                + b"\r\n".join(fields)
                + b"\r\nConnection: close\r\n\r\n"
            )
            await upstream.drain()
        await writer.drain()
        tasks = {
            asyncio.create_task(_relay(reader, upstream)),
            asyncio.create_task(_relay(upstream_reader, writer)),
        }
        _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except (
        ValueError,
        UnicodeError,
        TimeoutError,
        asyncio.LimitOverrunError,
        asyncio.IncompleteReadError,
        OSError,
    ) as exc:
        LOG.warning("Rejected browser request: %s", type(exc).__name__)
        writer.write(
            b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
        )
        try:
            await writer.drain()
        except ConnectionError:
            pass
    finally:
        writer.close()
        if upstream is not None:
            upstream.close()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    server = await asyncio.start_server(
        handle_client, "0.0.0.0", 3128, limit=HEADER_LIMIT
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
