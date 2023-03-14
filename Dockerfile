FROM python:3.6

WORKDIR /app

COPY . /app

RUN pip install gunicorn
RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["gunicorn", "--timeout", "120", "-w", "1", "-b", ":5000", "app:app"]