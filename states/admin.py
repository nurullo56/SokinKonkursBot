from aiogram.fsm.state import State, StatesGroup


class SetupWizard(StatesGroup):
    waiting_group_id = State()
    waiting_channel_id = State()


class AddPublicFlow(StatesGroup):
    waiting_channel_id = State()
    waiting_limit = State()


class AddZayafkaFlow(StatesGroup):
    waiting_channel_id = State()
    waiting_invite_link = State()
    waiting_limit = State()


class DelPublicFlow(StatesGroup):
    waiting_channel_id = State()


class DelZayafkaFlow(StatesGroup):
    waiting_channel_id = State()


class BroadcastFlow(StatesGroup):
    waiting_message = State()
    confirm_send = State()


class ResultsFlow(StatesGroup):
    waiting_count = State()
    waiting_reply_link = State()
    confirm = State()
