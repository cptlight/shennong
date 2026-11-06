#!/usr/bin/env bash
# Deploy the demo to Hugging Face Spaces.
#
#   export HF_TOKEN=hf_xxx          # write token for your account/org
#   ./scripts/deploy_space.sh your-user/shennong
#
# Creates the Space if needed, then uploads the Dockerfile and card. The Space builds the repo itself, so
# no large files are uploaded from here.
set -euo pipefail
SPACE="${1:?usage: deploy_space.sh <user-or-org>/<space-name>}"
: "${HF_TOKEN:?set HF_TOKEN (a Hugging Face write token)}"
cd "$(dirname "$0")/.."
.venv/bin/python - "$SPACE" <<'PY'
import os, sys
from huggingface_hub import HfApi
space = sys.argv[1]
api = HfApi(token=os.environ["HF_TOKEN"])
api.create_repo(repo_id=space, repo_type="space", space_sdk="docker", exist_ok=True)
for f in ("space/README.md", "space/Dockerfile"):
    api.upload_file(path_or_fileobj=f, path_in_repo=os.path.basename(f),
                    repo_id=space, repo_type="space")
print(f"deployed -> https://huggingface.co/spaces/{space}")
PY
