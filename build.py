#!/usr/bin/env python3
"""The yes not yes: build a tap page from a small list of questions.

  python3 build.py examples/garden-shed.json --standalone -o my-page.html

Then open my-page.html in any browser, on a phone or a computer.

--mode copy   (the default) Nothing is stored anywhere. The person taps, presses
              Copy my answers, and pastes the text back into a chat with their AI.
--mode saved  For a page published as a Claude Artifact with a database
              (capabilities {"db": {"rules": [{"path": "", "read": "owner", "write": "owner"}]}}).
              Each answer is saved to the collection "rulings". Anywhere else, the
              page keeps the answers on the device and Copy my answers still works.
--standalone  Write a whole HTML document (what you want for a file you open or send).
              Without it the output is the page body that the Claude Artifact tool expects.
--previous    An earlier questions file, to catch a question reworded under its old id.

Four rules are checked so they cannot be skipped:
  1. every card says what it is about before the question     (stops the build)
  2. questions are asked the positive way round                (warning)
  3. an unfinished Not yes is never reported as "Not answered" (built into the page)
  4. a reworded question gets a new id                         (stops on a repeated id; warns with --previous)

It never writes over an existing file that differs. Give the new one a new name.
"""
import argparse, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'template.html')
SKELETON = ('<!doctype html><html lang="en-GB"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '</head><body>\n%s\n</body></html>\n')
BACKWARDS = re.compile(r"\b(stay off|stays off|kept off|keep off|left out|leave out|not be|shouldn't|should not|don't|do not)\b", re.I)


def check(cfg, previous):
    errs, warns, seen = [], [], set()
    qs = cfg.get('questions')
    if not isinstance(qs, list):
        sys.exit('"questions" must be a list')
    for n, q in enumerate(qs, 1):
        qid = str(q.get('id', '')).strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', qid):
            errs.append(f'question {n}: id must be letters, digits, - or _ (got {qid!r})')
        if qid in seen:
            errs.append(f'question {n}: id {qid!r} is used twice')
        seen.add(qid)
        about = q.get('about')
        about = [about] if isinstance(about, str) else (about or [])
        if not any((a if isinstance(a, str) else ' '.join(a)).strip() for a in about):
            errs.append(f'question {n} ({qid}): no "about". Every card needs its context, before the question.')
        for k in ('t', 'q', 'yes', 'alt'):
            if not str(q.get(k, '')).strip():
                errs.append(f'question {n} ({qid}): "{k}" is empty')
        if not str(q.get('alt2', '')).strip():
            warns.append(f'question {n} ({qid}): no "alt2". Each Not yes works best with a second alternative.')
        if BACKWARDS.search(str(q.get('q', ''))):
            warns.append(f'question {n} ({qid}): reads backwards? Ask it the positive way round ("Do you want these added?").')
        if qid in previous and previous[qid] != str(q.get('q', '')).strip():
            warns.append(f'question {n} ({qid}): the wording changed but the id did not. A reworded question gets a new id.')
    for w in warns:
        print('WARNING ·', w, file=sys.stderr)
    if errs:
        sys.exit('NOT BUILT\n' + '\n'.join('  · ' + e for e in errs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('questions', help='the questions file (see examples/garden-shed.json)')
    ap.add_argument('--mode', choices=['saved', 'copy'], help='overrides "mode" in the file; copy if neither says')
    ap.add_argument('--standalone', action='store_true', help='write a whole HTML document')
    ap.add_argument('--previous', help='an earlier questions file, to catch a reworded question keeping its old id')
    ap.add_argument('-o', '--out', required=True)
    a = ap.parse_args()

    with open(a.questions, encoding='utf-8') as f:
        cfg = json.load(f)
    cfg['mode'] = a.mode or cfg.get('mode') or 'copy'
    if cfg['mode'] not in ('saved', 'copy'):
        sys.exit('"mode" must be "saved" or "copy"')
    previous = {}
    if a.previous:
        with open(a.previous, encoding='utf-8') as f:
            previous = {str(q.get('id')): str(q.get('q', '')).strip() for q in json.load(f).get('questions', [])}
    check(cfg, previous)

    with open(TEMPLATE, encoding='utf-8') as f:
        page = f.read()
    blob = json.dumps(cfg, ensure_ascii=False).replace('</', '<\\/').replace('<!--', '<\\!--')
    page = page.replace('__TITLE__', html.escape(cfg.get('title') or 'The yes not yes'), 1).replace('__CFG__', blob, 1)
    if a.standalone:
        page = SKELETON % page

    if os.path.exists(a.out):
        with open(a.out, encoding='utf-8') as f:
            if f.read() == page:
                print('Unchanged:', a.out)
                return
        sys.exit(f'NOT WRITTEN: {a.out} exists and differs. Give the new page a new name.')
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'Built ({cfg["mode"]}{", standalone" if a.standalone else ""}, {len(cfg["questions"])} questions, {len(page):,} bytes): {a.out}')


if __name__ == '__main__':
    main()
