#!/usr/bin/python3
import os
import logging
import sys

logging.basicConfig(level=logging.INFO)


def process_batches():
    batch_ids = ""
    if os.environ.get("BATCH_IDS") == None:
        logging.info("Could not find BATCH_IDS as env var")
        exit(2)
    else:
        batch_ids = os.environ.get("BATCH_IDS")

    logging.info(batch_ids)


if __name__ == "__main__":
    process_batches()