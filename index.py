import sys
import packet_handler
from bw_logging import get_logger

from minecraft import authentication
from minecraft.exceptions import YggdrasilError
from minecraft.networking.connection import Connection
from minecraft.networking.packets import Packet, clientbound, serverbound
import minecraft.networking.packets.clientbound.play as packets

from config import SERVER_IP, MINECRAFT_USERNAME, MINECRAFT_PASSWORD

auth_token = authentication.AuthenticationToken()


def authenticate(username, password):
    logger = get_logger("authenticator")
    logger.debug("Attempting to authenticate")
    try:
        auth_token.authenticate(username, password)
    except YggdrasilError as e:
        logger.fatal("Error authenticating", e)
        exit(2)
    logger.debug("Successful authentication as {}.".format(auth_token.profile.name))


def main():
    authenticate(MINECRAFT_USERNAME, MINECRAFT_PASSWORD)
    connection = Connection(SERVER_IP, 25565, auth_token=auth_token)

    connection.register_packet_listener(packet_handler.handle_join_game, packets.JoinGamePacket)
    connection.register_packet_listener(lambda chat_packet: packet_handler.handle_chat(chat_packet, connection), packets.ChatMessagePacket)
    connection.register_packet_listener(packet_handler.handle_player_list, packets.PlayerListItemPacket)

    connection.connect()

    while True:
        try:
            text = input()
            packet = serverbound.play.ChatPacket()
            packet.message = text
            connection.write_packet(packet)
        except KeyboardInterrupt:
            print("Bye!")
            sys.exit()


main()
