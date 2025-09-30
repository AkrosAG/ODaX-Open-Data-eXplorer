
FROM mageai/mageai:0.9.76
ARG PIP=pip3


RUN echo 'deb http://deb.debian.org/debian bullseye main' > /etc/apt/sources.list.d/bullseye.list

RUN apt-get update -y && \
    apt-get install -y \
    openjdk-17-jdk \
    curl \
    libfreetype6-dev \
    libpng-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

RUN rm /etc/apt/sources.list.d/bullseye.list

RUN ${PIP} install pyspark==3.5.6


# Install system dependencies for matplotlib
# RUN apt-get install -y \
#     libgl1-mesa-glx \
#     libglib2.0-0 \
#     libsm6 \
#     libxext6 \
#     libxrender-dev \
#     libgomp1 \
#     libgthread-2.0-0 \
#     libgtk-3-0 \
#     libavcodec-dev \
#     libavformat-dev \
#     libswscale-dev \
#     libv4l-dev \
#     libxvidcore-dev \
#     libx264-dev \
#     libjpeg-dev \
#     libpng-dev \
#     libtiff-dev \
#     libatlas-base-dev \
#     gfortran \
#     && rm -rf /var/lib/apt/lists/*



COPY requirements.txt /tmp/requirements.txt
RUN ${PIP} install --no-cache-dir -r /tmp/requirements.txt

# Add scala kernel via spylon-kernel
# RUN python3 -m spylon_kernel install

# Set matplotlib backend to Agg for non-interactive environments
# ENV MPLBACKEND=Agg

# Create directory for plots
# RUN mkdir -p /home/src/plots

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV SPARK_HOME=/opt/spark
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3
# ENV PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH


# Set working directory to Mage AI's expected location
WORKDIR /home/src
# RUN mkdir -p /opt/spark/conf
# COPY spark-defaults.conf /opt/spark/conf
# ENV PATH="/opt/spark/sbin:/opt/spark/bin:${PATH}"


# ENV SPARK_VERSION=3.5.6
# ENV SPARK_MAJOR_VERSION=3.5
# ENV ICEBERG_VERSION=1.9.0

# # Download spark
# RUN mkdir -p ${SPARK_HOME} \
#  && curl https://dlcdn.apache.org/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz -o spark-${SPARK_VERSION}-bin-hadoop3.tgz \
#  && tar xvzf spark-${SPARK_VERSION}-bin-hadoop3.tgz --directory /opt/spark --strip-components 1 \
#  && rm -rf spark-${SPARK_VERSION}-bin-hadoop3.tgz

# # Download iceberg spark runtime
# RUN curl -s https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-${SPARK_MAJOR_VERSION}_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-${SPARK_MAJOR_VERSION}_2.12-${ICEBERG_VERSION}.jar -Lo /opt/spark/jars/iceberg-spark-runtime-${SPARK_MAJOR_VERSION}_2.12-${ICEBERG_VERSION}.jar

# RUN curl -s https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-extensions-${SPARK_MAJOR_VERSION}_2.12/${ICEBERG_VERSION}/iceberg-spark-extensions-${SPARK_MAJOR_VERSION}_2.12-${ICEBERG_VERSION}.jar -Lo /opt/spark/jars/iceberg-spark-extensions-${SPARK_MAJOR_VERSION}_2.12-${ICEBERG_VERSION}.jar

# RUN curl -s https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-nessie/${ICEBERG_VERSION}/iceberg-nessie-${ICEBERG_VERSION}.jar -Lo /opt/spark/jars/iceberg-nessie-${ICEBERG_VERSION}.jar

# # Download AWS bundle
# RUN curl -s https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar -Lo /opt/spark/jars/iceberg-aws-bundle-${ICEBERG_VERSION}.jar


# # Default command
# CMD ["mage", "start", "default_repo", "--project-type", "standalone"]

ENV MAGE_DATA_DIR=