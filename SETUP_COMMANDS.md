# Environment Setup Commands

These are the commands needed to use the Cedar verification stack from the `vllm` conda environment.

## Activate The Environment

```bash
conda activate vllm
```

## Check Installed Tools

```bash
cedar --version
cedar symcc --help
cvc5 --version
which cedar
which cvc5
```

Expected binaries:

- `cedar`: `/home/yzhou136/miniconda3/envs/vllm/bin/cedar`
- `cvc5`: `/home/yzhou136/miniconda3/envs/vllm/bin/cvc5`

## Run The Main Verifier

From the repo root:

```bash
conda activate vllm
cd /home/yzhou136/cedar-synthesis-engine
CVC5=$CONDA_PREFIX/bin/cvc5 python orchestrator.py --workspace experiments/github
```

## Run The Evaluation Harness

Single scenario:

```bash
conda activate vllm
cd /home/yzhou136/cedar-synthesis-engine
CVC5=$CONDA_PREFIX/bin/cvc5 python eval_harness.py --scenario experiments/github --no-review
```

Multiple scenarios:

```bash
conda activate vllm
cd /home/yzhou136/cedar-synthesis-engine
CVC5=$CONDA_PREFIX/bin/cvc5 python eval_harness.py --all --no-review --max-iters 20
```

## If You Need To Rebuild Cedar With `symcc`

The `symcc` subcommand is not included in the default crates.io install of `cedar-policy-cli`.
It must be built from the upstream Cedar source with the `analyze` feature enabled.

```bash
conda activate vllm
git clone --depth 1 https://github.com/cedar-policy/cedar /tmp/cedar-upstream
cargo install --path /tmp/cedar-upstream/cedar-policy-cli \
  --features analyze \
  --root $CONDA_PREFIX \
  --force
```

## If You Need To Install `cvc5` Again

```bash
conda activate vllm
tmpdir=$(mktemp -d)
cd "$tmpdir"
curl -L -o cvc5.zip https://github.com/cvc5/cvc5/releases/download/cvc5-1.3.3/cvc5-Linux-x86_64-static.zip
unzip -q cvc5.zip
find . -type f -name cvc5 -perm -111 -print -quit | xargs -I{} install -m 755 {} "$CONDA_PREFIX/bin/cvc5"
```

