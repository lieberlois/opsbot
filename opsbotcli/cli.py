import subprocess

import click
import requests
from click_shell import shell


def get_message(message):
    return {
        "attachments": [
            {
                "content": "<div><div><span itemscope=\"\" itemtype=\"http://schema.skype.com/Mention\" itemid=\"0\">OpsBot</span>&nbsp;guten abend herr&nbsp;opsbot</div>\\n</div>",
                "contentType": "text/html"
            }
        ],
        "channelData": {
            "channel": {
                "id": "19:7f139b7a485e46a6b32f1053ab863fcf@thread.skype"
            },
            "team": {
                "id": "19:7f139b7a485e46a6b32f1053ab863fcf@thread.skype"
            },
            "teamsChannelId": "19:7f139b7a485e46a6b32f1053ab863fcf@thread.skype",
            "teamsTeamId": "19:7f139b7a485e46a6b32f1053ab863fcf@thread.skype",
            "tenant": {
                "id": "7eb9feac-5602-4a4c-918a-7e7cb4f26040"
            }
        },
        "channelId": "msteams",
        "conversation": {
            "conversationType": "channel",
            "id": "19:7f139b7a485e46a6b32f1053ab863fcf@thread.skype;messageid=1583942402382",
            "isGroup": True,
            "tenantId": "db4b360f-e32f-4ada-aaac-4d44bddfb5f8"
        },
        "entities": [
            {
                "mentioned": {
                    "id": "28:42c4b01f-8d4c-4852-b823-6fa4272f2d64",
                    "name": "OpsBot"
                },
                "text": "<at>OpsBot</at>",
                "type": "mention"
            },
            {
                "country": "DE",
                "locale": "de-DE",
                "platform": "Mac",
                "type": "clientInfo"
            }
        ],
        "from": {
            "aadObjectId": "4aac1b15-9c77-477b-a36a-3b6c6987123c",
            "id": "29:14bGwtoLMTb7E0VrhSC7JXCDEAo-Juwdz0RiaAfPRqz75Yv9pJCr5_FQt6w4cV5em728coBVjNuOVkvX9Ut9TA",
            "name": "Some User"
        },
        "id": "1583960742386",
        "localTimestamp": "2020-03-11T22:00:42.5811168+01:00",
        "locale": "de-DE",
        "recipient": {
            "id": "28:42c4b01f-8d4c-4852-b823-6fa4222f2d64",
            "name": "OpsBot"
        },
        "serviceUrl": "http://localhost:1234",
        "text": f"<at>OpsBot</at> {message}\\n",
        "textFormat": "plain",
        "timestamp": "2020-03-11T21:00:42.5811168Z",
        "type": "message"
    }


def _start_server():
    global p
    click.echo("start server")
    p = subprocess.Popen(['venv/bin/python', 'opsbotcli/server.py'])


def _stop_server(_=None):
    global p
    if p:
        p.terminate()
        p = None
        click.echo("server stopped")


@shell(prompt='opsbot-cli > ', intro='Starting opsbot cli...', on_finished=_stop_server)
def opsbot_cli():
    pass


@opsbot_cli.command()
@click.argument('message', required=True)
def send(message):
    r = requests.post("http://localhost:5000/api/message", json=get_message(message))
    if r.status_code > 204:
        print(f"Request error: {r.status_code}: {r.reason}")


@opsbot_cli.command()
def start():
    _stop_server()
    _start_server()


@opsbot_cli.command()
def stop():
    _stop_server()


def main():
    _start_server()
    opsbot_cli()


if __name__ == '__main__':
    main()
