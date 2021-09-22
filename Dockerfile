FROM gcr.io/google.com/cloudsdktool/cloud-sdk:latest

COPY import_common.py /usr/bin
ENTRYPOINT ["/usr/bin/import_common.py"]
