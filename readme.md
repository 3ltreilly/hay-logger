# Simple website to track hay usage, still wip

## Install with Docker

Writing this down so I don't forget again

* Do you developing where ever you want
* Push updates to github
* Use github actions to build the new docker image and push it to the docker hub
* Docker on diskstation can then pull it down from docker hub to use
* Required files
  * `.github/workflows/docker-image.yml` for github actions
  * `.dockerignore` docker ignore files
  * `Dockerfile` use for setting up and running docker locally?
  * `wip.sh` handy commands and what to run on diskstation
