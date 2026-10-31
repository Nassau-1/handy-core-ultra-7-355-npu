"""Export the pinned Hugging Face reference; never downloads or executes remote code.

Experimental, fixed-shape utterances, not cache-aware streaming. The reference
implementation comes from Apache-2.0 licensed Hugging Face Transformers 5.13.0.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

print('Importing reference dependencies...', flush=True)

import numpy as np
import openvino as ov
import soundfile as sf
import torch
from transformers import AutoModelForRNNT, AutoProcessor


class Encoder(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, features, mask, prompt):
        return self.model.get_audio_features(
            features, attention_mask=mask, prompt_ids=prompt,
            num_lookahead_tokens=3, use_cache=False,
        ).pooler_output


class Predictor(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.decoder = model.decoder

    def forward(self, token, hidden, cell):
        output, (hidden, cell) = self.decoder.lstm(
            self.decoder.embedding(token), (hidden, cell))
        return self.decoder.decoder_projector(output), hidden, cell


class StaticEncoder(torch.nn.Module):
    """Reference layers with a traceable, fixed-shape chunked attention mask.

    Implements the same `chunked_limited_mask_function` as the Apache-2.0 HF
    reference without its vmap-based mask factory (not TorchScript traceable).
    Must pass a numerical comparison to the unmodified reference before export.
    """
    def __init__(self, model):
        super().__init__()
        self.encoder = model.encoder
        self.prompt_projector = model.prompt_projector
        self.encoder_projector = model.encoder_projector
        self.num_prompts = model.config.num_prompts

    def forward(self, features, mask, prompt):
        encoder = self.encoder
        hidden = encoder.subsampling(features, mask) * encoder.input_scale
        length = hidden.shape[1]
        valid = encoder._get_output_attention_mask(mask, target_length=length)
        positions = torch.arange(length, device=hidden.device)
        chunks = positions // 4
        distance = chunks[:, None] - chunks[None, :]
        allowed = (distance >= 0) & (distance <= (encoder.config.sliding_window-1)//4)
        allowed = allowed[None, None, :, :] & valid[:, None, None, :]
        all_masked = torch.all(~allowed, dim=-1)
        embeddings = encoder.encode_positions(hidden, cached_frames=0)
        for layer in encoder.layers:
            hidden = layer(hidden, attention_mask=allowed, all_masked_rows=all_masked,
                           position_embeddings=embeddings, use_cache=False)
        one_hot = torch.nn.functional.one_hot(prompt, self.num_prompts).to(hidden.dtype)
        fused = self.prompt_projector(torch.cat(
            [hidden, one_hot[:, None, :].expand(-1, length, -1)], dim=-1))
        return self.encoder_projector(fused)


class Joint(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.joint = model.joint

    def forward(self, frame, prediction):
        return self.joint(prediction, frame).argmax(dim=-1)


def emit(stage, **kwargs):
    print(json.dumps({'stage': stage, **kwargs}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--audio', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--frames', type=int, default=1024)
    p.add_argument('--reference-only', action='store_true')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((args.model / 'source-manifest.json').read_text(encoding='utf-8'))
    if manifest['revision'] != 'ea30d66debe3740a08b573244286791d423d6b3e':
        raise ValueError('Unexpected model revision; use download.py')
    with (args.model / 'model.safetensors').open('rb') as weights:
        if hashlib.file_digest(weights, 'sha256').hexdigest() != '9eebdd6590289cb3030f310858f3df93256600a800a3e8200c5993d5f967e174':
            raise ValueError('Model weights failed the pinned integrity check')
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    start = time.perf_counter()
    emit('loading_reference')
    processor = AutoProcessor.from_pretrained(args.model, local_files_only=True)
    np.savez(args.output / 'frontend.npz', mel=processor.feature_extractor.mel_filters.numpy(),
             window=torch.hann_window(400, periodic=False).numpy())
    model = AutoModelForRNNT.from_pretrained(
        args.model, local_files_only=True, torch_dtype=torch.float32,
        attn_implementation='sdpa').eval()
    emit('reference_loaded', seconds=time.perf_counter()-start)
    audio, sr = sf.read(args.audio, dtype='float32')
    if sr != 16000 or audio.ndim != 1:
        raise ValueError('Expected mono 16 kHz audio')
    batch = processor(audio, sampling_rate=sr, return_tensors='pt', language='auto')
    from frontend import Processor
    frontend = Processor(args.output, args.model)(audio)
    torch.testing.assert_close(torch.from_numpy(frontend['input_features']),
                               batch['input_features'], rtol=1e-5, atol=2e-4)
    assert np.array_equal(frontend['attention_mask'], batch['attention_mask'].numpy())
    emit('frontend_parity', max_abs_error=float(np.max(np.abs(
        frontend['input_features']-batch['input_features'].numpy()))))
    emit('features', shapes={k: list(v.shape) for k, v in batch.items() if hasattr(v, 'shape')})
    features, mask = batch['input_features'], batch['attention_mask']
    if features.shape[1] > args.frames:
        raise ValueError('Audio exceeds the static export shape')
    features = torch.nn.functional.pad(features, (0, 0, 0, args.frames-features.shape[1]))
    mask = torch.nn.functional.pad(mask, (0, args.frames-mask.shape[1]))
    prompt = batch['prompt_ids']
    inputs = (features, mask, prompt)
    with torch.inference_mode():
        start = time.perf_counter()
        reference = Encoder(model)(*inputs)
        candidate = StaticEncoder(model)(*inputs)
        torch.testing.assert_close(candidate, reference, rtol=1e-4, atol=1e-4)
        if not torch.isfinite(reference).all():
            raise ValueError('Reference encoder produced nonfinite values')
        emit('static_mask_parity', max_abs_error=float((candidate-reference).abs().max()))
        valid = int(model.encoder._get_subsampling_output_length(mask.sum(-1)).item())
        generated = model.generate(input_features=features, attention_mask=mask,
                                   prompt_ids=prompt, num_lookahead_tokens=3)
        tokens = generated.sequences[0].tolist()
        text = processor.batch_decode(generated.sequences, skip_special_tokens=True)[0]
        emit('reference_transcription', text=text, seconds=time.perf_counter()-start)
        np.savez(args.output / 'reference.npz', features=features.numpy(), mask=mask.numpy(),
                 prompt=prompt.numpy(), encoded=reference.numpy(), valid=np.array(valid),
                 tokens=np.array(tokens))
        metadata = {'frames': args.frames, 'valid_frames': valid, 'text': text,
                    'blank': model.config.blank_token_id, 'max_symbols': model.max_symbols_per_step,
                    'hidden': model.config.decoder_hidden_size, 'layers': model.config.num_decoder_layers,
                    'reference_revision': 'ea30d66debe3740a08b573244286791d423d6b3e',
                    'transformers': '5.13.0', 'mode': 'fixed-shape-utterance'}
        (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
        if args.reference_only:
            return
        for name, module, example in [
            ('predictor', Predictor(model), (torch.tensor([[model.config.blank_token_id]]),
                torch.zeros(2, 1, 640), torch.zeros(2, 1, 640))),
            ('joint', Joint(model), (torch.zeros(1, 1, 640), torch.zeros(1, 1, 640))),
            ('encoder', StaticEncoder(model), inputs),
        ]:
            emit('converting', component=name)
            converted = ov.convert_model(module.eval(), example_input=example)
            converted.reshape({i: list(value.shape) for i, value in enumerate(example)})
            ov.save_model(converted, args.output / f'{name}.xml', compress_to_fp16=False)
            emit('exported', component=name)


if __name__ == '__main__':
    main()
