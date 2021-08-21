FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000/tcp
EXPOSE 8000/udp
CMD [ "python", "-m", "pytest", "-s", "-v", "-m", "bug" ]