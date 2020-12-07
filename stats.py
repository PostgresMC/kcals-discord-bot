import requests
import math

from bw_logging import get_logger
from config import HYPIXEL_API_KEY

logger = get_logger("stats")
xp_per_prestige = 487000
required_bw_keys = ["Experience", "final_kills_bedwars", "final_deaths_bedwars", "beds_broken_bedwars", "beds_lost_bedwars"]


def calculate_bedwars_stars(exp):
    prestiges = math.floor(exp / xp_per_prestige)
    remainder = exp % xp_per_prestige

    num_stars = prestiges * 100

    # this unfortunate system is due to the way the first 5 levels work.

    if remainder >= 500:
        remainder -= 500
        num_stars += 1

    if remainder >= 1000:
        remainder -= 1000
        num_stars += 1

    if remainder >= 2000:
        remainder -= 2000
        num_stars += 1

    if remainder >= 3500:
        remainder -= 3500
        num_stars += 1

    if remainder >= 5000:
        num_stars = num_stars + math.floor(remainder / 5000)

    return num_stars


check_stats_logger = logger.getChild("check_stats")


def check_stats(uuid):
    check_stats_logger.debug("Checking stats for {}".format(uuid))
    # first, validate uuid by checking mojang
    # we do this because hypixel inserts fake players to make npcs
    mojang_profile_req = requests.get("https://sessionserver.mojang.com/session/minecraft/profile/{}".format(uuid))
    if mojang_profile_req.status_code != 200:
        check_stats_logger.error("Invalid username or mojang error (status {}). Don't worry, probably a NPC.".format(mojang_profile_req.status_code))
        return
    else:
        check_stats_logger.debug("Mojang check successful for {}".format(uuid))

    check_stats_logger.debug("Getting hypixel stats for {}".format(uuid))
    hypixel_req = requests.get("https://api.hypixel.net/player?key={}&uuid={}".format(HYPIXEL_API_KEY, uuid))

    if hypixel_req.status_code != 200:
        if hypixel_req.status_code == 429:
            check_stats_logger.error("Hypixel rate limited, please wait...")
        else:
            check_stats_logger.error("Error getting hypixel stats for {} (status code {})".format(uuid, hypixel_req.status_code))
        return

    check_stats_logger.debug("Got hypixel stats for {}".format(uuid))
    player_data = hypixel_req.json()
    bedwars_stats = player_data["player"]["stats"]["Bedwars"]

    for k in required_bw_keys:
        if k not in bedwars_stats:
            bedwars_stats[k] = 1

    stats = {
        "username": player_data["player"]["displayname"],
        "stars": calculate_bedwars_stars(bedwars_stats["Experience"]),
        "final_kdr": bedwars_stats["final_kills_bedwars"] / bedwars_stats["final_deaths_bedwars"],
        "wlr": bedwars_stats["beds_broken_bedwars"] / bedwars_stats["beds_lost_bedwars"]
    }

    check_stats_logger.info("Stats for {}: {}".format(player_data["player"]["displayname"], stats))
