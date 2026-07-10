FROM apify/actor-python:3.12

COPY requirements.txt ./
RUN echo "Python: $(python --version)" \
 && pip install -U pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

COPY . ./

CMD ["python3", "-m", "src"]
