#!/bin/sh
# Update milhouse to the latest hay-logger image on Docker Hub (the steps in wip.sh).
# Run it after a PR merges to main and its GitHub Actions run has pushed the image.
# Stops without touching anything if Docker Hub has no new image.
set -e

ssh -t 3ltreilly@milhouse.local '
set -e
# Synology installs docker here; a non-interactive ssh session may not have it on PATH
export PATH="/usr/local/bin:$PATH"

pull_output=$(docker pull 3ltreilly/hay-logger)
echo "$pull_output"
case "$pull_output" in
    *"Image is up to date"*)
        echo "No new image on Docker Hub, so nothing changed. Has the Actions run on main finished?"
        exit 1
        ;;
esac

docker stop hay-logger
docker rm hay-logger
docker run -d --network host \
    --restart unless-stopped \
    --env-file /volume1/docker/hay-logger/hay-logger.env \
    -v /volume1/docker/hay-logger/db:/app/db \
    --name hay-logger 3ltreilly/hay-logger

# look for "Listening at: http://0.0.0.0:8000"
sleep 5
docker logs --tail 20 hay-logger
'
