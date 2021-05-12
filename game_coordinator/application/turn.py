import logging
import time

from collections import defaultdict

from .helpers.ip import ip_to_str

log = logging.getLogger(__name__)


class Application:
    def __init__(self, coordinator):
        super().__init__()

        self._coordinator = coordinator
        self._relays = defaultdict(lambda: {})
        self._started = {}

    def disconnect(self, source):
        if not hasattr(source, "token"):
            return

        # Also close the other side.
        if source.protocol.relay_peer:
            if source.protocol.relay_peer.protocol.relay_peer is None:
                if source.token[0] == "C":
                    client = source
                    server = source.protocol.relay_peer
                else:
                    client = source.protocol.relay_peer
                    server = source

                delta = time.time() - self._started[source.token[1:]]

                log.info(f"Stopped relay for {client.ip} <-> {server.ip} after {delta} seconds")
                log.info(
                    f"  Transfer from client: {client.protocol.relay_bytes} bytes, {client.protocol.relay_bytes / delta} bytes/sec"
                )
                log.info(
                    f"  Transfer from server: {server.protocol.relay_bytes} bytes, {server.protocol.relay_bytes / delta} bytes/sec"
                )

            source.protocol.relay_peer.protocol.transport.close()
            source.protocol.relay_peer = None

    async def receive_PACKET_TURN_CLIENT_CONNECT(self, source, token):
        prefix = token[0]
        token = token[1:]
        self._relays[token][prefix] = source

        # TODO -- Validate tokens

        if "C" in self._relays[token] and "S" in self._relays[token]:
            client = self._relays[token]["C"]
            server = self._relays[token]["S"]

            client.token = f"C{token}"
            server.token = f"S{token}"

            server.protocol.relay_peer = client
            client.protocol.relay_peer = server

            await server.protocol.send_PACKET_TURN_SERVER_CONNECTED(ip_to_str(client.ip), client.port)
            await client.protocol.send_PACKET_TURN_SERVER_CONNECTED(ip_to_str(server.ip), server.port)

            self._started[token] = time.time()

            log.info(f"Started relay for {client.ip} <-> {server.ip}")

        # TODO -- Start a timeout to close idle connections
