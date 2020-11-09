# coding=utf-8
import asyncio
import logging
import re
import traceback

from botbuilder.schema import Activity, ActivityTypes, ChannelAccount, Mention, ConversationAccount
from botframework.connector import ConnectorClient
from botframework.connector.auth import MicrosoftAppCredentials, JwtTokenValidation, SimpleCredentialProvider
from flask import Flask, request

from .config import get_config_value
from .plugins.plugin_loader import PluginLoader

logger = logging.getLogger()


class TeamsBot(object):
    def __init__(self, name):
        self.name = name
        self._messagehook_unknown = None
        self._messagehooks = list()
        self._app_id = get_config_value('teams.app_id', fail_if_missing=True)
        self._app_password = get_config_value('teams.app_password', fail_if_missing=True)
        self.plugins = PluginLoader(self)
        self._config = self.plugins.persistence().read_state()
        bot_config = self._config.get("bot_config", dict())
        self._service_url = bot_config.get("service_url")
        self._conversations = bot_config.get("conversations", dict())
        self._current_channel = bot_config.get("current_channel")
        self._current_bot_id = bot_config.get("current_bot_id")
        self._channel_data = bot_config.get("channel_data")
        self._user_map = bot_config.get("user_map", dict())
        self._conversation_channels = bot_config.get("conversation_channels", dict())
        self._init_routes()

    def _init_routes(self):
        self._flask_app = Flask(__name__)
        self._flask_app.add_url_rule('/api/message', "message", self.message_received, methods=['POST'])
        self._flask_app.add_url_rule('/health', "health", self.health, methods=['GET'])
        self._flask_app.add_url_rule('/', "index", self.index_page, methods=['GET'])

    def _register_conversation(self, conversation, conversation_type):
        self._conversations[conversation_type] = conversation.__dict__["id"].split(";")[0]

    def send_reply(self, text, reply_to, mentions=None):
        self.__send(text, reply_to.conversation, mentions)

    def send_message(self, text, channel_type, mentions=None):
        if channel_type in self._conversation_channels:
            channel_id = self._conversation_channels[channel_type]
        else:
            channel_id = self._channel_data['channel']['id']
        conversation = ConversationAccount(is_group=True, id=channel_id, conversation_type="channel")
        self.__send(text, conversation, mentions)

    def __send(self, text, conversation, mentions=None):
        logger.info(f"Sending message: {text}")
        entities = list()
        if mentions is None:
            mentions = list()
        for name in mentions:
            user_id = self._user_map.get(name)
            if not user_id:
                logger.info("User not found: %s" % name)
                continue
            mention = Mention(mentioned=ChannelAccount(id=user_id, name=name), text="<at>%s</at>" % name,
                              type="mention")
            entities.append(mention)

        credentials = MicrosoftAppCredentials(self._app_id, self._app_password)
        connector = ConnectorClient(credentials, base_url=self._service_url)

        reply = Activity(
            type=ActivityTypes.message,
            channel_id=self._current_channel,
            conversation=conversation,
            from_property=ChannelAccount(id=self._current_bot_id["id"], name=self._current_bot_id["name"]),
            entities=entities,
            text=text,
            service_url=self._service_url)

        response = connector.conversations.send_to_conversation(reply.conversation.id, reply)
        logger.info(response)

    def message_received(self):
        """ handles incoming messages """
        logger.info(f"Received message: \n {request.get_json()}")
        activity = Activity.deserialize(request.get_json())
        authorization = request.headers.get("Authorization")

        # if not self._handle_authentication(authorization, activity):
        #    logger.info("Authorization failed. Not processing request")
        #    return ""
        self._service_url = activity.service_url
        try:
            if activity.type == ActivityTypes.message.value:
                self._update_user_map(activity)
                mentions = self._extract_mentions(activity)
                message_text = activity.text
                matched = False
                for match_type, matcher, func in self._messagehooks:
                    if match_type == "REGEX":
                        if matcher.findall(message_text.lower()):
                            func(activity, mentions)
                            matched = True
                            break
                    elif match_type == "FUNC":
                        if matcher(message_text):
                            func(activity, mentions)
                            matched = True
                            break
                if not matched and self._messagehook_unknown:
                    self._messagehook_unknown(activity, mentions)
            self._save_system_config()
        except Exception as e:
            traceback.print_exc()
            try:
                self.send_reply("Es ist ein Fehler aufgetreten: %s" % e, reply_to=activity)
            except:
                traceback.print_exc()
        return ""

    def _handle_authentication(self, authorization, activity):
        credential_provider = SimpleCredentialProvider(self._app_id, self._app_password)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(JwtTokenValidation.assert_valid_activity(
                activity, authorization, credential_provider))
            return True
        except Exception as ex:
            logger.info(ex)
            return False
        finally:
            loop.close()

    def _update_bot_infos(self, activity):
        self._current_channel = activity.channel_id
        self._current_bot_id = activity.recipient.__dict__
        self._channel_data = activity.channel_data

    def _extract_mentions(self, activity):
        mentions = list()
        for entitiy in activity.entities:
            if entitiy.type == "mention":
                mentioned = entitiy.__dict__["additional_properties"]["mentioned"]
                user_id = mentioned["id"]
                name = mentioned["name"]
                if name.lower() == self.name.lower():
                    continue
                mentions.append(name)
        return mentions

    def _update_user_map(self, activity):
        for mention in activity.entities:
            if mention.type == "mention":
                mentioned = mention.__dict__["additional_properties"]["mentioned"]
                user_id = mentioned["id"]
                name = mentioned["name"]
                self._user_map[name] = user_id
        mentioned = activity.from_property.__dict__
        user_id = mentioned["id"]
        name = mentioned["name"]
        self._user_map[name] = user_id

    def register_messagehook_regex(self, regex, message_func):
        regex_matcher = re.compile(regex)
        self._messagehooks.append(("REGEX", regex_matcher, message_func))

    def register_messagehook_func(self, matcher_func, message_func):
        self._messagehooks.append(("FUNC", matcher_func, message_func))

    def register_messagehook_unknown(self, message_func):
        self._messagehook_unknown = message_func

    def messagehook_regex(self, regex):
        def decorator(message_func):
            self.register_messagehook_regex(regex, message_func)
            return message_func

        return decorator

    def messagehook_func(self, matcher_func):
        def decorator(message_func):
            self.register_messagehook_func(matcher_func, message_func)
            return message_func

        return decorator

    def messagehook_unknown(self, func=None):
        def decorator(message_func):
            self.register_messagehook_unknown(message_func)
            return message_func

        if func:
            return decorator(func)
        else:
            return decorator

    def _save_system_config(self):
        bot_config = dict()
        bot_config["service_url"] = self._service_url
        bot_config["conversations"] = self._conversations
        bot_config["current_channel"] = self._current_channel
        bot_config["current_bot_id"] = self._current_bot_id
        bot_config["channel_data"] = self._channel_data
        bot_config["user_map"] = self._user_map
        bot_config["conversation_channels"] = self._conversation_channels
        self._config["bot_config"] = bot_config
        self.plugins.persistence().persist_state(self._config)

    def health(self):
        return "OK"

    def index_page(self):
        return "This is Opsbot"

    def get_app(self):
        return self._flask_app

    def run(self, port=5000, debug=False):
        self._flask_app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
