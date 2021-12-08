FROM python:3

ENV VIRTUAL_ENV=/opt/bot-env
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN mkdir -p /usr/src/bot

COPY requirements.txt /usr/src/bot/requirements.txt

WORKDIR /usr/src/bot

RUN pip install -r requirements.txt

COPY . .

CMD [ "python3", "-u", "pixray_bot.py" ]
