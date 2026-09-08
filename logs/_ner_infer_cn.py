"""Run NER inference on Chinese PII text using the Intel OpenVINO model."""
import json
import sys
import io
from pathlib import Path

# Send output to utf-8 log file (avoids PowerShell mojibake on Chinese)
out_log = Path(r'C:\Users\Trekker-PTL\superclaw_benchmark\logs\ner_infer_cn_output.txt')
log_fh = open(out_log, 'w', encoding='utf-8')
sys.stdout = log_fh
sys.stderr = log_fh

model_dir = Path(r'C:\Users\Trekker-PTL\Downloads\intel_models\multilang-pii-ner-ov-int8')
cfg = json.load(open(model_dir / 'config.json', encoding='utf-8'))
id2label = {int(k): v for k, v in cfg['id2label'].items()}

try:
    from openvino import Core
except Exception:
    try:
        from openvino.runtime import Core
    except Exception as e:
        print(f'openvino import failed: {e}')
        sys.exit(1)

import numpy as np

ie = Core()
compiled = ie.compile_model(model=str(model_dir / 'openvino_model.xml'), device_name='CPU')
input_names = [inp.any_name for inp in compiled.inputs]
output_names = [out.any_name for out in compiled.outputs]
print(f'openvino OK')
print(f'Inputs:  {input_names}')
print(f'Outputs: {output_names}')

try:
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(model_dir))
    TOKENIZER_MODE = 'hf'
    print('using transformers AutoTokenizer')
except Exception as e:
    print(f'transformers not available, trying openvino_tokenizers: {e}')
    try:
        from openvino_tokenizers import convert_tokenizer
        ov_tokenizer = convert_tokenizer(str(model_dir), with_detokenizer=False)
        tok_compiled = ie.compile_model(ov_tokenizer, 'CPU')
        TOKENIZER_MODE = 'ov'
        print('using openvino_tokenizers')
    except Exception as e2:
        print(f'no tokenizer available: {e2}')
        sys.exit(1)


def run(text, max_len=128):
    if TOKENIZER_MODE == 'hf':
        enc = tok(text, return_tensors='np', truncation=True, max_length=max_len, padding='max_length')
        feeds = {}
        for n in input_names:
            v = enc.get(n)
            if v is None:
                v = np.zeros_like(enc['input_ids'])
            feeds[n] = v.astype(np.int64)
        res = compiled(feeds)
        logits = res[output_names[0]]
        preds = np.argmax(logits, axis=-1)[0]
        tokens = tok.convert_ids_to_tokens(enc['input_ids'][0])
        return [(t, id2label.get(int(p), 'O')) for t, p in zip(tokens, preds)]
    else:
        out = tok_compiled([text])
        input_ids = out['input_ids']
        attention_mask = out['attention_mask']
        feeds = {input_names[0]: input_ids, input_names[1]: attention_mask}
        res = compiled(feeds)
        logits = res[output_names[0]]
        preds = np.argmax(logits, axis=-1)[0]
        return [(f'id={int(x)}', id2label.get(int(p), 'O')) for x, p in zip(input_ids[0], preds)]


samples = [
    ('CN_PERSON_only', '我的名字是张伟。'),
    ('CN_PERSON_in_sentence', '客户张伟打电话给李娜说他的订单有问题。'),
    ('CN_ADDRESS', '请把文件寄到北京市朝阳区建国路88号。'),
    ('CN_IDCARD', '他的身份证号是110101199003078239。'),
    ('CN_BANKCARD', '银行卡号6222021234567890123。'),
    ('CN_COMPANY', '上海华联科技公司的李娜是法人代表。'),
    ('CN_EMAIL', '邮箱是zhangwei@example.cn。'),
    ('CN_PASSWORD', '密码是Wx@2024cn#secure。'),
    ('CN_APIKEY', 'API key是sk-cn-9f3a71bd42ee4c0e8be1770c9d2f5a6b。'),
    ('ZH_MIXED', '客户张伟(110101199003078239)电话13800138001住北京市朝阳区建国路88号。'),
    ('EN_PERSON', 'My name is Dana Whitfield and I live in Bellevue.'),
    ('EN_SSN', 'SSN is 412-55-8921.'),
    ('EN_MIXED', 'Dana Whitfield SSN 412-55-8921 lives at 1487 Cedar Hollow Rd.'),
]

print()
print('='*78)
print('NER inference (35 labels, XLM-RoBERTa base, OpenVINO IR)')
print('='*78)
for label, text in samples:
    print(f'\n[{label}]  {text}')
    try:
        result = run(text)
        tokens = [t for t, _ in result]
        labels = [l for _, l in result]
        # Filter to non-O, skip special tokens
        special = {'<s>', '</s>', '<pad>', '<unk>', '<mask>', '[CLS]', '[SEP]', '[PAD]'}
        non_o = [(t, l) for t, l in result if l != 'O' and t not in special and not t.startswith('▁') and not t.startswith('<')]
        print(f'  tokens: {tokens[:40]}')
        if non_o:
            print('  entities:')
            for t, l in non_o:
                print(f'    {l:25s} {t!r}')
        else:
            print('  (no entities detected)')
    except Exception as e:
        print(f'  ERROR: {e}')

log_fh.close()
print(f'\nWritten to {out_log}', file=sys.__stderr__)
