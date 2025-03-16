# Dockerfile, Image, Container
# FROM python:3.7

# WORKDIR /humanity_app

# COPY requirements.txt ./requirements.txt

# RUN pip install -r requirements.txt

# EXPOSE 8888

# COPY . /app

# CMD streamlit run --server.port 8888 --server.enableCORS false app.py

FROM python:3.7

EXPOSE 8888

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD streamlit run --server.port 8888 app.py