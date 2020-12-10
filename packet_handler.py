import json
import threading

import minecraft.networking.packets.clientbound.play as packets
from bw_logging import get_logger
from minecraft.networking.packets import serverbound
from stats import check_stats

# Using default python logger.
logger = get_logger("packet_handler")

join_game_logger = logger.getChild("handle_join_game")


def handle_join_game(join_packet):
    join_game_logger.debug("Connected to server")


chat_logger = logger.getChild("handle_chat")


# handle_chat handles AFK and logs all other chat messages.
def handle_chat(chat_packet: packets.ChatMessagePacket, connection):
    loaded = {}
    try:
        loaded = json.loads(chat_packet.json_data)
    except AttributeError:
        return

    # we get empty chat packets sometimes when Hypixel just wants to display an empty line.
    if not loaded:
        return

    # Handle AFK
    if loaded["text"] == "You are AFK. Move around to return from AFK.":
        send_chat_message("/l bedwars", connection)
        chat_logger.info("Marked as AFK, rejoining Bedwars lobby...")
        return

    if "extra" not in loaded or len(loaded["extra"]) < 1:
        return

    # This very complex if statement looks for chat messages and prints them.
    # It ignores all other types of messages including lobby join messages (which are very similar).
    extras = loaded["extra"]
    is_chat_message = len(extras) > 1 and "hoverEvent" not in extras[-1] and "clickEvent" in extras[-2] and \
                      extras[-2]["clickEvent"]["value"].startswith("/viewprofile ") and "joined the lobby" not in \
                      extras[-2]["text"]

    if is_chat_message:
        sanitized_chat_message = loaded["extra"][-1]["text"].removeprefix(": ")
        chat_logger.debug(
            "Message ({}): {}".format(chat_packet.field_string("position"), sanitized_chat_message))
    return


player_list_logger = logger.getChild("handle_player_list")
# hypixel repeats the join packet multiple times one after another, this makes sure we get one of each
previous_player_uuid = ""


# handle_player_list handles when players "join" the game.
# This is where we detect new players in the lobby.
def handle_player_list(packet: packets.PlayerListItemPacket):
    global previous_player_uuid
    for action in packet.actions:
        # ensure that a new player has joined (not a ping change or something, those are the same packet)
        if not isinstance(action, packets.PlayerListItemPacket.AddPlayerAction):
            return

        if action.uuid == previous_player_uuid:
            return
        else:
            previous_player_uuid = action.uuid
            player_list_logger.debug("{} ({}) just joined the lobby.".format(action.name, action.uuid))

            # If we don't thread this, we'll get a broken pipe error as it will block
            # pyCraft's networking thread and it won't be able to send packets.
            t = threading.Thread(target=check_stats, args=(action.uuid,))
            t.start()


send_chat_message_logger = get_logger("send_chat_message")


# Used for AFK
def send_chat_message(message, connection):
    send_chat_message_logger.debug("Sending chat message: {}".format(message))
    packet = serverbound.play.ChatPacket()
    packet.message = message
    connection.write_packet(packet)
