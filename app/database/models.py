import uuid
from enum import Enum

from tortoise import fields
from tortoise.fields.relational import ReverseRelation
from tortoise.models import Model


class Account(Model):
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=255, null=True)
    name = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    @property
    def created_at_ts(self):
        return int(self.created_at.timestamp())

    def __repr__(self):
        return f"<Accounts(account_id={self.id}, username='{self.username}')>"

    class Meta:
        table = "accounts"


class AccountCompanyRelation(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    company_id = fields.UUIDField()
    account = fields.ForeignKeyField("models.Account", related_name="account_relations")

    def __repr__(self):
        return f"""<AccountCompanyRelations(account={self.account.id}, 
        company={self.company_id})>"""

    class Meta:
        table = "account_company_relations"


class Chat(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    @property
    def created_at_ts(self):
        return int(self.created_at.timestamp())

    def __repr__(self):
        return f"<Chats(chat_id={self.id}, Chat_name='{self.name}')>"

    class Meta:
        table = "chats"


class Bot(Model):
    id = fields.BigIntField(pk=True)
    bot_token = fields.CharField(max_length=255)
    secret_token = fields.CharField(max_length=255)
    bot_username = fields.CharField(max_length=255)
    bot_first_name = fields.CharField(max_length=255)
    company_id = fields.UUIDField()
    is_active = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    comment = fields.TextField(null=True)

    @property
    def created_at_ts(self):
        return int(self.created_at.timestamp())

    def __repr__(self):
        return f"""<Bots(bot_id={self.id}, name='{self.bot_username}',
          active={self.is_active})>"""

    class Meta:
        table = "bots"


class BotChatRelation(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    bot = fields.ForeignKeyField("models.Bot", related_name="bot_relations", on_delete=fields.CASCADE)
    chat = fields.ForeignKeyField("models.Chat", related_name="bot_relations", on_delete=fields.CASCADE)
    is_admin = fields.BooleanField(default=False)

    def __repr__(self):
        return f"<BotChatRelations(bot={self.bot.id}, chat={self.chat.id})>"

    class Meta:
        table = "bot_chat_relations"


class Message(Model):
    id = fields.CharField(pk=True, max_length=255)
    timestamp = fields.DatetimeField(auto_now_add=True)
    account = fields.ForeignKeyField("models.Account", related_name="messages")

    chat = fields.ForeignKeyField("models.Chat", related_name="messages")
    text = fields.TextField(null=True)
    s3_key = fields.CharField(max_length=255, null=True)

    @property
    def created_at_ts(self):
        return int(self.timestamp.timestamp())

    def __repr__(self):
        return f"""<Messages(message_id={self.id}, 
        chat={self.chat.id}, account={self.account.id})>"""

    class Meta:
        table = "messages"


class ScheduleStrategy(str, Enum):
    ANALYSIS = "analysis"
    NOTIFICATION = "notification"


class ScheduleType(str, Enum):
    INTERVAL = "interval"
    CRON = "cron"


class SendStrategy(str, Enum):
    FIXED = "fixed"
    RELATIVE = "relative"


class ChatSchedule(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    name = fields.CharField(max_length=255, null=True)
    schedule_strategy = fields.CharEnumField(ScheduleStrategy)

    chat = fields.ForeignKeyField("models.Chat", related_name="schedules", null=True)
    prompt = fields.ForeignKeyField("models.Prompt", related_name="schedules", null=True)

    schedule_type = fields.CharEnumField(ScheduleType)

    # Стратегия: анализ
    # --- Тип: interval ---
    interval_hours = fields.IntField(null=True)
    interval_minutes = fields.IntField(null=True)

    # --- Тип: cron ---
    cron_expression = fields.CharField(max_length=100, null=True)  # '0 5 * * *'

    # Стратегия: напоминание
    notification_text = fields.TextField(null=True)

    # Общие поля:
    enabled = fields.BooleanField(default=True)
    last_run_at = fields.DatetimeField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    send_strategy = fields.CharEnumField(SendStrategy, default="fixed", null=True)
    send_after_minutes = fields.IntField(null=True)
    time_to_send = fields.TimeField(null=True)
    company_id = fields.UUIDField()

    bot = fields.ForeignKeyField("models.Bot", related_name="schedules")

    message_intro = fields.CharField(max_length=255, null=True)

    description = fields.TextField(null=True)

    target_chats: ReverseRelation["TargetChat"]
    run_on_empty_chat = fields.BooleanField(default=False)

    @property
    def created_at_ts(self):
        return int(self.created_at.timestamp())

    def __repr__(self):
        return f"""<ChatSchedules(schedule_id={self.id}, 
         type='{self.schedule_type}')>"""

    class Meta:
        table = "chat_schedules"


class TargetChat(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    schedule = fields.ForeignKeyField("models.ChatSchedule", related_name="target_chats")
    chat = fields.ForeignKeyField("models.Chat", related_name="target_chats")

    def __repr__(self):
        return f"""<TargetChats(target_chat_id={self.id}, 
        chat={self.chat.id})>"""

    class Meta:
        table = "target_chats"


class AnalysingModelTypes(str, Enum):
    YA_GPT_MINI = "yandex-gpt-mini"
    YA_GPT_PRO = "yandex-gpt-pro"


class AnalysisResult(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)

    prompt = fields.ForeignKeyField("models.Prompt", related_name="analysis")
    result_text = fields.TextField()
    chat = fields.ForeignKeyField("models.Chat", related_name="analysis_results")
    schedule = fields.ForeignKeyField("models.ChatSchedule", related_name="analysis_results", null=True)
    company_id = fields.UUIDField()
    created_at = fields.DatetimeField(auto_now_add=True)

    # Разворачиваем фильтры:
    date_from = fields.DatetimeField()
    date_to = fields.DatetimeField()

    tokens_input = fields.IntField()
    tokens_output = fields.IntField()

    analysing_model = fields.CharEnumField(AnalysingModelTypes, null=True)

    send_time = fields.BigIntField(null=True)

    @property
    def created_at_ts(self):
        return int(self.created_at.timestamp())

    def __repr__(self):
        return f"""<AnalysisResult(analysis_id={self.id},
          prompt={self.prompt.id})>"""

    class Meta:
        table = "analysis_results"


class Prompt(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    name = fields.CharField(max_length=255)
    text = fields.TextField()
    company_id = fields.UUIDField()
    created_at = fields.DatetimeField(auto_now_add=True)

    @property
    def created_at_ts(self):
        return int(self.created_at.timestamp())

    def __repr__(self):
        return f"<Prompts(prompt_id={self.id}, prompt_name='{self.name}')>"

    class Meta:
        table = "prompts"


class UserAgreement(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    user_id = fields.UUIDField()
    date = fields.DatetimeField(auto_now_add=True)
    user_ip = fields.CharField(max_length=15)

    class Meta:
        table = "user_agreements"
