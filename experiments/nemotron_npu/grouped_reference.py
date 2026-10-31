"""Efficient long reference using unmodified HF encoder/decoder components.

Must first match saved native-chunk HF generate references. Grouping only batches
aligned attention chunks; it never changes the reference mask or cache classes.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import AutoModelForRNNT, AutoProcessor
from transformers.models.nemotron3_5_asr.generation_nemotron3_5_asr import Nemotron3_5AsrRNNTDecoderCache

from stream_export import chunks


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--audio', type=Path, nargs='+', required=True)
    p.add_argument('--native-references', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    with (args.model/'model.safetensors').open('rb') as source:
        if hashlib.file_digest(source,'sha256').hexdigest() != '9eebdd6590289cb3030f310858f3df93256600a800a3e8200c5993d5f967e174':
            raise ValueError('Pinned model integrity check failed')
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    model = AutoModelForRNNT.from_pretrained(args.model, local_files_only=True,
        dtype=torch.float32, attn_implementation='sdpa').eval()
    processor = AutoProcessor.from_pretrained(args.model, local_files_only=True)
    args.output.mkdir(parents=True, exist_ok=True)
    verified = 0
    report = []
    with torch.inference_mode():
        for path in args.audio:
            native_path = args.native_references/f'reference-{path.stem}.npz'
            if not native_path.exists() and verified < 3:
                raise ValueError('Verify at least three native HF references before a new long fixture')
            audio,sr = sf.read(path,dtype='float32')
            if sr != 16000 or audio.ndim != 1:
                raise ValueError('Expected mono 16 kHz')
            batch = processor(audio,sampling_rate=sr,language='auto',return_tensors='pt')
            groups = list(chunks(batch.input_features,64))
            kv,padding = None,None
            encoded=[]
            for index,group in enumerate(groups):
                result=model.get_audio_features(group,prompt_ids=batch.prompt_ids,
                    past_key_values=kv,padding_cache=padding,num_lookahead_tokens=3,use_cache=True)
                kv,padding=result.past_key_values,result.padding_cache
                encoded.append(result.pooler_output)
                if index%16==0:
                    print(json.dumps({'audio':path.name,'encoded_group':index}),flush=True)
            encoded=torch.cat(encoded,dim=1)
            valid=((len(audio)//160+1+7+31)//32)*4
            cache=Nemotron3_5AsrRNNTDecoderCache(model.config)
            blank=model.config.blank_token_id
            prediction=model.decoder(torch.tensor([[blank]]),cache=cache)
            tokens=[]
            for index in range(valid):
                for _ in range(model.max_symbols_per_step):
                    token=int(model.joint(prediction,encoded[:,index:index+1]).argmax(dim=-1).item())
                    if token==blank:
                        break
                    tokens.append(token)
                    prediction=model.decoder(torch.tensor([[token]]),cache=cache)
            if native_path.exists():
                native=np.load(native_path)
                np.testing.assert_allclose(encoded.numpy(),native['encoded'],rtol=2e-4,atol=2e-4)
                expected=[int(t) for t in native['tokens'] if t!=blank]
                if tokens!=expected:
                    raise ValueError('Grouped reference decoder differs from HF generate')
                verified+=1
            np.savez(args.output/f'reference-{path.stem}.npz', first=groups[0].numpy(),
                following=np.stack([g.numpy() for g in groups[1:]]) if len(groups)>1 else np.empty(0),
                encoded=encoded.numpy(),prompt=batch.prompt_ids.numpy(),samples=np.array(len(audio)),
                features=batch.input_features.numpy(),tokens=np.array(tokens))
            report.append({'audio':path.name,'samples':len(audio),'tokens':len(tokens),
                           'matched_native_reference':native_path.exists()})
            (args.output/'grouped-reference-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report[-1]),flush=True)


if __name__=='__main__':
    main()
