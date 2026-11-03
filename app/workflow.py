"""Load the ComfyUI API-format orbit workflow and patch its inputs for one job."""

import copy
import json

from .settings import ORBIT_PROMPT, WORKFLOW_DIR


def _by_title(graph: dict, title: str) -> tuple[str, dict]:
    for node_id, node in graph.items():
        if node.get("_meta", {}).get("title") == title:
            return node_id, node
    raise KeyError(f"workflow has no node titled {title!r}")


MODEL_INPUTS = {   # engine model role -> (node title, input name)
    "unet": ("Diffusion Model", "unet_name"),
    "clip": ("Text Encoder", "clip_name"),
    "vae": ("Video VAE", "vae_name"),
    "orbit_lora": ("Orbit LoRA", "lora_name"),
    "turbo_lora": ("Turbo LoRA", "lora_name"),
}


def build_orbit(image_name: str, width: int, height: int, frames: int, steps: int, seed: int,
                lora_strength: float, turbo: bool, prefix: str, models: dict | None = None) -> dict:
    with open(WORKFLOW_DIR / "orbit_api.json", encoding="utf-8") as f:
        graph = copy.deepcopy(json.load(f))

    # An existing ComfyUI may keep its models in subfolders or use other compatible builds.
    for role, name in (models or {}).items():
        if role in MODEL_INPUTS and name:
            title, key = MODEL_INPUTS[role]
            _by_title(graph, title)[1]["inputs"][key] = name

    _by_title(graph, "Input Image")[1]["inputs"]["image"] = image_name
    _by_title(graph, "Orbit LoRA")[1]["inputs"]["strength_model"] = lora_strength
    _by_title(graph, "Seed")[1]["inputs"]["noise_seed"] = seed
    _by_title(graph, "Scheduler")[1]["inputs"]["steps"] = steps
    _by_title(graph, "Save Frames")[1]["inputs"]["filename_prefix"] = prefix

    cond = _by_title(graph, "Orbit Conditioning")[1]["inputs"]
    cond.update(prompt=ORBIT_PROMPT, width=width, height=height, length=frames)

    if not turbo:
        # Bypass the Turbo LoRA: everything that read from it reads from the orbit LoRA instead.
        turbo_id, turbo_node = _by_title(graph, "Turbo LoRA")
        upstream = turbo_node["inputs"]["model"]
        del graph[turbo_id]
        for node in graph.values():
            for key, value in node["inputs"].items():
                if isinstance(value, list) and value and value[0] == turbo_id:
                    node["inputs"][key] = upstream
    return graph
