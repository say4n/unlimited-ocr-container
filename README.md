# unlimited-ocr-container

Ready-to-run container images for [baidu/Unlimited-OCR](https://github.com/baidu/Unlimited-OCR).

## Images

The images are published to GHCR from every commit to `main`.

```text
ghcr.io/say4n/unlimited-ocr-container:cpu
ghcr.io/say4n/unlimited-ocr-container:gpu
```

Use the GPU image when you have NVIDIA Docker support. Use the CPU image only for testing or small jobs; it is much slower.

The CPU image is published for `linux/amd64` and `linux/arm64`, so it works on Intel/AMD Linux machines and Apple Silicon Docker. The GPU image is published for `linux/amd64`.

Apple Silicon Docker runs Linux containers, so the CPU image cannot access the macOS MPS backend or the Apple GPU. The bundled runner prefers MPS only when it is run natively on macOS with an MPS-enabled PyTorch build.

## Requirements

GPU:

- Docker with NVIDIA GPU support.
- NVIDIA Container Toolkit installed on the host.
- A CUDA-capable NVIDIA GPU with enough VRAM for the model.

CPU:

- Docker.
- Enough system RAM for the model.

Both images may need Hugging Face access to `baidu/Unlimited-OCR`, depending on your environment.

## Setup

Create folders for input files, OCR output, and model cache:

```bash
mkdir -p data outputs log models
```

The `models` mount keeps the Hugging Face cache between runs.

## Run with GPU

PDF:

```bash
docker run --rm --gpus all \
  -v "$PWD/data:/data:ro" \
  -v "$PWD/outputs:/workspace/outputs" \
  -v "$PWD/log:/workspace/log" \
  -v "$PWD/models:/models" \
  ghcr.io/say4n/unlimited-ocr-container:gpu \
  --pdf /data/document.pdf \
  --output_dir /workspace/outputs \
  --concurrency 8 \
  --gpu 0 \
  --image_mode gundam
```

Image directory:

```bash
docker run --rm --gpus all \
  -v "$PWD/data:/data:ro" \
  -v "$PWD/outputs:/workspace/outputs" \
  -v "$PWD/log:/workspace/log" \
  -v "$PWD/models:/models" \
  ghcr.io/say4n/unlimited-ocr-container:gpu \
  --image_dir /data/images \
  --output_dir /workspace/outputs \
  --concurrency 8 \
  --gpu 0 \
  --image_mode gundam
```

Markdown outputs are written to `outputs/`. The SGLang server log is written to `log/sglang_server.log`.

## Run with CPU

The CPU image supports `--pdf`, `--image_file`, and `--image_dir`. It does not accept GPU/SGLang options such as `--gpu`, `--concurrency`, or `--server_log`.

OCR text is printed to container stdout and also written as Markdown files in `/workspace/outputs`.

PDF:

```bash
docker run --rm \
  -v "$PWD/data:/data:ro" \
  -v "$PWD/outputs:/workspace/outputs" \
  -v "$PWD/models:/models" \
  ghcr.io/say4n/unlimited-ocr-container:cpu \
  --pdf /data/document.pdf \
  --output_dir /workspace/outputs
```

Image directory:

```bash
docker run --rm \
  -v "$PWD/data:/data:ro" \
  -v "$PWD/outputs:/workspace/outputs" \
  -v "$PWD/models:/models" \
  ghcr.io/say4n/unlimited-ocr-container:cpu \
  --image_dir /data/images \
  --output_dir /workspace/outputs \
  --image_mode gundam
```

Single image:

```bash
docker run --rm \
  -v "$PWD/data:/data:ro" \
  -v "$PWD/outputs:/workspace/outputs" \
  -v "$PWD/models:/models" \
  ghcr.io/say4n/unlimited-ocr-container:cpu \
  --image_file /data/page.png \
  --output_dir /workspace/outputs
```

For PDFs and single images, the stable output file is named after the input, for example `outputs/document.md` or `outputs/page.md`. For image directories, each image gets its own Markdown file under `outputs/`, with nested path separators replaced by `__`.

## Hugging Face Token

If your Hugging Face setup needs a token, pass it at runtime:

```bash
docker run --rm --gpus all \
  -e HF_TOKEN="$HF_TOKEN" \
  -v "$PWD/data:/data:ro" \
  -v "$PWD/outputs:/workspace/outputs" \
  -v "$PWD/log:/workspace/log" \
  -v "$PWD/models:/models" \
  ghcr.io/say4n/unlimited-ocr-container:gpu \
  --pdf /data/document.pdf \
  --output_dir /workspace/outputs
```

## Options

GPU image:

```text
--pdf PATH                       Convert a PDF to page images and OCR each page.
--image_dir PATH                 OCR every supported image under a directory.
--output_dir PATH                Directory for Markdown output files.
--concurrency N                  Number of concurrent requests to the local SGLang server.
--gpu GPU                        CUDA_VISIBLE_DEVICES value inside the container.
--model_dir MODEL                Hugging Face model ID or local model path.
--image_mode {gundam,base}       Upstream image mode.
--server_log PATH                SGLang server log path.
```

CPU image:

```text
--pdf PATH                       Convert a PDF to page images and OCR it.
--image_file PATH                OCR one image.
--image_dir PATH                 OCR every supported image under a directory sequentially.
--output_dir PATH                Directory for Markdown output files.
--model_dir MODEL                Hugging Face model ID or local model path.
--image_mode {gundam,base}       Upstream single-image mode.
--max_length N                   Maximum generated sequence length.
--pdf_dpi N                      DPI used when converting PDF pages to images.
```

## Publishing

The GitHub Actions workflow at `.github/workflows/publish.yml` builds and pushes both images on every commit to `main`:

- `ghcr.io/say4n/unlimited-ocr-container:cpu`
- `ghcr.io/say4n/unlimited-ocr-container:gpu`
- `ghcr.io/say4n/unlimited-ocr-container:cpu-<commit-sha>`
- `ghcr.io/say4n/unlimited-ocr-container:gpu-<commit-sha>`

The `cpu` tags are multi-arch (`linux/amd64`, `linux/arm64`). The `gpu` tags are `linux/amd64`.

## Development

Local builds are only needed when changing the image definitions:

```bash
docker build --target cpu -t unlimited-ocr:cpu .
docker build --target gpu -t unlimited-ocr:gpu .
```

Plain `docker build -t unlimited-ocr:latest .` builds the CPU target.
