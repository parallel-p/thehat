# -*- coding: utf-8 -*-
"""Upload a built dataset folder to the Hugging Face Hub.

Separate from the build step on purpose: this is the only part that *publishes*.
It never handles your token -- authenticate yourself first with

    huggingface-cli login          # or: hf auth login

then:

    # dry run: show exactly what would be pushed, upload nothing
    python -m scripts.upload_hf_dataset --dir out/the-hat-games \
        --repo nzinov/the-hat-games --private

    # actually create the private repo and upload
    python -m scripts.upload_hf_dataset --dir out/the-hat-games \
        --repo nzinov/the-hat-games --private --do-upload
"""

import argparse
import logging
import os
import sys

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", required=True, help="folder produced by build_hf_dataset")
    p.add_argument("--repo", required=True, help="e.g. nzinov/the-hat-games")
    p.add_argument("--private", action="store_true", default=True,
                   help="create the repo private (default: private)")
    p.add_argument("--public", dest="private", action="store_false",
                   help="override: create/set the repo public")
    p.add_argument("--do-upload", action="store_true",
                   help="actually push; without it this is a dry run")
    args = p.parse_args()

    # The parquet is the canonical, HF-loadable copy; the jsonl is a bulky local
    # convenience mirror and is not published.
    ignore_patterns = ["*.jsonl"]
    files = []
    for root, _dirs, names in os.walk(args.dir):
        for name in names:
            if name.endswith(".jsonl"):
                continue
            full = os.path.join(root, name)
            files.append((full, os.path.relpath(full, args.dir)))
    files.sort(key=lambda t: t[1])
    if not files:
        p.error("no files under %s -- run scripts.build_hf_dataset first" % args.dir)

    total = sum(os.path.getsize(f) for f, _ in files)
    logger.info("repo=%s private=%s  (%d files, %.1f MiB)",
                args.repo, args.private, len(files), total / 1048576)
    for _full, rel in files:
        logger.info("  %s", rel)

    if not args.do_upload:
        logger.info("dry run -- nothing uploaded. Re-run with --do-upload to push.")
        return 0

    try:
        from huggingface_hub import HfApi
        from huggingface_hub.utils import HfHubHTTPError
    except ImportError:
        p.error("pip install huggingface_hub first")

    api = HfApi()
    try:
        whoami = api.whoami()
    except Exception as error:  # noqa: BLE001
        raise SystemExit(
            "not logged in to Hugging Face. Run `huggingface-cli login` "
            "with a write token, then retry.") from error
    logger.info("authenticated as %s", whoami.get("name"))

    api.create_repo(repo_id=args.repo, repo_type="dataset",
                    private=args.private, exist_ok=True)
    logger.info("uploading folder %s -> %s", args.dir, args.repo)
    api.upload_folder(folder_path=args.dir, repo_id=args.repo,
                      repo_type="dataset", ignore_patterns=ignore_patterns,
                      commit_message="Add anonymized Hat games dataset")
    logger.info("done: https://huggingface.co/datasets/%s", args.repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
