"""Export explicit streaming state from the pinned Transformers reference.

Reference algorithms are Apache-2.0 Transformers 5.13.0; see
TRANSFORMERS-LICENSE. All cache tensors have bounded static shapes.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import openvino as ov
import soundfile as sf
import torch
from transformers import AutoModelForRNNT, AutoProcessor


class ConvState:
    def __init__(self, values, first=False):
        self.values = values
        self.next = {}
        self.first = first

    def update(self, hidden, key, module):
        previous = self.values[key]
        axis = 2
        joined = torch.cat([previous, hidden], dim=axis)
        self.next[key] = joined[:, :, -module.left_pad:]
        if self.first and hidden.ndim == 4:
            extra = module.left_pad_init-module.left_pad
            joined = torch.nn.functional.pad(joined, (0, 0, extra, 0))
        return joined


class Subsampler(torch.nn.Module):
    def __init__(self, model, first=False):
        super().__init__()
        self.subsampling = model.encoder.subsampling
        self.scale = model.encoder.input_scale
        self.first = first

    def forward(self, features, c0, c1, c2):
        cache = ConvState(dict(zip(['subsampling.0', 'subsampling.1', 'subsampling.2'],
                                   [c0, c1, c2])), self.first)
        hidden = self.subsampling(features, padding_cache=cache)*self.scale
        return (hidden, *(cache.next[f'subsampling.{i}'] for i in range(3)))


class AttentionState:
    def __init__(self, keys, values, length):
        self.keys, self.values, self.length = keys, values, length
        self.next_keys, self.next_values = [], []

    def update(self, keys, values, index):
        keys = torch.cat([self.keys[index], keys], dim=2)
        values = torch.cat([self.values[index], values], dim=2)
        self.next_keys.append(keys[:, :, -self.length:])
        self.next_values.append(values[:, :, -self.length:])
        return keys, values


class EncoderBody(torch.nn.Module):
    def __init__(self, model, frames):
        super().__init__()
        self.encoder = model.encoder
        self.prompt_projector = model.prompt_projector
        self.encoder_projector = model.encoder_projector
        self.num_prompts = model.config.num_prompts
        self.left = model.config.encoder_config.sliding_window-1
        self.frames = frames

    def attention_mask(self, seen):
        q = torch.arange(self.frames)+self.left
        k = torch.arange(self.left+self.frames)
        distance = q[:, None]//4-k[None, :]//4
        return ((distance >= 0) & (distance <= self.left//4)
                & (k[None, :] >= self.left-seen))[None, None]

    def forward(self, hidden, prompt, mask, keys, values, conv):
        cache = AttentionState(keys, values, self.left)
        padding = ConvState({f'conv.{i}': conv[i] for i in range(len(self.encoder.layers))})
        positions = self.encoder.encode_positions(hidden, cached_frames=self.left)
        for layer in self.encoder.layers:
            hidden = layer(hidden, attention_mask=mask, position_embeddings=positions,
                           past_key_values=cache, padding_cache=padding, use_cache=True)
        one_hot = torch.nn.functional.one_hot(prompt, self.num_prompts).to(hidden.dtype)
        fused = self.prompt_projector(torch.cat(
            [hidden, one_hot[:, None, :].expand(-1, self.frames, -1)], dim=-1))
        return (self.encoder_projector(fused), torch.stack(cache.next_keys),
                torch.stack(cache.next_values),
                torch.stack([padding.next[f'conv.{i}'] for i in range(len(self.encoder.layers))]))


def states(model):
    cfg = model.config.encoder_config
    subs = [torch.zeros(1, 1, 1, cfg.num_mel_bins+3)]
    frequency = cfg.num_mel_bins
    for _ in range(2):
        frequency = frequency//2+1
        subs.append(torch.zeros(1, cfg.subsampling_conv_channels, 1, frequency+3))
    keys = torch.zeros(cfg.num_hidden_layers, 1, cfg.num_attention_heads,
                       cfg.sliding_window-1, cfg.hidden_size//cfg.num_attention_heads)
    conv = torch.zeros(cfg.num_hidden_layers, 1, cfg.hidden_size, cfg.conv_kernel_size-1)
    return subs, [keys, torch.zeros_like(keys), conv]


def chunks(features, frames):
    """Aligned first and continuation mel groups, retaining the final fragment."""
    start, count = 0, frames*8-7
    while start < features.shape[1]:
        chunk = features[:, start:start+count]
        yield torch.nn.functional.pad(chunk, (0, 0, 0, count-chunk.shape[1]))
        start += count
        count = frames*8


def emit(stage, **fields):
    print(json.dumps({'stage': stage, **fields}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--base-artifact', type=Path, required=True)
    p.add_argument('--audio', type=Path, nargs='+', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--frames', type=int, default=64)
    p.add_argument('--check-only', action='store_true')
    args = p.parse_args()
    if args.frames < 4 or args.frames % 4:
        raise ValueError('Encoder groups must contain whole four-frame attention chunks')
    with (args.model/'model.safetensors').open('rb') as source:
        if hashlib.file_digest(source, 'sha256').hexdigest() != '9eebdd6590289cb3030f310858f3df93256600a800a3e8200c5993d5f967e174':
            raise ValueError('Pinned model integrity check failed')
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    emit('loading_reference')
    model = AutoModelForRNNT.from_pretrained(args.model, local_files_only=True,
        dtype=torch.float32, attn_implementation='sdpa').eval()
    processor = AutoProcessor.from_pretrained(args.model, local_files_only=True)
    first, step, body = Subsampler(model, True).eval(), Subsampler(model).eval(), EncoderBody(model, args.frames).eval()
    args.output.mkdir(parents=True, exist_ok=True)
    comparisons = []
    with torch.inference_mode():
        for path in args.audio:
            audio, sr = sf.read(path, dtype='float32')
            if sr != 16000 or audio.ndim != 1:
                raise ValueError('Expected mono 16 kHz fixture')
            batch = processor(audio, sampling_rate=sr, language='auto', return_tensors='pt')
            subs, state = states(model)
            kv, padding = None, None
            reference, actual, groups = [], [], []
            for group, features in enumerate(chunks(batch.input_features, args.frames)):
                sub_result = (first if group == 0 else step)(features, *subs)
                subs = list(sub_result[1:])
                output = body(sub_result[0], batch.prompt_ids,
                              body.attention_mask(min(group*args.frames, body.left)), *state)
                state = list(output[1:])
                # Compare to native reference chunks, including all warm-up and rollover states.
                offset = 0
                count = 25 if group == 0 else 32
                pieces = []
                while offset < features.shape[1]:
                    result = model.get_audio_features(features[:, offset:offset+count],
                        prompt_ids=batch.prompt_ids, past_key_values=kv, padding_cache=padding,
                        num_lookahead_tokens=3, use_cache=True)
                    kv, padding = result.past_key_values, result.padding_cache
                    pieces.append(result.pooler_output)
                    offset += count
                    count = 32
                target = torch.cat(pieces, dim=1)
                delta = float((output[0]-target).abs().max())
                emit('group_parity', audio=path.name, group=group, max_abs=delta)
                torch.testing.assert_close(output[0], target, atol=2e-4, rtol=2e-4)
                actual.append(output[0].numpy())
                reference.append(target.numpy())
                groups.append(features.numpy())
            generated = model.generate(input_features=(part for part in chunks(batch.input_features, 4)),
                prompt_ids=batch.prompt_ids, num_lookahead_tokens=3, max_new_tokens=4096)
            tokens = generated.sequences[0].tolist()
            text = processor.batch_decode(generated.sequences, skip_special_tokens=True)[0]
            emit('reference_transcription', audio=path.name, text=text)
            np.savez(args.output/f'reference-{path.stem}.npz',
                first=groups[0], following=np.stack(groups[1:]) if len(groups)>1 else np.empty(0),
                encoded=np.concatenate(reference, axis=1), prompt=batch.prompt_ids.numpy(),
                samples=np.array(len(audio)), features=batch.input_features.numpy(), tokens=np.array(tokens))
            comparisons.append({'audio':path.name, 'groups':len(groups), 'passed':True})
        (args.output/'torch-parity.json').write_text(json.dumps(comparisons, indent=2), encoding='utf-8')
        if args.check_only:
            return
        subs, state = states(model)
        for name, module, inputs in [
            ('subsampler_first', first, (torch.zeros(1, args.frames*8-7, 128), *subs)),
            ('subsampler_step', step, (torch.zeros(1, args.frames*8, 128), *subs)),
            ('encoder_stream', body, (torch.zeros(1, args.frames, 1024), torch.tensor([101]), body.attention_mask(56), *state)),
        ]:
            emit('converting', component=name)
            converted = ov.convert_model(module, example_input=inputs)
            converted.reshape({i:list(v.shape) for i,v in enumerate(inputs)})
            ov.save_model(converted, args.output/f'{name}.xml', compress_to_fp16=False)
            emit('exported', component=name)
        for filename in ['predictor.xml','predictor.bin','joint.xml','joint.bin','frontend.npz']:
            shutil.copy2(args.base_artifact/filename, args.output/filename)
        metadata = json.loads((args.base_artifact/'metadata.json').read_text(encoding='utf-8'))
        metadata.update(mode='cached-streaming', encoder_frames=args.frames, left_context=body.left,
            first_mel_frames=args.frames*8-7, mel_frames=args.frames*8, max_samples=16000*600,
            subsampler_shapes=[list(s.shape) for s in subs], state_shapes=[list(s.shape) for s in state])
        (args.output/'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
