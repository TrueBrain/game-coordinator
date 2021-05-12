import asyncio
import click
import logging

from openttd_helpers import click_helper
from openttd_helpers.logging_helper import click_logging
from openttd_helpers.sentry_helper import click_sentry

from .application.coordinator import Application as CoordinatorApplication
from .application.stun import Application as StunApplication
from .application.turn import Application as TurnApplication
from .openttd import (
    tcp_coordinator,
    tcp_stun,
    tcp_turn,
)
from .openttd.tcp_coordinator import click_coordinator_proxy_protocol
from .openttd.tcp_stun import click_stun_proxy_protocol

log = logging.getLogger(__name__)


async def run_server(application, bind, port, ProtocolClass):
    loop = asyncio.get_event_loop()

    server = await loop.create_server(
        lambda: ProtocolClass(application),
        host=bind,
        port=port,
        reuse_port=True,
        start_serving=True,
    )
    log.info(f"Listening on {bind}:{port} ...")

    return server


@click_helper.command()
@click_logging  # Should always be on top, as it initializes the logging
@click_sentry
@click.option(
    "--bind", help="The IP to bind the server to", multiple=True, default=["::1", "127.0.0.1"], show_default=True
)
@click.option("--coordinator-port", help="Port of the Game Coordinator", default=3976, show_default=True)
@click.option("--stun-port", help="Port of the STUN server", default=3975, show_default=True)
@click.option("--turn-port", help="Port of the TURN server", default=3974, show_default=True)
@click_coordinator_proxy_protocol
@click_stun_proxy_protocol
def main(bind, coordinator_port, stun_port, turn_port):
    app_instance = CoordinatorApplication()
    stun_instance = StunApplication(app_instance)
    turn_instance = TurnApplication(app_instance)

    loop = asyncio.get_event_loop()
    server = loop.run_until_complete(
        run_server(app_instance, bind, coordinator_port, tcp_coordinator.OpenTTDProtocolTCPCoordinator)
    )
    stun_server = loop.run_until_complete(run_server(stun_instance, bind, stun_port, tcp_stun.OpenTTDProtocolTCPStun))
    turn_server = loop.run_until_complete(run_server(turn_instance, bind, turn_port, tcp_turn.OpenTTDProtocolTCPTurn))

    try:
        loop.run_until_complete(server.serve_forever())
    except KeyboardInterrupt:
        pass

    log.info("Shutting down game_coordinator ...")
    turn_server.close()
    stun_server.close()
    server.close()


if __name__ == "__main__":
    main(auto_envvar_prefix="GAME_COORDINATOR")
