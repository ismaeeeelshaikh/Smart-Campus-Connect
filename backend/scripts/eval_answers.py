"""Answer-quality check against a RUNNING backend (real knowledge base + real LLM).

Asks every question in eval_questions.json through the guest endpoint and checks that the answer
contains an expected fact, is in the right script (for language questions) and, where marked, has
a source link. Run it after website syncs or prompt/model changes to catch regressions.

    python -m scripts.eval_answers                       # backend on http://127.0.0.1:8000
    python -m scripts.eval_answers --delay 0             # no pause (paid / self-hosted LLM)
    python -m scripts.eval_answers --url http://host:8000 --min-pass 0.9

The default 20-second pause keeps Groq's free tier (~8,000 tokens/minute) from rate-limiting.
Exit code 1 if the pass rate is below --min-pass.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

QUESTIONS = Path(__file__).with_name("eval_questions.json")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def ask(url: str, question: str) -> dict:
    request = urllib.request.Request(f"{url.rstrip('/')}/guest/chat", data=json.dumps({"question": question}).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def check(item: dict, result: dict) -> list[str]:
    """Problems with one answer (empty list = pass)."""
    answer = result["answer"]

    def norm(s: str) -> str:  # models sometimes use non-breaking or narrow spaces
        return " ".join(s.lower().replace(",", "").split())

    flat = norm(answer)
    problems = []
    if not any(norm(e) in flat for e in item["expect_any"]):
        problems.append(f"expected one of {item['expect_any']}")
    if item.get("script") == "devanagari" and not DEVANAGARI.search(answer):
        problems.append("answer should be in Devanagari")
    if item.get("script") == "latin" and DEVANAGARI.search(answer):
        problems.append("Hinglish question answered in Devanagari")
    if item.get("source") and not result.get("sources"):
        problems.append("no source link")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--delay", type=float, default=20, help="seconds between questions (default 20)")
    parser.add_argument("--min-pass", type=float, default=0.85, help="minimum pass rate (default 0.85)")
    parser.add_argument("--only", help="run only questions containing this text (case-insensitive)")
    args = parser.parse_args()

    items = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    if args.only:
        items = [i for i in items if args.only.lower() in i["q"].lower()]
    passed = 0
    for i, item in enumerate(items, 1):
        if i > 1:
            time.sleep(args.delay)
        try:
            result = ask(args.url, item["q"])
            problems = check(item, result)
        except urllib.error.HTTPError as e:
            result, problems = {"answer": "", "sources": []}, [f"HTTP {e.code}: {e.read().decode()[:120]}"]
        except OSError as e:
            print(f"Can't reach the backend at {args.url}: {e}")
            sys.exit(2)
        ok = not problems
        passed += ok
        answer = " ".join(result["answer"].split())
        print(f"{'PASS' if ok else 'FAIL'} [{i:2}/{len(items)}] {item['q']}")
        print(f"      {answer[:160]}{'…' if len(answer) > 160 else ''}")
        if problems:
            print(f"      problems: {'; '.join(problems)}")
    rate = passed / len(items)
    print(f"\n{passed}/{len(items)} passed ({rate:.0%}), required {args.min_pass:.0%}")
    sys.exit(0 if rate >= args.min_pass else 1)


if __name__ == "__main__":
    main()
