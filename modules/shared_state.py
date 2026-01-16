# modules/shared_state.py

class Context:
    def __init__(self):
        self.AI_NAME = "Marbis"

        self.MIC_ON = False

        self.CURRENT_STATUS = "Idle"


state = Context()