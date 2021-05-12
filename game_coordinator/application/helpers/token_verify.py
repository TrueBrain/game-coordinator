import asyncio
import logging

from .ip import get_family
from ...openttd.protocol.enums import ConnectionType

log = logging.getLogger(__name__)


class ConnectAndCloseProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        transport.close()


class TokenVerify:
    def __init__(self, token, server):
        self.token = token
        self._server = server
        self._family = {}

        self._stuns = 0

    def disconnect(self):
        pass

    def _get_stun_info(self, prefix, interface_number):
        return self._server._application.storage_stun.get(f"{prefix}{self.token}", {}).get(
            interface_number, (None, None)
        )

    async def stun_result(self, prefix, interface_number, result):
        self._stuns += 1

        if not result:
            # If we got two results, assume it is an IPv4 / IPv6 pair, and we
            # are done. Although OpenTTD client implements this, the protocol
            # leaves room for this to be a false statement. Yet, it makes
            # registering a lot quicker, so we are going with it for now.
            if self._stuns == 2:
                self._server._detection_done.set()
            return

        server_ip, _ = self._get_stun_info("V", interface_number)
        if server_ip is None:
            log.info("STUN info not received yet, retrying ..")
            # The message over the STUN protocol can be a bit later than the
            # STUN_RESULT packet over the GC protocol, so wait a bit till it
            # (possibly) arrives.
            await asyncio.sleep(0.1)
            server_ip, _ = self._get_stun_info("V", interface_number)

        if server_ip is None:
            log.error("Got STUN result packet but we don't have a STUN result on file")
            return

        family = get_family(server_ip)
        self._server.server_ip[family] = server_ip

        # First, see if we can direct connect to this IP.
        if await self._detect_direct_ip(server_ip):
            pass
        else:
            # We don't really try a STUN request; we just assumes every client
            # can be STUN'd, so we gather stats for those that cannot.
            self._server.connection_type[family] = ConnectionType.CONNECTION_TYPE_STUN

        if self._stuns == 2:
            self._server._detection_done.set()

    async def _detect_direct_ip(self, ip):
        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().create_connection(
                    lambda: ConnectAndCloseProtocol(), host=str(ip), port=self._server.server_port
                ),
                1,
            )
            self._server.connection_type[get_family(ip)] = ConnectionType.CONNECTION_TYPE_DIRECT
        except (OSError, ConnectionRefusedError, asyncio.TimeoutError):
            return False

        return True
