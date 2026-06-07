FROM python:3.11-slim

RUN pip install --no-cache-dir fava beancount-periodic

EXPOSE 5000

CMD ["fava", "--host", "0.0.0.0", "/bean/main.bean"]
