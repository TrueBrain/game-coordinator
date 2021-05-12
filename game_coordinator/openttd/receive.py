import logging

from .protocol.enums import (
    PacketTCPCoordinatorType,
    PacketTCPStunType,
    PacketTCPTurnType,
    ServerGameType,
)
from .protocol.exceptions import (
    PacketInvalidData,
    PacketInvalidSize,
    PacketInvalidType,
)
from .protocol.read import (
    read_bytes,
    read_string,
    read_uint8,
    read_uint16,
    read_uint32,
)

log = logging.getLogger(__name__)


class OpenTTDProtocolStunReceive:
    def receive_data(self, queue, data):
        while len(data) > 2:
            length, _ = read_uint16(data)

            if len(data) < length:
                break

            queue.put_nowait(data[0:length])
            data = data[length:]

        return data

    def receive_packet(self, source, data):
        # Check length of packet
        length, data = read_uint16(data)
        if length != len(data) + 2:
            raise PacketInvalidSize(len(data) + 2, length)

        # Check if type is in range
        type, data = read_uint8(data)
        if type >= PacketTCPStunType.PACKET_STUN_END:
            raise PacketInvalidType(type)

        # Check if we expect this packet
        type = PacketTCPStunType(type)
        func = getattr(self, f"receive_{type.name}", None)
        if func is None:
            raise PacketInvalidType(type)

        # Process this packet
        kwargs = func(source, data)
        return type, kwargs

    @staticmethod
    def receive_PACKET_STUN_CLIENT_STUN(source, data):
        protocol_version, data = read_uint8(data)

        if protocol_version != 1:
            raise PacketInvalidData("unknown protocol version: ", protocol_version)

        token, data = read_string(data)
        interface_number, data = read_uint8(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected; remaining: ", len(data))

        return {"interface_number": interface_number, "token": token}


class OpenTTDProtocolTurnReceive:
    def receive_data(self, queue, data):
        while len(data) > 2:
            length, _ = read_uint16(data)

            if len(data) < length:
                break

            queue.put_nowait(data[0:length])
            data = data[length:]

        return data

    def receive_packet(self, source, data):
        # Check length of packet
        length, data = read_uint16(data)
        if length != len(data) + 2:
            raise PacketInvalidSize(len(data) + 2, length)

        # Check if type is in range
        type, data = read_uint8(data)
        if type >= PacketTCPTurnType.PACKET_TURN_END:
            raise PacketInvalidType(type)

        # Check if we expect this packet
        type = PacketTCPTurnType(type)
        func = getattr(self, f"receive_{type.name}", None)
        if func is None:
            raise PacketInvalidType(type)

        # Process this packet
        kwargs = func(source, data)
        return type, kwargs

    @staticmethod
    def receive_PACKET_TURN_CLIENT_CONNECT(source, data):
        protocol_version, data = read_uint8(data)

        if protocol_version != 1:
            raise PacketInvalidData("unknown protocol version: ", protocol_version)

        token, data = read_string(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected; remaining: ", len(data))

        return {"token": token}


class OpenTTDProtocolCoordinatorReceive:
    def receive_data(self, queue, data):
        while len(data) > 2:
            length, _ = read_uint16(data)

            if len(data) < length:
                break

            queue.put_nowait(data[0:length])
            data = data[length:]

        return data

    def receive_packet(self, source, data):
        # Check length of packet
        length, data = read_uint16(data)
        if length != len(data) + 2:
            raise PacketInvalidSize(len(data) + 2, length)

        # Check if type is in range
        type, data = read_uint8(data)
        if type >= PacketTCPCoordinatorType.PACKET_COORDINATOR_END:
            raise PacketInvalidType(type)

        # Check if we expect this packet
        type = PacketTCPCoordinatorType(type)
        func = getattr(self, f"receive_{type.name}", None)
        if func is None:
            raise PacketInvalidType(type)

        # Process this packet
        kwargs = func(source, data)
        return type, kwargs

    @staticmethod
    def receive_PACKET_COORDINATOR_CLIENT_REGISTER(source, data):
        protocol_version, data = read_uint8(data)

        if protocol_version != 1:
            raise PacketInvalidData("unknown protocol version: ", protocol_version)

        game_type, data = read_uint8(data)

        if game_type >= ServerGameType.SERVER_GAME_TYPE_END:
            raise PacketInvalidData("invalid ServerGameType", game_type)

        game_type = ServerGameType(game_type)

        server_port, data = read_uint16(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected; remaining: ", len(data))

        return {"protocol_version": protocol_version, "game_type": game_type, "server_port": server_port}

    @staticmethod
    def receive_PACKET_COORDINATOR_CLIENT_UPDATE(source, data):
        protocol_version, data = read_uint8(data)

        if protocol_version != 1:
            raise PacketInvalidData("unknown protocol version: ", protocol_version)

        game_info_version, data = read_uint8(data)

        if game_info_version != 5:
            raise PacketInvalidData("unknown game info version: ", game_info_version)

        join_key, data = read_string(data)

        if getattr(source, "join_key", None) != join_key:
            raise PacketInvalidData("join_key doesn't match registration: ", getattr(source, "join_key"), join_key)

        newgrf_mode, data = read_uint8(data)
        if newgrf_mode == 0:
            newgrfs = None
        else:
            newgrf_count, data = read_uint8(data)

            newgrfs = []
            for i in range(newgrf_count):
                newgrf_id, data = read_uint32(data)
                md5sum, data = read_bytes(data, 16)

                # Servers shouldn't be sending this, but we accept and ignore it.
                # This is just to be protocol compatible.
                if newgrf_mode == 2:
                    _, data = read_string(data)

                newgrfs.append((newgrf_id, md5sum))

        game_date, data = read_uint32(data)
        start_date, data = read_uint32(data)

        companies_max, data = read_uint8(data)
        companies_on, data = read_uint8(data)
        spectators_max, data = read_uint8(data)

        name, data = read_string(data)
        openttd_version, data = read_string(data)
        use_password, data = read_uint8(data)

        clients_max, data = read_uint8(data)
        clients_on, data = read_uint8(data)
        spectators_on, data = read_uint8(data)

        map_width, data = read_uint16(data)
        map_height, data = read_uint16(data)
        map_type, data = read_uint8(data)

        is_dedicated, data = read_uint8(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected; remaining: ", len(data))

        return {
            "protocol_version": protocol_version,
            "join_key": join_key,
            "newgrfs": newgrfs,
            "game_date": game_date,
            "start_date": start_date,
            "companies_max": companies_max,
            "companies_on": companies_on,
            "clients_max": clients_max,
            "clients_on": clients_on,
            "spectators_max": spectators_max,
            "spectators_on": spectators_on,
            "name": name,
            "openttd_version": openttd_version,
            "use_password": use_password,
            "is_dedicated": is_dedicated,
            "map_width": map_width,
            "map_height": map_height,
            "map_type": map_type,
        }

    @staticmethod
    def receive_PACKET_COORDINATOR_CLIENT_LISTING(source, data):
        protocol_version, data = read_uint8(data)

        if protocol_version != 1:
            raise PacketInvalidData("unknown protocol version: ", len(protocol_version))

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected; remaining: ", len(data))

        return {"protocol_version": protocol_version}

    @staticmethod
    def receive_PACKET_COORDINATOR_CLIENT_CONNECT(source, data):
        protocol_version, data = read_uint8(data)

        if protocol_version != 1:
            raise PacketInvalidData("unknown protocol version: ", len(protocol_version))

        join_key, data = read_string(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected; remaining: ", len(data))

        return {"protocol_version": protocol_version, "join_key": join_key}

    @staticmethod
    def receive_PACKET_COORDINATOR_CLIENT_CONNECT_FAILED(source, data):
        protocol_version, data = read_uint8(data)

        if protocol_version != 1:
            raise PacketInvalidData("unknown protocol version: ", len(protocol_version))

        token, data = read_string(data)
        tracking_number, data = read_uint8(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected; remaining: ", len(data))

        return {"protocol_version": protocol_version, "token": token, "tracking_number": tracking_number}

    @staticmethod
    def receive_PACKET_COORDINATOR_CLIENT_CONNECTED(source, data):
        protocol_version, data = read_uint8(data)

        if protocol_version != 1:
            raise PacketInvalidData("unknown protocol version: ", len(protocol_version))

        token, data = read_string(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected2; remaining: ", len(data))

        return {"protocol_version": protocol_version, "token": token}

    @staticmethod
    def receive_PACKET_COORDINATOR_CLIENT_STUN_RESULT(source, data):
        protocol_version, data = read_uint8(data)

        if protocol_version != 1:
            raise PacketInvalidData("unknown protocol version: ", len(protocol_version))

        token, data = read_string(data)
        family, data = read_uint8(data)
        result, data = read_uint8(data)

        if len(data) != 0:
            raise PacketInvalidData("more bytes than expected2; remaining: ", len(data))

        return {"protocol_version": protocol_version, "token": token, "family": family, "result": result}
