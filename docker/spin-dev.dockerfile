FROM registry.contact.de/spin-base
COPY setup-system.sh .
RUN sh -x setup-system.sh
