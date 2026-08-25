from src.utils import format
from src.utils.loadConfig import messages

class TierlistQueue:
    """In-memory queues keyed by kit."""

    def __init__(self, maxQueue: int, maxTesters: int, cooldown: int):
        self.queue = {}
        self.maxQueue = maxQueue
        self.maxTesters = maxTesters
        self.cooldown = cooldown

    @staticmethod
    def key(kit: str) -> str:
        return kit

    def setup(self, kits: dict) -> None:
        self.queue.clear()
        for kit_name, kit_data in kits.items():
            key = self.key(kit_name)
            self.queue[key] = {
                    "kit": kit_name,
                    "queueChannel": kit_data["queue_channel"],
                    "queueMessage": None,
                    "open": False,
                    "testers": [],
                    "queue": []
            }

    def openqueue(self, queue_key: str, open: bool):
        self.queue[queue_key]["open"] = open
        if not open:
            self.queue[queue_key]["queue"] = []
            self.queue[queue_key]["testers"] = []

    def find_by_message(self, messageID: int):
        for key, data in self.queue.items():
            if data["queueMessage"] == messageID:
                return key
        return None

    def addUser(self, messageID: int, userID: int):
        queue_key = self.find_by_message(messageID)
        if queue_key is None:
            return "queue doesnt exist"

        data = self.queue[queue_key]
        if userID in data["queue"]:
            return messages["alreadyInQueue"]
        if len(data["queue"]) >= self.maxQueue:
            return messages["queueFull"]

        data["queue"].append(userID)
        return messages["addToQueue"]

    def removeUser(self, messageID: int, userID: int):
        queue_key = self.find_by_message(messageID)
        if queue_key is None:
            return "queue doesnt exist"

        data = self.queue[queue_key]
        if userID not in data["queue"]:
            return messages["notInQueue"]

        data["queue"].remove(userID)
        return messages["leaveQueue"]

    def addTester(self, kit: str, userID: int):
        queue_key = self.key(kit)
        data = self.queue[queue_key]

        if data["testers"] == []:
            self.openqueue(queue_key, True)

        if userID in data["testers"]:
            return ("You are already testing this queue!", "")

        if len(data["testers"]) < self.maxTesters:
            data["testers"].append(userID)
            return (
                f'{messages["testerOpenQueue"]}: <#{data["queueChannel"]}>',
                self.makeQueueMessage(queue_key)
            )

        return ("The tester limit for this queue has been reached.", "")

    def removeTester(self, kit: str, userID: int):
        queue_key = self.key(kit)
        data = self.queue[queue_key]

        if not data["open"]:
            return "Testing is closed"

        if userID in data["testers"]:
            data["testers"].remove(userID)
            if data["testers"] == []:
                self.openqueue(queue_key, False)
                return (
                    "testing has closed",
                    format.formatnoqueue(kit),
                    data["queueChannel"],
                    data["queueMessage"]
                )

            return (
                "you have stopped testing",
                self.makeQueueMessage(queue_key),
                data["queueChannel"],
                data["queueMessage"]
            )

        return (
            "you are not testing this queue",
            self.makeQueueMessage(queue_key),
            data["queueChannel"],
            data["queueMessage"]
        )

    def getNextTest(self, testerID: int, kit: str):
        queue_key = self.key(kit)
        data = self.queue[queue_key]
        if not data["queue"]:
            return (None, f"No users are in the {kit} queue")

        return (data["queue"].pop(0), None)

    def makeQueueMessage(self, queue_key: str):
        data = self.queue[queue_key]
        capacity = f'{len(data["queue"])}/{self.maxQueue}'
        testerCapacity = f'{len(data["testers"])}/{self.maxTesters}'
        queue = "\n".join(
            f"{i + 1}. <@{user_id}>" for i, user_id in enumerate(data["queue"])
        ) or "No players are currently waiting."
        testers = "\n".join(
            f"{i + 1}. <@{user_id}>" for i, user_id in enumerate(data["testers"])
        ) or "No testers are currently testing."

        return format.formatqueue(
            capacity=capacity,
            queue=queue,
            testerCapacity=testerCapacity,
            testers=testers,
            kit=data["kit"]
        )

    def addQueueMessageId(self, queue_key: str, messageID: int):
        self.queue[queue_key]["queueMessage"] = messageID

    def getqueueraw(self):
        return self.queue
