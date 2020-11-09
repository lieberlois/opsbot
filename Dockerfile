FROM python:3.7-slim

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
COPY opsbot /opsbot

EXPOSE 5000

CMD ["python" , "-m", "opsbot.main"]
