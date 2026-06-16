FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages 2>/dev/null || \
    pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY handler.py .

CMD ["handler.handler"]
