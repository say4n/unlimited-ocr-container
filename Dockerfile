ARG DEBIAN_FRONTEND=noninteractive
ARG UNLIMITED_OCR_REF=c7ade8c686d8f026c2db43b58320e0a1e39e4064

FROM nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 AS gpu

ARG DEBIAN_FRONTEND
ARG UNLIMITED_OCR_REF

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/huggingface \
    TRANSFORMERS_CACHE=/models/huggingface \
    SGLANG_DISABLE_TORCH_COMPILE_CACHE=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    libnuma1 \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
  && rm -rf /var/lib/apt/lists/*

RUN python3.12 -m venv /opt/venv \
  && python -m pip install --upgrade pip setuptools wheel

WORKDIR /opt
RUN git clone https://github.com/baidu/Unlimited-OCR.git /opt/Unlimited-OCR \
  && cd /opt/Unlimited-OCR \
  && git checkout "${UNLIMITED_OCR_REF}"

WORKDIR /opt/Unlimited-OCR
RUN python -m pip install wheel/sglang-0.0.0.dev11416+g92e8bb79e-py3-none-any.whl \
  && python -m pip install kernels==0.11.7 pymupdf==1.27.2.2 requests

COPY scripts/entrypoint.sh /usr/local/bin/unlimited-ocr
RUN chmod +x /usr/local/bin/unlimited-ocr \
  && mkdir -p /workspace /models/huggingface \
  && chmod -R 777 /models

WORKDIR /workspace
ENTRYPOINT ["unlimited-ocr"]
CMD ["--help"]

FROM python:3.12-slim AS cpu

ARG DEBIAN_FRONTEND
ARG UNLIMITED_OCR_REF

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/huggingface \
    TRANSFORMERS_CACHE=/models/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone https://github.com/baidu/Unlimited-OCR.git /opt/Unlimited-OCR \
  && cd /opt/Unlimited-OCR \
  && git checkout "${UNLIMITED_OCR_REF}"

RUN python -m pip install --upgrade pip setuptools wheel \
  && python -m pip install --index-url https://download.pytorch.org/whl/cpu \
    torch==2.10.0 \
    torchvision==0.25.0 \
  && python -m pip install \
    transformers==4.57.1 \
    Pillow==12.1.1 \
    matplotlib==3.10.8 \
    einops==0.8.2 \
    addict==2.4.0 \
    easydict==1.13 \
    pymupdf==1.27.2.2 \
    psutil==7.2.2

COPY scripts/cpu_infer.py /usr/local/bin/unlimited-ocr-cpu
RUN chmod +x /usr/local/bin/unlimited-ocr-cpu \
  && mkdir -p /workspace /models/huggingface \
  && chmod -R 777 /models

WORKDIR /workspace
ENTRYPOINT ["unlimited-ocr-cpu"]
CMD ["--help"]

FROM cpu AS default
