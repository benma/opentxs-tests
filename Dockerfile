FROM opentxs-notary:latest

MAINTAINER Filip Gospodinov "filip@monetas.net"

ENV TEST_DIR /home/otuser/opentxs-test
RUN mkdir $TEST_DIR
ADD ot-clean-data $TEST_DIR/ot-clean-data
ADD test-data $TEST_DIR/test-data
ADD python3 $TEST_DIR/python3
RUN find $TEST_DIR/python3 | grep "\.pyc$" | xargs rm
WORKDIR $TEST_DIR/python3
ENV PYTHONPATH /usr/local/lib/x86_64-linux-gnu/python3.4/site-packages/:$TEST_DIR/python3
ENV DOCKER=1
RUN chown -R otuser:otuser /home/otuser/
USER otuser
RUN ./runtests.py
CMD ["bash"]
