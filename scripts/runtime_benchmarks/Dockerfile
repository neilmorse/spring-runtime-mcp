ARG JDK
ARG PYTHON
FROM ${JDK} AS java
FROM ${PYTHON}
COPY --from=java /opt/java/openjdk /opt/java/openjdk
ENV PATH="/opt/java/openjdk/bin:${PATH}"
COPY requirements.txt /tmp/benchmark-requirements.txt
RUN pip install --no-cache-dir --no-deps --require-hashes -r /tmp/benchmark-requirements.txt \
    && rm /tmp/benchmark-requirements.txt \
    && java -version
