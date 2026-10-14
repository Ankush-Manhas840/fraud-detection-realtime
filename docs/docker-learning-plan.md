# Docker learning plan

Goal: interview-ready Docker, learned through real projects rather than a separate course.

## What interview-ready means

**Explain in simple words**

1. What a container is, and how it differs from a virtual machine
2. Image compared with container (a recipe compared with the cooked dish)
3. Why use Docker at all ("it works on my machine" problems)
4. What a Dockerfile is, and what `FROM`, `COPY`, `RUN` and `CMD` do
5. Volumes (keeping data) and ports (reaching the app from outside)
6. What Docker Compose is for (running several containers together)
7. How Docker was used in this project

**Be able to do**

1. Write a Dockerfile for a Python API
2. Build an image and run it
3. Use Docker Compose to run the API, Kafka and Redis together
4. Push an image to AWS and run it there

## When each part is learned

| When | What | Level |
|---|---|---|
| Fraud project, streaming week | Run Kafka and Redis with `docker compose up` | Basics |
| Fraud project, after the API works | Dockerfile for the FastAPI app, added to Compose | Most of interview level |
| November, AWS | Push the image to AWS (ECR) and run it in the cloud | Interview level |
| December, RAG project | Do it again on a new project | Confident |

## Checklist

- [ ] Explain container, image, and container compared with virtual machine
- [ ] Run Kafka and Redis with `docker compose up -d`, read logs, stop them
- [ ] Fix a "port already in use" error
- [ ] Write a Dockerfile for the FastAPI app
- [ ] Build and run the API image locally
- [ ] Add the API to `docker-compose.yml`
- [ ] Push the image to AWS ECR
- [ ] Run the container on AWS
- [ ] Answer all 7 "explain" questions out loud without notes

## Free resources (documentation first)

- Docker "Get started": https://docs.docker.com/get-started/ (parts 1 to 3 for basics, the rest for interview level)
- Writing a Dockerfile: https://docs.docker.com/build/concepts/dockerfile/
- Docker Compose: https://docs.docker.com/compose/
- FastAPI's Docker guide: https://fastapi.tiangolo.com/deployment/docker/
