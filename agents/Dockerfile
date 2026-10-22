FROM python:3.12-slim

WORKDIR /app
COPY floodsense_agents ./floodsense_agents

EXPOSE 8100
CMD ["python", "-m", "floodsense_agents"]
