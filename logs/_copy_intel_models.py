import shutil
from pathlib import Path

src_root = Path(r'C:\Program Files\Intel\SuperClaw\servicehub\security_manager\_internal\models')
dst_root = Path(r'C:\Users\Trekker-PTL\Downloads\intel_models')

dst_root.mkdir(parents=True, exist_ok=True)

for sub in ['multilang-pii-ner-ov-int8', 'finance_embedding_ov-int8']:
    src = src_root / sub
    dst = dst_root / sub
    if not src.exists():
        print(f'MISSING: {src}')
        continue
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    n_files = sum(1 for _ in dst.rglob('*') if _.is_file())
    total = sum(f.stat().st_size for f in dst.rglob('*') if f.is_file())
    mb = total / (1024 * 1024)
    print(f'OK {sub}: {n_files} files, {mb:.1f} MB -> {dst}')

print()
print('--- dest tree ---')
for f in sorted(dst_root.rglob('*')):
    if f.is_file():
        print(f'  {f.stat().st_size:>12d}  {f.relative_to(dst_root)}')
