#!/usr/bin/env python3
"""새 실험 폴더를 만들고 루트 README.md의 실험 목록 표에 한 줄을 기록한다.

폴더명(kebab-case slug)과 목적 문장은 호출하는 쪽(Claude)이 먼저 판단해서 넘겨준다.
이 스크립트는 그 이후의 기계적인 작업(폴더/README 생성, 표 수정, 검증)만 결정적으로 수행한다.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDER_ROW_RE = re.compile(r"^\|\s*-\s*\|\s*-\s*\|\s*-\s*\|$")


def get_repo_root():
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        print("ERROR: 현재 위치가 git 저장소가 아닙니다.", file=sys.stderr)
        sys.exit(1)
    return out.stdout.strip()


def find_table(lines):
    """'폴더'와 '주제' 컬럼을 포함한 첫 번째 마크다운 표를 찾아 (header_idx, data_start, data_end)를 반환."""
    header_idx = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("|") and "폴더" in s and "주제" in s:
            header_idx = i
            break
    if header_idx is None:
        return None
    sep_idx = header_idx + 1
    if sep_idx >= len(lines) or not lines[sep_idx].strip().startswith("|"):
        return None
    data_start = sep_idx + 1
    data_end = data_start
    while data_end < len(lines) and lines[data_end].strip().startswith("|"):
        data_end += 1
    return header_idx, data_start, data_end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True, help="kebab-case 폴더명 (예: react-server-components)")
    parser.add_argument("--topic", required=True, help="표에 기록할 실험 주제 (사람이 읽는 표시용 문구)")
    parser.add_argument("--purpose", required=True, help="실험 폴더 README.md에 들어갈 1~2문장 목적 설명")
    parser.add_argument("--date", help="기록할 날짜 (YYYY-MM-DD). 생략하면 오늘 날짜 사용")
    args = parser.parse_args()

    checklist = []

    is_kebab = bool(SLUG_RE.match(args.slug))
    checklist.append(("폴더명이 kebab-case 형식이다 (소문자/숫자, 하이픈 구분)", is_kebab))
    if not is_kebab:
        print(f"ERROR: '{args.slug}'는 유효한 kebab-case가 아닙니다.", file=sys.stderr)
        _print_checklist(checklist)
        sys.exit(1)

    root = get_repo_root()
    folder_path = os.path.join(root, args.slug)

    folder_exists = os.path.exists(folder_path)
    checklist.append(("동일한 이름의 폴더가 저장소 루트에 이미 존재하지 않는다", not folder_exists))
    if folder_exists:
        print(f"ERROR: 폴더가 이미 존재합니다: {folder_path}", file=sys.stderr)
        _print_checklist(checklist)
        sys.exit(1)

    readme_path = os.path.join(root, "README.md")
    if not os.path.exists(readme_path):
        print(f"ERROR: 루트 README.md를 찾을 수 없습니다: {readme_path}", file=sys.stderr)
        sys.exit(1)

    with open(readme_path, encoding="utf-8") as f:
        content = f.read()
    lines = content.splitlines()

    table = find_table(lines)
    checklist.append(("루트 README.md에서 실험 목록 표를 찾았다", table is not None))
    if table is None:
        print("ERROR: 루트 README.md에서 '폴더/주제/날짜' 컬럼을 가진 실험 목록 표를 찾지 못했습니다.", file=sys.stderr)
        _print_checklist(checklist)
        sys.exit(1)

    header_idx, data_start, data_end = table
    data_rows = lines[data_start:data_end]

    dup_row_idx = None
    for i, row in enumerate(data_rows):
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if cells and cells[0] == args.slug:
            dup_row_idx = i
            break
    checklist.append(("표에 동일한 폴더명을 가진 행이 없다 (중복 아님)", dup_row_idx is None))
    if dup_row_idx is not None:
        print(f"ERROR: 표에 이미 '{args.slug}' 행이 있습니다.", file=sys.stderr)
        _print_checklist(checklist)
        sys.exit(1)

    date_str = args.date or datetime.date.today().isoformat()
    date_ok = bool(DATE_RE.match(date_str))
    checklist.append(("날짜 형식이 YYYY-MM-DD이다", date_ok))
    if not date_ok:
        print(f"ERROR: 날짜 형식이 잘못되었습니다: {date_str}", file=sys.stderr)
        _print_checklist(checklist)
        sys.exit(1)

    new_row = f"| {args.slug} | {args.topic} | {date_str} |"

    placeholder_idx = None
    for i, row in enumerate(data_rows):
        if PLACEHOLDER_ROW_RE.match(row.strip()):
            placeholder_idx = i
            break

    if placeholder_idx is not None:
        data_rows[placeholder_idx] = new_row
        action = "placeholder 행을 대체"
    else:
        data_rows.append(new_row)
        action = "새 행을 추가"

    new_lines = lines[:data_start] + data_rows + lines[data_end:]
    new_content = "\n".join(new_lines)
    if content.endswith("\n"):
        new_content += "\n"

    os.makedirs(folder_path)
    exp_readme_path = os.path.join(folder_path, "README.md")
    with open(exp_readme_path, "w", encoding="utf-8") as f:
        f.write(f"# {args.topic}\n\n{args.purpose}\n")
    checklist.append(("실험 폴더와 README.md가 생성되었다", os.path.exists(exp_readme_path)))

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"OK: {folder_path} 생성")
    print(f"OK: {readme_path} 갱신 ({action})")
    _print_checklist(checklist)


def _print_checklist(checklist):
    print("\n자체 검증 체크리스트:")
    for text, passed in checklist:
        mark = "✅" if passed else "⚠️"
        print(f"  {mark} {text}")


if __name__ == "__main__":
    main()
