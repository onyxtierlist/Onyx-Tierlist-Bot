import json
import datetime
from src.utils.loadConfig import branding, listKits

def _load(name):
    with open(f"config/{name}", "r", encoding="utf-8") as file:
        return json.load(file)

resultmessage = _load("resultmessage.json")
noqueuemessage = _load("noqueue.json")
enterwaitlistmessage = _load("enterwaitlist.json")
queuemessage = _load("queue.json")
ticketmessage = _load("ticket.json")
highticketmessage = _load("highticket.json")
infomessage = _load("info.json")

def _brand(data):
    data = json.loads(json.dumps(data))
    data["color"] = branding["color"]
    footer = data.setdefault("footer", {})
    footer["text"] = branding["footer"]
    return data

def formatresult(discordUsername, testerID, region, kit, minecraftUsername, oldTier, newTier, uuid):
    data = _brand(resultmessage)
    text = json.dumps(data)
    replacements = {
        "{{PLAYER}}": discordUsername, "{{TESTER}}": f"<@{testerID}>",
        "{{REGION}}": region, "{{KIT}}": listKits[kit].get("label", kit.title()),
        "{{USERNAME}}": minecraftUsername, "{{PREV_TIER}}": oldTier,
        "{{NEW_TIER}}": newTier, "{{THUMBNAIL_URL}}": f"https://render.crafty.gg/3d/bust/{uuid}"
    }
    for old, new in replacements.items():
        text = text.replace(old, str(new))
    return json.loads(text)

def formatnoqueue(kit=None):
    data = _brand(noqueuemessage)
    kit_label = listKits[kit].get("label", kit.title()) if kit else ""
    if kit:
        data["title"] = f"{branding['name']} • {kit_label}"
        data["description"] = f"No tester is currently available for **{kit_label}**."
    return data

def formatqueue(capacity, queue, testerCapacity, testers, kit):
    data = _brand(queuemessage)
    kit_label = listKits[kit].get("label", kit.title())
    data["title"] = f"{branding['name']} • {kit_label}"
    for field in data.get("fields", []):
        field["name"] = field["name"].replace("{{CAPACITY}}", capacity).replace("{{TESTERCAPACITY}}", testerCapacity)
        field["value"] = field["value"].replace("{{QUEUE}}", queue).replace("{{TESTERS}}", testers)
    if data.get("description"):
        data["description"] = data["description"].replace("{{KIT}}", kit_label).replace("{{REGION}}", "")
    return data

def formatticketmessage(username, tier, server, kit, uuid):
    data = _brand(ticketmessage)
    text = json.dumps(data).replace("{{SERVER}}", server).replace("{{USERNAME}}", username)
    text = text.replace("{{TIER}}", tier).replace("{{KIT}}", listKits[kit].get("label", kit.title()))
    text = text.replace("{{THUMBNAIL_URL}}", f"https://render.crafty.gg/3d/bust/{uuid}")
    return json.loads(text)

def formathighticketmessage(username, tier, kit, uuid):
    data = _brand(highticketmessage)
    text = json.dumps(data).replace("{{USERNAME}}", username).replace("{{TIER}}", tier)
    text = text.replace("{{KIT}}", listKits[kit].get("label", kit.title()))
    text = text.replace("{{THUMBNAIL_URL}}", f"https://render.crafty.gg/3d/bust/{uuid}")
    return json.loads(text)

def formatinfo(discordName, username, tier, lastTest, region, kit, restricted, uuid):
    data = _brand(infomessage)
    text = json.dumps(data).replace("{{USERNAME}}", username).replace("{{TIER}}", tier)
    text = text.replace("{{REGION}}", region).replace("{{KIT}}", listKits[kit].get("label", kit.title()))
    text = text.replace("{{DISCORDUSER}}", discordName)
    text = text.replace("{{RESTRICTED}}", "true" if restricted == 1 else "false")
    text = text.replace("{{LAST}}", "Not tested before" if lastTest == 0 else f"<t:{lastTest}:f>")
    text = text.replace("{{THUMBNAIL_URL}}", f"https://render.crafty.gg/3d/bust/{uuid}")
    return json.loads(text)
