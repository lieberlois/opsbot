FROM python:3.7-slim

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
COPY opsbot /opsbot
RUN adduser --no-create-home --uid 1000 opsbot && chown -R opsbot /opsbot
USER 1000
EXPOSE 5000
CMD ["python" , "-m", "opsbot.main"]
