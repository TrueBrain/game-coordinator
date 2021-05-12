from .protocol.enums import (
    PacketTCPCoordinatorType,
    PacketTCPTurnType,
    ServerGameType,
)
from .protocol.write import (
    write_init,
    write_bytes,
    write_string,
    write_uint8,
    write_uint16,
    write_uint32,
    write_presend,
)


class OpenTTDProtocolTurnSend:
    async def send_PACKET_TURN_SERVER_CONNECTED(self, host, port):
        data = write_init(PacketTCPTurnType.PACKET_TURN_SERVER_CONNECTED)

        data = write_string(data, host)
        data = write_uint16(data, port)

        data = write_presend(data)
        await self.send_packet(data)


class OpenTTDProtocolCoordinatorSend:
    async def send_PACKET_COORDINATOR_SERVER_ERROR(self, error_no, error_detail):
        data = write_init(PacketTCPCoordinatorType.PACKET_COORDINATOR_SERVER_ERROR)

        data = write_uint8(data, error_no.value)
        data = write_string(data, error_detail)

        data = write_presend(data)
        await self.send_packet(data)

    async def send_PACKET_COORDINATOR_SERVER_REGISTER_ACK(self, join_key, connection_type):
        data = write_init(PacketTCPCoordinatorType.PACKET_COORDINATOR_SERVER_REGISTER_ACK)

        data = write_string(data, join_key)
        data = write_uint8(data, connection_type.value)

        data = write_presend(data)
        await self.send_packet(data)

    async def send_PACKET_COORDINATOR_SERVER_LISTING(self, servers):
        for join_key, server in servers.items():
            if server.game_type != ServerGameType.SERVER_GAME_TYPE_PUBLIC:
                continue
            if len(server.info) == 0:
                continue

            data = write_init(PacketTCPCoordinatorType.PACKET_COORDINATOR_SERVER_LISTING)

            data = write_uint16(data, 1)

            data = write_uint8(data, 5)  # Game Info version
            data = write_string(data, join_key)
            data = write_uint8(data, 1)  # has-newgrf-data

            data = write_uint8(data, len(server.info["newgrfs"]))
            for newgrf in server.info["newgrfs"]:
                data = write_uint32(data, newgrf[0])
                data = write_bytes(data, newgrf[1])

            data = write_uint32(data, server.info["game_date"])
            data = write_uint32(data, server.info["start_date"])

            data = write_uint8(data, server.info["companies_max"])
            data = write_uint8(data, server.info["companies_on"])
            data = write_uint8(data, server.info["spectators_max"])

            data = write_string(data, server.info["name"])
            data = write_string(data, server.info["openttd_version"])
            data = write_uint8(data, server.info["use_password"])
            data = write_uint8(data, server.info["clients_max"])
            data = write_uint8(data, server.info["clients_on"])
            data = write_uint8(data, server.info["spectators_on"])

            data = write_uint16(data, server.info["map_width"])
            data = write_uint16(data, server.info["map_height"])
            data = write_uint8(data, server.info["map_type"])

            data = write_uint8(data, server.info["is_dedicated"])

            data = write_presend(data)
            await self.send_packet(data)

        # Send a final packet with 0 servers to indicate end-of-list.
        data = write_init(PacketTCPCoordinatorType.PACKET_COORDINATOR_SERVER_LISTING)
        data = write_uint16(data, 0)
        data = write_presend(data)
        await self.send_packet(data)

    async def send_PACKET_COORDINATOR_SERVER_CONNECTING(self, token, join_key):
        data = write_init(PacketTCPCoordinatorType.PACKET_COORDINATOR_SERVER_CONNECTING)

        data = write_string(data, token)
        data = write_string(data, join_key)

        data = write_presend(data)
        await self.send_packet(data)

    async def send_PACKET_COORDINATOR_SERVER_CONNECT_FAILED(self, token):
        data = write_init(PacketTCPCoordinatorType.PACKET_COORDINATOR_SERVER_CONNECT_FAILED)

        data = write_string(data, token)

        data = write_presend(data)
        await self.send_packet(data)

    async def send_PACKET_COORDINATOR_SERVER_DIRECT_CONNECT(self, token, tracking_number, server_host, server_port):
        data = write_init(PacketTCPCoordinatorType.PACKET_COORDINATOR_SERVER_DIRECT_CONNECT)

        data = write_string(data, token)
        data = write_uint8(data, tracking_number)
        data = write_string(data, server_host)
        data = write_uint16(data, server_port)

        data = write_presend(data)
        await self.send_packet(data)

    async def send_PACKET_COORDINATOR_SERVER_STUN_REQUEST(self, token):
        data = write_init(PacketTCPCoordinatorType.PACKET_COORDINATOR_SERVER_STUN_REQUEST)

        data = write_string(data, token)

        data = write_presend(data)
        await self.send_packet(data)

    async def send_PACKET_COORDINATOR_SERVER_STUN_CONNECT(self, token, tracking_number, interface_number, host, port):
        data = write_init(PacketTCPCoordinatorType.PACKET_COORDINATOR_SERVER_STUN_CONNECT)

        data = write_string(data, token)
        data = write_uint8(data, tracking_number)
        data = write_uint8(data, interface_number)
        data = write_string(data, host)
        data = write_uint16(data, port)

        data = write_presend(data)
        await self.send_packet(data)

    async def send_PACKET_COORDINATOR_SERVER_TURN_CONNECT(self, token, tracking_number, host, port):
        data = write_init(PacketTCPCoordinatorType.PACKET_COORDINATOR_SERVER_TURN_CONNECT)

        data = write_string(data, token)
        data = write_uint8(data, tracking_number)
        data = write_string(data, host)
        data = write_uint16(data, port)

        data = write_presend(data)
        await self.send_packet(data)
