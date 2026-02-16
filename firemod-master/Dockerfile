FROM gcc:12 AS builder

WORKDIR /farsite

COPY src/ src/
COPY Makefile .

RUN mkdir -p bin obj && make

# ---

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /farsite/bin/TestFARSITE /usr/local/bin/TestFARSITE

RUN mkdir -p /data/input /data/output

WORKDIR /data

ENTRYPOINT ["TestFARSITE"]
