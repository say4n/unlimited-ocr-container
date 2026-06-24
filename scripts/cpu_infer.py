#!/usr/bin/env python3
"""CPU/MPS-oriented Transformers runner for baidu/Unlimited-OCR."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer


PROMPT_SINGLE = "<image>document parsing."
PROMPT_MULTI = "<image>Multi page parsing."


def preferred_device() -> torch.device:
    mps_backend = getattr(torch.backends, "mps", None)
    if mps_backend is not None and mps_backend.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def move_tensor(tensor: torch.Tensor, device: torch.device) -> torch.Tensor:
    if device.type in {"cpu", "mps"} and tensor.is_floating_point() and tensor.dtype == torch.bfloat16:
        tensor = tensor.float()
    return tensor.to(device=device)


def install_cuda_shim(device: torch.device) -> None:
    if torch.cuda.is_available():
        return

    def tensor_cuda(self, device=None, non_blocking=False, memory_format=torch.preserve_format):
        return move_tensor(self, selected_device)

    def module_cuda(self, device=None):
        return self.to(selected_device)

    selected_device = device
    torch.Tensor.cuda = tensor_cuda
    torch.nn.Module.cuda = module_cuda


def pdf_to_images(pdf_path: str, dpi: int) -> list[str]:
    import fitz

    doc = fitz.open(pdf_path)
    tmp_dir = tempfile.mkdtemp(prefix="pdf_ocr_")
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    paths = []
    for i, page in enumerate(doc):
        out = os.path.join(tmp_dir, f"page_{i + 1:04d}.png")
        page.get_pixmap(matrix=mat).save(out)
        paths.append(out)
    doc.close()
    return paths


def collect_images(image_dir: str) -> list[str]:
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    return sorted(
        str(path)
        for path in Path(image_dir).rglob("*")
        if path.is_file() and path.suffix.lower() in exts
    )


def image_config(image_mode: str) -> dict:
    if image_mode == "base":
        return {"base_size": 1024, "image_size": 1024, "crop_mode": False}
    return {"base_size": 1024, "image_size": 640, "crop_mode": True}


def output_stem(input_path: str, suffix: str = "") -> str:
    stem = Path(input_path).stem
    return f"{stem}{suffix}" if suffix else stem


def persist_result(output_dir: str, destination_stem: str) -> Path | None:
    result_file = Path(output_dir) / "result.md"
    if not result_file.exists():
        return None
    destination = Path(output_dir) / f"{destination_stem}.md"
    if result_file.resolve() != destination.resolve():
        shutil.copyfile(result_file, destination)
    print(f"\nOCR output written to {destination}", flush=True)
    return destination


def load_model(model_dir: str):
    device = preferred_device()
    install_cuda_shim(device)
    print(f"Using device: {device}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        model_dir,
        trust_remote_code=True,
        use_safetensors=True,
        dtype=torch.float32,
    )
    model = model.eval().to(device)
    return tokenizer, model


def run_single_image(model, tokenizer, image_file: str, args, output_stem_value: str | None = None) -> None:
    config = image_config(args.image_mode)
    model.infer(
        tokenizer,
        prompt=PROMPT_SINGLE,
        image_file=image_file,
        output_path=args.output_dir,
        max_length=args.max_length,
        no_repeat_ngram_size=args.no_repeat_ngram_size,
        ngram_window=128,
        save_results=True,
        **config,
    )
    persist_result(args.output_dir, output_stem_value or output_stem(image_file))


def run(args) -> None:
    os.makedirs(args.output_dir, exist_ok=True)
    tokenizer, model = load_model(args.model_dir)

    if args.pdf:
        image_files = pdf_to_images(args.pdf, args.pdf_dpi)
        model.infer_multi(
            tokenizer,
            prompt=PROMPT_MULTI,
            image_files=image_files,
            output_path=args.output_dir,
            image_size=1024,
            max_length=args.max_length,
            no_repeat_ngram_size=args.no_repeat_ngram_size,
            ngram_window=1024,
            save_results=True,
        )
        persist_result(args.output_dir, output_stem(args.pdf))
        return

    if args.image_file:
        run_single_image(model, tokenizer, args.image_file, args)
        return

    if args.image_dir:
        image_files = collect_images(args.image_dir)
        if not image_files:
            raise ValueError(f"No supported images found in {args.image_dir}")
        for index, image_file in enumerate(image_files, start=1):
            print(f"[{index}/{len(image_files)}] {image_file}", flush=True)
            rel_stem = Path(image_file).relative_to(args.image_dir).with_suffix("")
            run_single_image(
                model,
                tokenizer,
                image_file,
                args,
                output_stem_value=str(rel_stem).replace(os.sep, "__"),
            )
        return

    raise ValueError("Pass one of --pdf, --image_file, or --image_dir")


def parse_args():
    parser = argparse.ArgumentParser(
        description="CPU/MPS Transformers inference for baidu/Unlimited-OCR.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--image_file", default="", help="Single image to OCR")
    parser.add_argument("--image_dir", default="", help="Directory of images to OCR sequentially")
    parser.add_argument("--pdf", default="", help="PDF to convert and OCR")
    parser.add_argument("--output_dir", default="./outputs")
    parser.add_argument("--model_dir", default="baidu/Unlimited-OCR")
    parser.add_argument("--image_mode", choices=("gundam", "base"), default="gundam")
    parser.add_argument("--max_length", type=int, default=32768)
    parser.add_argument("--no_repeat_ngram_size", type=int, default=35)
    parser.add_argument("--pdf_dpi", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
