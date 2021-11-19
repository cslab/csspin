FROM registry.contact.de/spin
COPY setup-system.sh .
RUN sh -x setup-system.sh
