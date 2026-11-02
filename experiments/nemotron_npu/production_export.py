"""Export the five accepted streaming graphs from pinned weights, without test audio."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import openvino as ov
import torch
from transformers import AutoModelForRNNT, AutoProcessor

from export import Predictor, Joint
from stream_export import Subsampler, EncoderBody, states

REVISION = 'ea30d66debe3740a08b573244286791d423d6b3e'
WEIGHTS_SHA256 = '9eebdd6590289cb3030f310858f3df93256600a800a3e8200c5993d5f967e174'


def export(model_path, output):
    with (model_path / 'model.safetensors').open('rb') as source:
        if hashlib.file_digest(source, 'sha256').hexdigest() != WEIGHTS_SHA256:
            raise ValueError('Pinned NVIDIA weights integrity failure')
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    model = AutoModelForRNNT.from_pretrained(model_path, local_files_only=True,
        dtype=torch.float32, attn_implementation='sdpa').eval()
    processor = AutoProcessor.from_pretrained(model_path, local_files_only=True)
    output.mkdir(parents=True, exist_ok=False)
    frames = 64
    with torch.inference_mode():
        subs, state = states(model)
        body = EncoderBody(model, frames).eval()
        for name, module, inputs in [
            ('predictor', Predictor(model), (torch.tensor([[model.config.blank_token_id]]),
                torch.zeros(2, 1, 640), torch.zeros(2, 1, 640))),
            ('joint', Joint(model), (torch.zeros(1, 1, 640), torch.zeros(1, 1, 640))),
            ('subsampler_first', Subsampler(model, True), (torch.zeros(1, frames*8-7, 128), *subs)),
            ('subsampler_step', Subsampler(model), (torch.zeros(1, frames*8, 128), *subs)),
            ('encoder_stream', body, (torch.zeros(1, frames, 1024), torch.tensor([101]), body.attention_mask(56), *state)),
        ]:
            print(f'Exporting {name}', flush=True)
            converted = ov.convert_model(module.eval(), example_input=inputs)
            converted.reshape({i: list(value.shape) for i, value in enumerate(inputs)})
            ov.save_model(converted, output / f'{name}.xml', compress_to_fp16=False)
        np.savez(output / 'frontend.npz', mel=processor.feature_extractor.mel_filters.numpy(),
                 window=torch.hann_window(400, periodic=False).numpy())
        metadata = dict(mode='cached-streaming', reference_revision=REVISION,
            transformers='5.13.0', blank=model.config.blank_token_id,
            max_symbols=model.max_symbols_per_step, hidden=model.config.decoder_hidden_size,
            layers=model.config.num_decoder_layers, encoder_frames=frames, left_context=body.left,
            first_mel_frames=frames*8-7, mel_frames=frames*8, max_samples=16000*600,
            subsampler_shapes=[list(s.shape) for s in subs], state_shapes=[list(s.shape) for s in state])
        (output / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(args.model, args.output)
