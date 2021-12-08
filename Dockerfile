FROM python:3

ENV VIRTUAL_ENV=/opt/bot-env
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install -U discord.py
RUN pip install -U python-dotenv

RUN mkdir -p /usr/src/bot
WORKDIR /usr/src/bot

COPY . .

CMD [ "python3", "pixray_bot.py" ]
