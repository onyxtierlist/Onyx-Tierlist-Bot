import yaml
import logging
import sys

try:
    with open("config/config.yml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
except Exception:
    logging.exception("Failed to load configuration file:")
    sys.exit("Error: Unable to load config file.")

try:
    botConfig = config["bot"]
    catagories = botConfig["catagories"]

    listTiers = list(botConfig["tiers"].keys())
    listTiers.append("none")
    # Discord shows clean uppercase tier labels while keeping lowercase values internally.
    listTierChoices = {tier.upper(): tier for tier in listTiers}
    listHighTiers = botConfig["highTiers"]

    listRegions = botConfig["regions"]
    listRegionsText = list(listRegions.keys())

    listKits = botConfig["kits"]
    listKitsText = list(listKits.keys())

    listRegionCategories = [region["ticket_catagory"] for region in listRegions.values()]
    listRegionCategories.append(catagories["highTests"])
    listRegionCategories.extend(
        kit["ticket_category"]
        for kit in listKits.values()
        if kit.get("ticket_category")
    )
    listKitQueueChannel = [kit["queue_channel"] for kit in listKits.values()]
    listRegionRolePing = [region["role_ping"] for region in listRegions.values()]

    testerRole = botConfig["roles"]["tester"]
    listTierRoles = dict(botConfig["tiers"])
    listKitTierRoles = {
        kit: dict(kit_data.get("tier_roles") or listTierRoles)
        for kit, kit_data in listKits.items()
    }
    messages = botConfig["messages"]
    channels = botConfig["channels"]

    maxQueue = botConfig["options"]["queueLimit"]
    maxTester = botConfig["options"]["testerLimit"]
    cooldown = botConfig["options"]["cooldown"]
    reloadQueue = botConfig["options"]["reloadQueue"]

    branding = botConfig["branding"]

    mysqlInfo = config["database"]["mysql"]
    databaseType = config["database"]["type"]
except Exception:
    logging.exception("Setting up config failed:")
    sys.exit("Error: Failed to setup config")
