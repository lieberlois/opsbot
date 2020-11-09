import logging

from flask import Flask, request

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)


@app.route("/v3/conversations/<gk>/activities", methods=['POST'])
def conversations(gk):
    print(f"Opsbot: {request.json['text']}")
    return {}, 200


if __name__ == "__main__":
    app.run('0.0.0.0', 1234)
