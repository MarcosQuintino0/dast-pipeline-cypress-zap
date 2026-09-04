"""
CLI to process HAR files.

Usage:
    python -m security_tests.cli.process_har

This script runs the complete preprocessing pipeline:
1. Loads all raw HARs from the traffic/ folder
2. Extracts entries (HTTP requests)
3. Filters by business rules (status, endpoint, method)
4. Deduplicates by METHOD|URL combination
5. Tokenizes sensitive fields (userId, id, postId → {{AUTO_INT}})
6. Saves the filtered HAR as filtered_traffic.har

Run AFTER running the Cypress tests (which generate the raw HARs)
and BEFORE running the ZAP scan.
"""

from loguru import logger

from security_tests.har.preprocessing import (
    extract_entries,
    filter_and_deduplicate_entries,
    load_hars,
    save_har,
)


def main() -> None:
    """Main HAR processing pipeline.

    Every failure path exits with a non-zero status. Returning normally would
    hand the next step of the pipeline a success signal over a file that was
    never written — and a scan that never ran looks exactly like a scan that
    found nothing.
    """
    logger.info("=" * 60)
    logger.info("STARTING HAR PROCESSING")
    logger.info("=" * 60)

    # Step 1: Load raw HARs
    hars = load_hars()
    if not hars:
        logger.error("No HAR files found! Run the Cypress tests first: npm run test:e2e")
        raise SystemExit(1)

    # Step 2: Extract entries
    entries = extract_entries(hars)
    if not entries:
        logger.error("No entries found in the HARs!")
        raise SystemExit(1)

    # Step 3: Filter, deduplicate and tokenize
    filtered_entries = filter_and_deduplicate_entries(entries)
    if not filtered_entries:
        logger.error("No entries passed the filters! Check the ENDPOINT_RULES in config.py")
        raise SystemExit(1)

    # Step 4: Save filtered HAR
    path = save_har(filtered_entries)

    logger.info("=" * 60)
    logger.info("PROCESSING COMPLETE")
    logger.info(f"  Original entries: {len(entries)}")
    logger.info(f"  Filtered entries: {len(filtered_entries)}")
    logger.info(f"  File saved: {path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
