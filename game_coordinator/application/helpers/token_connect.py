import asyncio
import logging

from .enums import (
    ConnectType,
    Family,
)
from .ip import (
    get_family,
    ip_to_str,
)
from ...openttd.protocol.enums import ConnectionType

log = logging.getLogger(__name__)


class TokenConnect:
    def __init__(self, token, server, client_source):
        self.token = token

        self._server = server
        self.connect_state = [ConnectType.UNKNOWN, Family.UNKNOWN, Family.UNKNOWN]

        self._server_source = server._source
        self._client_source = client_source

        self._task = None
        self._is_connected = False
        self._stuns = 0
        self._tracking_number = 0

        self._server_family = {}
        self._client_family = {}
        self._server_stun = {}
        self._client_stun = {}
        self._stun_tried = {
            Family.IPv4: False,
            Family.IPv6: False,
        }

        self._turn_server = None
        self._turn_client = None
        self._turn_connected = asyncio.Event()

        self._wait_step = asyncio.Event()
        self._stun_done = False

        self._connect_methods = asyncio.Queue()
        if self._server.connection_type[get_family(client_source.ip)] == ConnectionType.CONNECTION_TYPE_DIRECT:
            self._connect_methods.put_nowait(lambda: self.connect_direct(get_family(client_source.ip)))
        self._connect_methods.put_nowait(lambda: self.connect_start_stun())

    def _get_stun_info(self, prefix, interface_number):
        return self._server._application.storage_stun.get(f"{prefix}{self.token}", {}).get(
            interface_number, (None, None)
        )

    def disconnect(self):
        if self._task:
            self._task.cancel()

    async def connect(self):
        self._task = asyncio.create_task(self._start_connect())

    async def connect_failed(self, prefix, tracking_number):
        if self._tracking_number == tracking_number:
            self._wait_step.set()

    async def connected(self):
        self._is_connected = True
        self._wait_step.set()

    async def stun_result(self, prefix, interface_number, result):
        self._stuns += 1

        if not result:
            return

        ip, port = self._get_stun_info(prefix, interface_number)
        if ip is None:
            log.info("STUN info not received yet, retrying ..")
            # The message over the STUN protocol can be a bit later than the
            # STUN_RESULT packet over the GC protocol, so wait a bit till it
            # (possibly) arrives.
            await asyncio.sleep(0.1)
            ip, port = self._get_stun_info("V", interface_number)

        if ip is None:
            log.error("Got STUN result packet but we don't have a STUN result on file")
            return

        family = get_family(ip)

        if prefix == "C":
            # If any of the STUN connections show another family than the GC
            # connection has, and the server supports this family, schedule a
            # direct connection.
            if (
                family != get_family(self._client_source.ip)
                and self._server.connection_type[family] == ConnectionType.CONNECTION_TYPE_DIRECT
            ):
                self._connect_methods.put_nowait(lambda: self.connect_direct(family))

        if prefix == "S":
            self._server_stun[family] = (interface_number, ip, port)
        else:
            self._client_stun[family] = (interface_number, ip, port)

        # Find a matching IPv4 or IPv6, given we haven't tried that pair yet.
        for server_family in self._server_stun:
            for client_family in self._client_stun:
                if client_family == server_family and not self._stun_tried[client_family]:
                    break
            else:
                continue

            break
        else:
            return

        # Found a matching STUN pair.
        self._stun_tried[client_family] = True
        self._connect_methods.put_nowait(lambda: self.connect_stun(client_family))

    async def _start_connect(self):
        try:
            await self._real_start_connect()
        except asyncio.CancelledError:
            pass

    async def _real_start_connect(self):
        _final_attempt = False

        while True:
            if self._stuns == 4 and self._connect_methods.empty():
                # If we got two * two results, assume it is an IPv4 / IPv6 pair,
                # and we are done. Although OpenTTD client implements this, the
                # protocol leaves room for this to be a false statement. Yet, it
                # makes joining a lot quicker, so we are going with it for now.
                _final_attempt = True
                func = self.connect_turn
            else:
                # Wait for a new method to present itself.
                try:
                    func = await asyncio.wait_for(self._connect_methods.get(), 1)
                except asyncio.TimeoutError:
                    _final_attempt = True
                    func = self.connect_turn

            # Try the new method.
            self._wait_step.clear()
            await func()

            # Wait for the method to result in anything useful.
            try:
                await asyncio.wait_for(self._wait_step.wait(), 4)
            except asyncio.TimeoutError:
                pass

            # If we are now connected or this was the final attempt, we are all done.
            if self._is_connected or _final_attempt:
                break

        if self._is_connected:
            log.info(
                f"Happy customer {self._client_source.ip} via {self.connect_state[0].value} (S: {self.connect_state[1].value}, C: {self.connect_state[2].value})"
            )
        else:
            # Even TURN failed, so we should tell the clients we have no way
            # of connecting them.
            await self._server_source.protocol.send_PACKET_COORDINATOR_SERVER_CONNECT_FAILED(f"S{self.token}")
            await self._client_source.protocol.send_PACKET_COORDINATOR_SERVER_CONNECT_FAILED(f"C{self.token}")

            log.info(f"Sad customer {self._client_source.ip} for {self._server_source.ip}")

        self._task = None

    async def connect_direct(self, family):
        self._tracking_number += 1
        self.connect_state = [ConnectType.DIRECT, family, family]
        await self._client_source.protocol.send_PACKET_COORDINATOR_SERVER_DIRECT_CONNECT(
            f"C{self.token}", self._tracking_number, ip_to_str(self._server.server_ip[family]), self._server.server_port
        )

    async def connect_start_stun(self):
        await self._server_source.protocol.send_PACKET_COORDINATOR_SERVER_STUN_REQUEST(f"S{self.token}")
        await self._client_source.protocol.send_PACKET_COORDINATOR_SERVER_STUN_REQUEST(f"C{self.token}")

        self._wait_step.set()

    async def connect_stun(self, family):
        self._tracking_number += 1
        self.connect_state = [ConnectType.STUN, family, family]
        await self._client_source.protocol.send_PACKET_COORDINATOR_SERVER_STUN_CONNECT(
            f"C{self.token}",
            self._tracking_number,
            self._client_stun[family][0],
            ip_to_str(self._server_stun[family][1]),
            self._server_stun[family][2],
        )
        await self._server_source.protocol.send_PACKET_COORDINATOR_SERVER_STUN_CONNECT(
            f"S{self.token}",
            self._tracking_number,
            self._server_stun[family][0],
            ip_to_str(self._client_stun[family][1]),
            self._client_stun[family][2],
        )

    async def connect_turn(self):
        self._tracking_number += 1
        self.connect_state = [ConnectType.TURN, Family.UNKNOWN, Family.UNKNOWN]
        # TODO -- Make a pool of TURN servers
        await self._server_source.protocol.send_PACKET_COORDINATOR_SERVER_TURN_CONNECT(
            f"S{self.token}", self._tracking_number, "coordinator.openttd.org", 3974
        )
        await self._client_source.protocol.send_PACKET_COORDINATOR_SERVER_TURN_CONNECT(
            f"C{self.token}", self._tracking_number, "coordinator.openttd.org", 3974
        )
