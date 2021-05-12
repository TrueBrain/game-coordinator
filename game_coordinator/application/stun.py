import logging

log = logging.getLogger(__name__)


class Application:
    def __init__(self, coordinator):
        super().__init__()

        self._coordinator = coordinator

    async def receive_PACKET_STUN_CLIENT_STUN(self, source, interface_number, token):
        self._coordinator.storage_stun[token][interface_number] = (source.ip, source.port)

        # TODO -- Start a timeout to close the connection
