# docker build . --tag custom-mininet

FROM iwaseyusuke/mininet
RUN apt-get update && apt-get install -y python-pip
RUN pip install networkx
