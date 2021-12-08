# pixray-bot

The official Discord bot for the pixray API (in beta). Based on [pixray](https://github.com/dribnet/pixray) by Tom White.

## Requirements
- Docker

## Install (Linux-only)
1. Update and upgrade.
`sudo apt-get update && sudo apt-get upgrade`

2. Install Docker
`curl -sSL https://get.docker.com | sh`

3. Add a non-root user (the current user) to the Docker group
`sudo usermod -aG docker ${USER}`

Check it by running `groups ${USER}` then reboot.

4. Build docker container
`cd ~/pixray-bot && docker build -t pixray-bot .`

5. Run the docker container
`docker run -d pixray-bot`
`-d` flag runs the container in detached mode (in the background).
Check running docker process `docker ps`.

You can stop the docker container running the bot with `docker stop <CONTAINER ID>` and you can restart it with `docker restart <CONTAINER ID>`.

Please look at the Docker docs for more information.

