import logging
import secrets

from collections import defaultdict

from .helpers.encode import human_encode
from .helpers.server import Server
from .helpers.token_connect import TokenConnect
from ..openttd.protocol.enums import NetworkCoordinatorErrorType

log = logging.getLogger(__name__)


class Application:
    def __init__(self):
        super().__init__()

        self._servers = {}
        self._tokens = {}

        self.storage_stun = defaultdict(lambda: {})
        self.storage_turn = {}

    def create_server(self, proc):
        while True:
            join_key = human_encode(secrets.token_bytes(5))
            if join_key not in self._servers:
                break

        self._servers[join_key] = proc(join_key)
        return self._servers[join_key]

    def create_token(self, proc):
        while True:
            token = secrets.token_hex(16)
            if token not in self._tokens:
                break

        self._tokens[token] = proc(token)
        return self._tokens[token]

    def delete_token(self, token):
        del self._tokens[token]
        if token in self.storage_stun:
            del self.storage_stun[token]
        if token in self.storage_turn:
            del self.storage_turn[token]

    def disconnect(self, source):
        join_key = getattr(source, "join_key", None)

        if join_key:
            for token in list(self._tokens.values()):
                if token._server == self._servers[join_key]:
                    token.disconnect()
                    del self._tokens[token.token]

            self._servers[join_key].disconnect()
            del self._servers[join_key]

    async def receive_PACKET_COORDINATOR_CLIENT_REGISTER(self, source, protocol_version, game_type, server_port):
        # Reuse the join-key if possible; this means they survive restarts etc.
        if hasattr(source, "join_key"):
            server = self._servers[source.join_key]
        else:
            server = self.create_server(lambda join_key: Server(join_key, self, source, game_type, server_port))
            source.join_key = server.join_key

        await server.detect_connection()

    async def receive_PACKET_COORDINATOR_CLIENT_UPDATE(self, source, protocol_version, join_key, **info):
        if join_key not in self._servers:
            source.protocol.transport.close()

        self._servers[join_key].update(info)

    async def receive_PACKET_COORDINATOR_CLIENT_LISTING(self, source, protocol_version):
        await source.protocol.send_PACKET_COORDINATOR_SERVER_LISTING(self._servers)

    async def receive_PACKET_COORDINATOR_CLIENT_CONNECT(self, source, protocol_version, join_key):
        server = self._servers.get(join_key)
        if server is None:
            await source.protocol.send_PACKET_COORDINATOR_SERVER_ERROR(
                NetworkCoordinatorErrorType.NETWORK_COORDINATOR_ERROR_INVALID_JOIN_KEY, join_key
            )
            source.protocol.transport.close()
            return

        token = self.create_token(lambda token: TokenConnect(token, server, source))
        await source.protocol.send_PACKET_COORDINATOR_SERVER_CONNECTING(f"C{token.token}", join_key)

        await token.connect()

    async def receive_PACKET_COORDINATOR_CLIENT_CONNECT_FAILED(self, source, protocol_version, token, tracking_number):
        prefix = token[0]
        token = self._tokens.get(token[1:])
        if token is None:
            # Don't close connection, as this might just be a delayed failure
            return

        await token.connect_failed(prefix, tracking_number)

    async def receive_PACKET_COORDINATOR_CLIENT_CONNECTED(self, source, protocol_version, token):
        token = self._tokens.get(token[1:])
        if token is None:
            source.protocol.transport.close()
            return

        await token.connected()
        self.delete_token(token.token)

    async def receive_PACKET_COORDINATOR_CLIENT_STUN_RESULT(self, source, protocol_version, token, family, result):
        prefix = token[0]
        token = self._tokens.get(token[1:])
        if token is None:
            source.protocol.transport.close()
            return

        await token.stun_result(prefix, family, result)
