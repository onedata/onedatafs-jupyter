FROM ubuntu:bionic-20190612
MAINTAINER Bartek Kryza <bkryza@gmail.com>

# Build arguments
ARG RELEASE_TYPE
ARG RELEASE="1802"
ARG DISTRIBUTION="bionic"
ARG ONECLIENT_VERSION=""
ARG FSONEDATAFS_VERSION=""
ARG ONEDATAFS_JUPYTER_VERSION=""
ARG HTTP_PROXY

# Enable Onedata devel package proxy cache
ENV http_proxy ${HTTP_PROXY}

# Get the image up to date and install utility tools
RUN apt-get -y update && \
    apt-get -y install bash-completion ca-certificates curl iputils-ping netcat \
                       man-db net-tools traceroute vim python-xattr parallel \
                       python-pip python3-pip && \
    apt-get clean

# Install fs.onedatafs dependencies
RUN pip install fs six setuptools
RUN pip3 install fs six setuptools
RUN pip install jupyter Pillow scipy pandas matplotlib
RUN pip3 install jupyter Pillow scipy pandas matplotlib

WORKDIR /tmp

# Install oneclient package
RUN case ${RELEASE_TYPE} in \
        production) \
            curl -O http://packages.onedata.org/oneclient-${RELEASE}.sh; \
            ;; \
        *) \
            curl -O http://packages.devel.onedata.org/oneclient-${RELEASE}.sh; \
            ;; \
        esac && \
        sh oneclient-${RELEASE}.sh python-onedatafs=${ONECLIENT_VERSION}-1~${DISTRIBUTION} && \
        apt-get -y install python3-onedatafs=${ONECLIENT_VERSION}-1~${DISTRIBUTION} \
                           python-fs-plugin-onedatafs=${FSONEDATAFS_VERSION}-1~${DISTRIBUTION} \
                           python3-fs-plugin-onedatafs=${FSONEDATAFS_VERSION}-1~${DISTRIBUTION} \
                           python-onedatafs-jupyter=${ONEDATAFS_JUPYTER_VERSION}-1~${DISTRIBUTION} \
                           python3-onedatafs-jupyter=${ONEDATAFS_JUPYTER_VERSION}-1~${DISTRIBUTION} \
                           sysbench

ADD jupyter_notebook_config.py /root/.jupyter/jupyter_notebook_config.py

EXPOSE 8888

RUN mkdir /notebooks

WORKDIR /notebooks

# Disable http_proxy for normal operation
ENV http_proxy ""

CMD ["jupyter", "notebook", "--port=8888", "--no-browser", "--allow-root", "--ip=0.0.0.0"]
