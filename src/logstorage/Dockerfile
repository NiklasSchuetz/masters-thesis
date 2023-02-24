FROM python:3.10-slim-buster

WORKDIR /app

# Currently no external libraries used: no need to install anything
# COPY requirements.txt requirements.txt

RUN pip3 install pandas

COPY . .

EXPOSE 50000
ENV PYTHONUNBUFFERED=1


CMD ["python", "./server.py"]