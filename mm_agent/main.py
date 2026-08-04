import argparse
import logging

from mm_agent.logging_config import setup_logging
from mm_agent.config import load_config
from mm_agent.scheduler import Scheduler
from mm_agent.collectors import registry as collector_registry


def main():
    # Initialize structured logging
    logger = setup_logging()
    logger.info("MandateMind Agent starting up")

    parser = argparse.ArgumentParser(description="MandateMind Agent")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    args = parser.parse_args()

    logger.info(f"Loading config from {args.config}")
    config = load_config(args.config)

    scheduler = Scheduler(config)
    logger.info("Scheduler initialized")

    # Register collectors
    for name, collector_cls in collector_registry.items():
        collector_cfg = config.collectors.get(name)
        if collector_cfg and collector_cfg.enabled:
            logger.info(f"Registering collector: {name}")
            scheduler.register_collector(name, collector_cls, collector_cfg)
        else:
            logger.info(f"Collector disabled or missing config: {name}")

    logger.info("Starting scheduler loop")
    scheduler.run_forever()
