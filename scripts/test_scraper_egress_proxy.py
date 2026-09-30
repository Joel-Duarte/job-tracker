import asyncio
import unittest
from unittest.mock import patch

from scraper_egress_proxy import _public_address, handle_client


class ScraperEgressProxyTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_private_and_mixed_dns_answers(self):
        loop = asyncio.get_running_loop()
        answers = [
            (2, 1, 6, "", ("93.184.215.14", 443)),
            (2, 1, 6, "", ("127.0.0.1", 443)),
        ]
        with patch.object(loop, "getaddrinfo", return_value=answers):
            with self.assertRaises(ValueError):
                await _public_address("example.com", 443)

    async def test_public_answer_is_pinned(self):
        loop = asyncio.get_running_loop()
        answers = [(2, 1, 6, "", ("93.184.215.14", 443))]
        with patch.object(loop, "getaddrinfo", return_value=answers):
            self.assertEqual(
                await _public_address("example.com", 443), ("93.184.215.14", 443)
            )

    async def test_connect_to_loopback_is_denied(self):
        server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"CONNECT 127.0.0.1:443 HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
            await writer.drain()
            response = await reader.read()
            self.assertIn(b"403 Forbidden", response)
            writer.close()
            await writer.wait_closed()

    async def test_connect_tunnels_to_the_checked_address(self):
        async def echo(reader, writer):
            writer.write(await reader.read(4))
            await writer.drain()
            writer.close()

        upstream = await asyncio.start_server(echo, "127.0.0.1", 0)
        proxy = await asyncio.start_server(handle_client, "127.0.0.1", 0)
        async with upstream, proxy:
            upstream_port = upstream.sockets[0].getsockname()[1]
            proxy_port = proxy.sockets[0].getsockname()[1]
            with patch(
                "scraper_egress_proxy._public_address",
                return_value=("127.0.0.1", upstream_port),
            ):
                reader, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
                writer.write(
                    f"CONNECT public.example:{upstream_port} HTTP/1.1\r\n\r\n".encode()
                )
                await writer.drain()
                self.assertIn(
                    b"200 Connection Established", await reader.readuntil(b"\r\n\r\n")
                )
                writer.write(b"PING")
                await writer.drain()
                self.assertEqual(await reader.read(4), b"PING")
                writer.close()
                await writer.wait_closed()

    async def test_http_request_uses_origin_form_and_closes_upstream(self):
        seen = []

        async def respond(reader, writer):
            seen.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK"
            )
            await writer.drain()
            writer.close()

        upstream = await asyncio.start_server(respond, "127.0.0.1", 0)
        proxy = await asyncio.start_server(handle_client, "127.0.0.1", 0)
        async with upstream, proxy:
            upstream_port = upstream.sockets[0].getsockname()[1]
            proxy_port = proxy.sockets[0].getsockname()[1]
            with patch(
                "scraper_egress_proxy._public_address",
                return_value=("127.0.0.1", upstream_port),
            ):
                reader, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
                writer.write(
                    f"GET http://public.example:{upstream_port}/job HTTP/1.1\r\nHost: public.example\r\n\r\n".encode()
                )
                await writer.drain()
                self.assertIn(b"200 OK", await reader.read())
                self.assertTrue(seen[0].startswith(b"GET /job HTTP/1.1\r\n"))
                self.assertIn(b"Connection: close", seen[0])
                writer.close()
                await writer.wait_closed()
