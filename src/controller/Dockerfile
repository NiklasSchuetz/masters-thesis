FROM python:3.10-slim-buster

WORKDIR /app

# Currently no external libraries used: no need to install anything
# COPY requirements.txt requirements.txt


COPY . .

EXPOSE 50000
ENV PYTHONUNBUFFERED=1

# CMD ["python", "./control.py"] to run the control script when applying pod to cluster

# to just sleep: so you can kubectl ini files into and then start using kubectl exec
CMD ["sleep", "infinity"] 