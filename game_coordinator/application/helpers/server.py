import asyncio
import logging

from .enums import Family
from .token_verify import TokenVerify

from ...openttd.protocol.enums import ConnectionType

log = logging.getLogger(__name__)


class Server:
    def __init__(self, join_key, application, source, game_type, server_port):
        self._application = application
        self._source = source
        self._task = None

        self.connection_type = {
            Family.IPv4: ConnectionType.CONNECTION_TYPE_ISOLATED,
            Family.IPv6: ConnectionType.CONNECTION_TYPE_ISOLATED,
        }

        self.server_ip = {
            Family.IPv4: None,
            Family.IPv6: None,
        }

        self.server_port = server_port
        self.join_key = join_key
        self.game_type = game_type
        self.info = {}

    def disconnect(self):
        if self._task:
            self._task.cancel()

    def update(self, info):
        if info["newgrfs"] is None:
            info["newgrfs"] = self.info["newgrfs"]
        self.info = info

    async def detect_connection(self):
        self._task = asyncio.create_task(self._start_detection())

    async def _start_detection(self):
        try:
            await self._real_start_detection()
        except asyncio.CancelledError:
            pass

    async def _real_start_detection(self):
        token = self._application.create_token(lambda token: TokenVerify(token, self))
        self._detection_done = asyncio.Event()

        await self._source.protocol.send_PACKET_COORDINATOR_SERVER_STUN_REQUEST(f"V{token.token}")

        try:
            await asyncio.wait_for(self._detection_done.wait(), 4)
        except asyncio.TimeoutError:
            pass

        # Make sure the server frees the resources assigned to this.
        await self._source.protocol.send_PACKET_COORDINATOR_SERVER_CONNECT_FAILED(f"V{token.token}")
        self._application.delete_token(token.token)

        log.info(
            f"Happy server {self.join_key}: "
            + " ".join(
                f"{self.server_ip[family]} ({self.connection_type[family].name[16:]})" for family in self.server_ip
            )
        )

        # Find out the best ConnectionType of the known families
        for ct in (
            ConnectionType.CONNECTION_TYPE_DIRECT,
            ConnectionType.CONNECTION_TYPE_STUN,
            ConnectionType.CONNECTION_TYPE_TURN,
        ):
            if ct in self.connection_type.values():
                break
        else:
            ct = ConnectionType.CONNECTION_TYPE_ISOLATED

        await self._source.protocol.send_PACKET_COORDINATOR_SERVER_REGISTER_ACK(
            join_key=self.join_key, connection_type=ct
        )

        self._task = None
