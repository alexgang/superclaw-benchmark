import httpx, json
b = {"model":"local-model","messages":[{"role":"user","content":"Reply with only the word: ok"}],"max_tokens":20,"stream":False}
r = httpx.post('http://127.0.0.1:18321/v1/chat/completions', json=b, timeout=60)
print('status:', r.status_code)
print('body:', r.text[:500])

b2 = {"model":"cloud-model","messages":[{"role":"user","content":"Reply with only the word: cloud-ok"}],"max_tokens":20,"stream":False}
r2 = httpx.post('http://127.0.0.1:18321/v1/chat/completions', json=b2, timeout=60)
print('\ncloud-model status:', r2.status_code)
print('body:', r2.text[:500])

b3 = {"model":"auto","messages":[{"role":"user","content":"Reply with only the word: auto-ok"}],"max_tokens":20,"stream":False}
r3 = httpx.post('http://127.0.0.1:18321/v1/chat/completions', json=b3, timeout=60)
print('\nauto status:', r3.status_code)
print('body:', r3.text[:500])