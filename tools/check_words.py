"""words.json 점검기. 배포하기 전에 실행하세요:  py tools/check_words.py
오류(✕)가 있으면 앱이 열리지 않거나 단어가 빠질 수 있으니 꼭 고치고, 주의(!)는 확인만 하면 됩니다."""
import json, sys, collections
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
P = Path(__file__).resolve().parent.parent / 'words.json'
CAT = {'school', 'daily', 'people', 'feel', 'action', 'describe', 'time', 'nature', 'society', 'func'}
POS = {'n', 'v', 'adj', 'adv', 'prep', 'conj', 'pron'}
errors, warns = [], []
err = errors.append
warn = warns.append

try:
    d = json.loads(P.read_text(encoding='utf-8'))
except json.JSONDecodeError as e:
    line = P.read_text(encoding='utf-8').splitlines()[e.lineno - 1] if e.lineno else ''
    print(f'✕ JSON 문법 오류: {e.lineno}번째 줄 {e.colno}번째 글자 근처 ({e.msg})')
    print('   ' + line[:160])
    print('   쉼표(,) 빠짐, 따옴표(") 짝, 마지막 항목 뒤 쉼표가 흔한 원인이에요.')
    sys.exit(1)

for k in ('version', 'textbook', 'groups', 'questions', 'dialogs', 'words'):
    if k not in d:
        err(f'맨 위에 "{k}" 항목이 없어요.')
words = d.get('words') or []
lessons = {l[0] for l in (d.get('textbook') or {}).get('lessons', [])}
groups = d.get('groups') or {}

ids = collections.Counter(w.get('id') for w in words)
for i, c in ids.items():
    if c > 1:
        err(f'단어 id "{i}"가 {c}번 나와요. id는 겹치면 안 돼요 (학습 기록이 id로 저장돼요).')
spell = collections.Counter((w.get('w') or '').lower() for w in words)
for wd, c in spell.items():
    if wd and c > 1:
        warn(f'"{wd}" 단어가 {c}번 있어요.')

for n, w in enumerate(words, 1):
    tag = f'{w.get("id", "?")} ({w.get("w", "?")})'
    if not w.get('id'):
        err(f'{n}번째 단어에 id가 없어요.')
    if not w.get('w'):
        err(f'{tag}: 영어(w)가 비어 있어요.')
    if not w.get('m'):
        err(f'{tag}: 뜻(m)이 비어 있어요. 뜻이 없으면 학습에 나오지 않아요.')
    if w.get('gr') not in (0, 1, 2, 3):
        err(f'{tag}: 학년(gr)은 1, 2, 3 중 하나(추가 단어는 0)여야 해요.')
    if w.get('c') and w['c'] not in CAT:
        warn(f'{tag}: 분류(c) "{w["c"]}"를 모르겠어요. {", ".join(sorted(CAT))} 중 하나로 써 주세요.')
    for p in (w.get('pos') or '').split('·'):
        if p and p not in POS:
            warn(f'{tag}: 품사(pos) "{p}"를 모르겠어요.')
    if 'ex' in w or 'ko' in w:
        err(f'{tag}: 예문은 "ex"/"ko"가 아니라 "exs": [{{"ex": "...", "ko": "..."}}] 목록에 넣어요.')
    exs = w.get('exs') or []
    if not isinstance(exs, list):
        err(f'{tag}: "exs"는 [ ]로 감싼 목록이어야 해요.')
        exs = []
    if len(exs) > 3:
        err(f'{tag}: 예문이 {len(exs)}개예요. 최대 3개까지만 보여요.')
    if not exs:
        warn(f'{tag}: 예문이 없어요. 문장 완성·따라 말하기에 나오지 않아요.')
    for i, x in enumerate(exs, 1):
        if not isinstance(x, dict) or not x.get('ex'):
            err(f'{tag}: 예문 {i}의 "ex"가 비어 있어요.')
        elif '[' not in x['ex']:
            warn(f'{tag}: 예문 {i}에 외울 단어를 [ ]로 감싸지 않았어요. 문장 완성 문제에 쓰이지 않아요.')
    for l in w.get('lss') or []:
        if l not in lessons:
            err(f'{tag}: 교과서 단원 "{l}"이 textbook.lessons에 없어요.')
    if w.get('g') and w['g'] not in groups:
        err(f'{tag}: 헷갈리는 짝 "{w["g"]}"이 groups에 없어요.')
    if not isinstance(w.get('n'), (int, float)):
        warn(f'{tag}: 순서 번호(n)가 없어요. 단어장 맨 앞에 나와요.')

dids = collections.Counter(x.get('id') for x in d.get('dialogs') or [])
for i, c in dids.items():
    if c > 1:
        err(f'대화 id "{i}"가 {c}번 나와요.')
for x in d.get('dialogs') or []:
    if not x.get('lines'):
        err(f'대화 {x.get("id")}: 대사(lines)가 없어요.')
    for l in x.get('lines') or []:
        if l.get('who') not in ('A', 'B') or not l.get('en'):
            err(f'대화 {x.get("id")}: 대사마다 who("A" 또는 "B")와 en이 필요해요.')
    if x.get('scene') and x['scene'] not in (d.get('scenes') or [x['scene']]):
        warn(f'대화 {x.get("id")}: 상황 "{x["scene"]}"이 scenes 목록에 없어요 (목록 끝에 따로 나와요).')
for i, q in enumerate(d.get('questions') or [], 1):
    for k in ('en', 'ko', 'st', 'ex'):
        if not q.get(k):
            err(f'질문 {i}번: "{k}"가 비어 있어요.')

for m in errors:
    print('✕', m)
for m in warns:
    print('!', m)
print(f'\n단어 {len(words)}개 · 대화 {len(d.get("dialogs") or [])}개 · 질문 {len(d.get("questions") or [])}개 · 오류 {len(errors)}개 · 주의 {len(warns)}개')
print('배포해도 돼요.' if not errors else '오류를 고친 뒤 다시 실행해 주세요.')
sys.exit(1 if errors else 0)
