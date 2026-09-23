# OF3D Laya CLI

`of3d-laya-cli` wraps [Laya](https://github.com/NandhaKishorM/laya) with stable JSON input and output for the OF3D Doubao CLI connector.

Laya is a typed-decision model. It chooses among supplied labels, scores an ordered rubric, or estimates whether a proposition is true. It does not generate or translate text.

## Requirements

- Python 3.10 or newer; Python 3.11 is recommended.
- Internet access during installation and the first model download.
- Approximately 4 GB of free memory for a single checkpoint.
- A persistent Hugging Face cache is strongly recommended.

CUDA is optional. CPU inference works but every fresh CLI process pays the model-load cost.

## Install

Install directly from the OF3D GitLab repository:

```bash
python -m pip install "git+https://gitlab.of3d.com/liangcheng/of3d-laya-cli.git"
```

Verify the lightweight CLI without loading the model:

```bash
of3d-laya --version
of3d-laya health
```

Download and verify the default multilingual checkpoint:

```bash
of3d-laya prepare --checkpoint multilingual --device cpu
```

## Decide

Input can be supplied as a file, an argument, or standard input:

```bash
of3d-laya decide --input-file examples/feedback.json --device cpu
```

```bash
of3d-laya decide --device cpu < examples/feedback.json
```

The default checkpoint is `multilingual`. A request may override it with a top-level `checkpoint` field. Supported values are `english`, `multilingual`, and `typed-decisions`.

Output is one compact JSON object on standard output. Input and runtime errors are JSON objects on standard error with a non-zero exit code.

## Doubao CLI connector

Recommended connector settings:

| Field | Value |
|---|---|
| Connector type | CLI connector |
| Network | Public network available |
| Runtime | Python `>=3.11` |
| Install | `python -m pip install "git+https://gitlab.of3d.com/liangcheng/of3d-laya-cli.git"` |
| Authorization | Leave empty |
| Revoke authorization | Leave empty |
| Authorization status | Leave empty |
| Version check | `of3d-laya --version` |
| CLI command name | `of3d-laya` |

If the repository remains private, the connector runtime needs read access to it. Do not embed a personal GitLab token in a skill package distributed to the whole organization. Prefer an organization deploy token with read-only repository scope, or publish a sanitized package to the organization's Python registry.

### Suggested tool command

Pass request JSON through standard input when the connector supports it:

```bash
of3d-laya decide --device cpu
```

For environments that only support arguments:

```bash
of3d-laya decide --device cpu --input-json '<JSON>'
```

Standard input is safer for long text and avoids shell-quoting problems.

## Configuration

Environment variables provide defaults:

| Variable | Default | Values |
|---|---|---|
| `OF3D_LAYA_CHECKPOINT` | `multilingual` | `english`, `multilingual`, `typed-decisions` |
| `OF3D_LAYA_DEVICE` | `auto` | `auto`, `cpu`, `cuda` |
| `HF_HOME` | Hugging Face default | Persistent model cache directory |
| `HF_TOKEN` | unset | Optional token for Hugging Face access |

## Operational notes

- Start with a small user group and measure cold-start time, memory, timeout behavior, and cache persistence.
- Do not rely on confidence alone for automatic high-impact actions. Validate accuracy against OF3D feedback samples and retain human review for uncertain cases.
- The multilingual base checkpoint is not a substitute for domain fine-tuning. Treat the initial deployment as a pilot.

## Attribution

This adapter is licensed under Apache-2.0. Laya and its pretrained weights are maintained by Convai Innovations and upstream contributors; review their repository and model cards for their licenses and limitations.

