FROM python:3.8

RUN useradd -m -U app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /home/app
USER app

COPY authorlist ./authorlist/
COPY server.py ./
COPY output.json ./

ENV PYTHONPATH=/home/app
ENV PORT 8080
ENV JSON output.json

CMD [ "python", "./server.py", "-n" ]
