# Opsbot

The Opsbot started as a small Microsoft Teams bot, whose sole purpose was to select a random pitiable team member to be responsible for operation and defects on that day.
Later on some more features were added like checking alertmanager or creating Jira subtasks.

Since this bot might be useful also for other teams we decided to refactor the bot to make it modular and to be configurable.

The repo also contains deployment templates to make the start easy.
If you work with kubernetes, have a look at the included helm template and the helmfile.
You only need to add some configurations, and you are ready to start.

At the moment most of the texts the bot sends out are still in German.

## Installation

To use the OpsBot you need to configure a new Bot in Microsoft Teams and have the backend service deployed somewhere publicly reachable.
The Bot in Teams has to be configured with the public URL of the backend service.

After you have installed both the Bot in MS Teams, and the backend Service you need to initialize the Opsbot.
This will set the Channel you issued the init command in as the default channel for the Opsbot:

    @Opsbot init
    
You can then ask the Opsbot for a complete list of all possible commands:

    @Opsbot help

### Teams Bot

To configure a bot in Microsoft Teams you use the Teams app "App Studio".
There you can create the configuration (A json manifest file) for the Bot and install it into your teams channel.
In `deploy/ms_teams` you find an example of such a manifest file. You can import and modify the provided one or create your own.
In both cases you will need to create a new Bot id and password in App Studio and set those in your Backend configuration.  
 
### Backend

The backend service is provided as a dockerfile which is available at [Dockerhub](https://hub.docker.com/r/maibornwolff/opsbot). 
You can use this one or build your own from this repository. In any case you have to deploy the service somewhere publicly available.

#### Kubernetes

For kubernetes deployment a helm template is included in the project under `deploy/helm/opsbot`
 and hosted as helm repository `https://maibornwolff.github.io/opsbot/` via github pages.

You can install this chart with

    $ helm repo add maibornwolff-opsbot https://MaibornWolff.github.io/opsbot
    $ helm install my-release maibornwolff-opsbot/opsbot --values my-values.yaml

To further simplify the deployment even more there is also a predefined helmfile (deploy/helmfile/helmfile.yaml) available.
You can configure the deployment of the backend service and also provide the Opsbot configuration in one file.
It is also possible to add custom plugins which will get deployed in a configmap and added to the Opsbot container.

## Configuration

The Bot is configured with a Yaml file. The path Opsbot looks for this file defaults to `./opsbot_config.yaml` but can be overwritten by setting the environment variable `OPSBOT_CONFIG_FILE`.

You can also set any of the configuration values via environment variables.
E.g. if you do not want to set the Bot password parameter `teams.app_password` in the config file, just use the environment variable `TEAMS_APP_PASSWORD` instead.

Most functionality of the Opsbot are provided by different plugins. Some plugins are contained in the OpsBot core but you can also add your own plugins. (See custom plugins below).

These plugins are currently included in OpsBot:

| Plugin | Description |
|---|---|
| Operations  |  Team member can be registered with this plugin. Every day the plugin chooses an operations responsible for the day and announces him or her in the Chat. |
| Sayings | A plugin that reacts to unknown commands with an insult. | 
| Jira | This plugin can check Jira for Defect tickets and it can create subtasks for an existing ticket. | 
| Alerts | Checks an alertmanager for active alerts. | 

This is an overview of all possible configuration parameters:

```yaml

timezone: "Europe/Berlin" # The current time zone

deactivate_plugins: # A list of plugins that should be deactivated

additional_plugin_dir: # Directory with additional plugins

teams:
  app_id: # The Bot App ID
  app_password: # the Bot password

persistence: # The persistence plugin to use. Currently available: file | configmap
  plugin: file
  path: persistence.yaml
  --------
  # plugin: configmap
  # configmap_name: 
  # configmap_namespace: 

actions: # Configuration for the different plugins

  operations:
    override_user: # A username that can override the normal daily queue
    how_to_link: # An optional link to a description of the operator
    quotes: # A list of quotes the operator for the day gets
      - "Remember, the force will be with you, always."
      - "Do. Or do not. There is no try."

  sayings:
    insults: # A list of insults the opsbot uses as response for unknown commands
      - "That is why you fail."
      - "...why?"

  jira:
    base_url: 
    username:
    password: 
    defects:
      filter_id: # The filter id
      link_defects: # Link to defect filter
    subtasks:
      project_id: # The project id 
      issue_type: # Jira internal number of the Issue type that should be created

  alerts:
    base_url: 
```

### Commands

Below you find a list of all commands, the Opsbot understands.
All commands are issued by mentioning the Opsbot either in a channel or via direct message. (@Opsbot \<command\>)

##### Global commands:

| Command | Description |
|---------|-------------|
| init | Initialize the Opsbot. The default channel will be set to the one the command was issued in |
| register channel XX | Configure the current channel for messages of type XX |
| unregister channel XX | Remove the channel assignment for type XX |
| help | Print out the help |

##### Operations plugin:

| Command | Description |
|---------|-------------|
| register @user | Add an user to the operations responsible rotation |
| unregister @user | Remove a user from the rotation |
| next <br/> weiter [@user] | Move to the next person in the rotation or the mentioned one |
| heute <br/> today <br/> wer | Prints out who is the responsible today |
| morgen <br/> tomorrow | Prints out who is the responsible tomorrow |
| 'Urlaub am dd.mm.yyyy' [@user] <br/> 'Urlaub von dd.mm.yyyy bis dd.mm.yyyy' [@user] <br/> 'Urlaub dd.mm.yyyy - dd.mm.yyyy' [@user] | Add your vacation or those of another mentioned person |

##### Jira plugin:

| Command | Description |
|---------|-------------|
| gen subtasks XXX-XXXX | Reads tasks from the Jira ticket XXX-XXXX and generates subtasks for each |
| show tasks XXX-XXXX | List tasks from the Jira ticket XXX-XXXX |
| fix XXX-XXXX | Solves the issue XXX-XXXX |
| defects | Lists current defects |


### Channels

Opsbot supports multiple Channels. The default is always the one the `init` command was issued in.
You can then tell Opsbot to send certain types of messages to another channel by sending this command:
    
    @Opsbot channel register defects

The channel type 'defects' that is used for this example is configured in the [Jira plugin](opsbot/plugins/actions/jira.py) when it sends out scheduled messages.
If there is no channel set for a type, the default one is used. There is also a deregister command to remove the association:

    @Opsbot defects deregister channel

#### Available channels
| Plugin | Channel type |
|---|---|
| Jira  |  defects |
| Alerts | alerts | 


## Local development

For local development Opsbot can be started on your machine. To start you need Python >= 3.7 and virtualenv installed.
You then need to initialize the `venv` dir with the `init_venv.sh` script.

Then you only need to create the `opsbot_config.yaml` file, and you can run Opsbot by `run_local.sh`.

### CLI

To simplify the local development of the bot there is also a small CLI tool with which you can talk to the bot while it is running on your local machine.

The CLI sends messages to the Opsbot at `localhost:5000`. In these messages the URL the Bot is going to reply to is set to `localhost:1234`. 
To receive those the CLI tool spins up a simple Flask server that listens on that port and echoes the responses of Opsbot.

The CLI can be started with `./run_cli.sh` and understands the following commands:

* start: Start of restart the flask server
* stop: Stop the flask server
* send "<message>": Send a message to opsbot
* quit/exit: Exit the CLI

## Custom plugins 

Opsbot can be extended with new features by adding custom plugins. A custom plugin must extend the abstract `ActionPlugin` or `PersistencePlugin` class and implement their required methods.
In the configuration `additional_plugin_dir` then needs to be set to the directory containing the custom plugin.

Example:

```python
from opsbot.plugins.actions import ActionPlugin

class MyCustomActionPlugin(ActionPlugin):

    def __init__(self, opsbot):
        super().__init__(opsbot)
        self.add_scheduled_job(self._scheduled, 'cron', id='some_id', day_of_week='mon-fri', hour=8, minute=0)

    def init_hooks(self):
        self.register_messagehook_regex(r"((MyCommand)|(mycommand))", self._response)

    def _response(self, activity, mentions):
        self.send_reply(f"Send response to the thread the command was issued.", activity)

    def _scheduled(self, activity, mentions):
        self.send_message(f"Send message to a channel. Either a named channel or the default one", channel_type='myChannelType')
```
