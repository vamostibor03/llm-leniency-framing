"""Host an open model on Modal as an OpenAI-compatible endpoint for the leniency harness.

UNTESTED (written without Modal access) - run the smoke test before any big run.

One-time setup:
    pip install modal && modal setup
    modal secret create leniency-serve LENIENCY_SERVE_KEY=<any-long-random-string>
    # only for gated models (Llama):  modal secret create huggingface HF_TOKEN=hf_...

Deploy (pick model + GPU; the endpoint scales to zero after 5 min idle, so it costs nothing while unused):
    SERVE_MODEL=Qwen/Qwen2.5-32B-Instruct SERVE_GPU=A100-80GB modal deploy deploy/modal_vllm.py
    # bigger:  SERVE_MODEL=meta-llama/Llama-3.3-70B-Instruct SERVE_GPU=H100:2 SERVE_TP=2 modal deploy ...

Modal prints a URL like https://<you>--leniency-vllm-serve.modal.run . Then:
    export LENIENCY_BASE_URL=https://<you>--leniency-vllm-serve.modal.run/v1
    export LENIENCY_API_KEY=<the same random string>
    python -m leniency run configs/smoke.yaml --model Qwen/Qwen2.5-32B-Instruct

Stop it when done:  modal app stop leniency-vllm
"""
import os
import subprocess

import modal

MODEL = os.environ.get("SERVE_MODEL", "Qwen/Qwen2.5-32B-Instruct")
GPU = os.environ.get("SERVE_GPU", "A100-80GB")
TP = os.environ.get("SERVE_TP", "1")              # tensor-parallel size = number of GPUs
MAX_LEN = os.environ.get("SERVE_MAX_LEN", "16384")  # our prompts are ~1-3k tokens
PORT = 8000

app = modal.App("leniency-vllm")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm==0.9.2", "huggingface_hub[hf_transfer]")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "SERVE_MODEL": MODEL, "SERVE_TP": TP, "SERVE_MAX_LEN": MAX_LEN})
)

# Cache weights across cold starts so you only pay the download once.
hf_cache = modal.Volume.from_name("leniency-hf-cache", create_if_missing=True)

secrets = [modal.Secret.from_name("leniency-serve")]
if os.environ.get("SERVE_HF_SECRET", "0") == "1" or MODEL.startswith("meta-llama/"):
    secrets.append(modal.Secret.from_name("huggingface"))


@app.function(
    image=image,
    gpu=GPU,
    timeout=24 * 3600,
    scaledown_window=300,      # shut down after 5 idle minutes -> no credits burned overnight
    max_containers=1,          # ONE GPU box; never fan out into many expensive containers
    volumes={"/root/.cache/huggingface": hf_cache},
    secrets=secrets,
)
@modal.concurrent(max_inputs=128)  # one container serves all parallel supergames (vLLM batches them)
@modal.web_server(port=PORT, startup_timeout=1800)
def serve():
    cmd = [
        "vllm", "serve", os.environ["SERVE_MODEL"],
        "--host", "0.0.0.0", "--port", str(PORT),
        "--served-model-name", os.environ["SERVE_MODEL"],
        "--tensor-parallel-size", os.environ["SERVE_TP"],
        "--max-model-len", os.environ["SERVE_MAX_LEN"],
        "--api-key", os.environ["LENIENCY_SERVE_KEY"],
    ]
    subprocess.Popen(cmd)
