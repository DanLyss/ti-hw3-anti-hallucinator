"""Reproducible metrics and comparison against exact automaton equivalence."""
import argparse
import json
from pathlib import Path

import yaml

from src.pipeline.runner import PROJECT_ROOT
from src.regex.evaluator import RESULTS
from src.testcases import TESTCASES

REPORT = PROJECT_ROOT / "reports/final_table_regex.md"


def _percentage(rows, key):
    return f"{100 * sum(r[key] is True for r in rows) / len(rows):.1f}" if rows else "—"


def render_report(rows, automata_rows, models, expected_runs=20):
    lines = ["# Домашка 8: регулярные выражения", "",
             "ANTLR4 → дерево разбора → ε-NFA Томпсона → удаление ε-переходов → DFA → точная эквивалентность с ground truth.", "",
             "Перед полной детерминизацией ищется слово-контрпример (включая пустое): "
             "расхождение с ground truth строго доказывает неэквивалентность. "
             "Совпадение на конечной выборке не считается доказательством: для положительного вердикта всё равно нужна точная проверка DFA.", "",
             "Проверяется весь сырой ответ. Markdown, пояснения и расширенный синтаксис не исправляются. "
             "Пробельные символы игнорируются грамматикой. Длина — число непробельных символов всего ответа, "
             "включая невалидные ответы; пустой ответ имеет длину 0. Проценты считаются от всех полученных ответов, "
             "а не только от валидных. Неоценённые из-за лимитов ответы показаны отдельно и не считаются доказанно корректными.", "",
             "Основные тесткейсы: basic, 4th-symbol, employer, intersection. personal добавлен для сопоставления с прошлым экспериментом.", "",
             "Все исходные ответы и параметры запросов хранятся в `data/raw_regex.tar.gz`. "
             "Для воспроизведения: `tar -xzf data/raw_regex.tar.gz`, затем команды из `README_hw8.md`.", "",
             "| Тесткейс | Модель | n / план | Средняя длина | Формат, % | Корректные, % | Не оценены |",
             "|---|---|---:|---:|---:|---:|---:|"]
    complete = True
    for case in [*TESTCASES, "Итого"]:
        for model in models:
            group = [r for r in rows if r["model"] == model and (case == "Итого" or r["testcase"] == case)]
            plan = expected_runs * (len(TESTCASES) if case == "Итого" else 1)
            complete &= len(group) == plan
            avg = f"{sum(r['length'] for r in group) / len(group):.2f}" if group else "—"
            unknown = sum(r["is_correct"] is None for r in group)
            lines.append(f"| {case} | {model} | {len(group)} / {plan} | {avg} | {_percentage(group, 'is_format_valid')} | {_percentage(group, 'is_correct')} | {unknown} |")
    lines += ["", "Выборка полная." if complete else "**Эксперимент не завершён. Пропущенные ответы не заменяются нулями; вывод о превосходстве пока предварительный.**", "",
              "## Сравнение с генерацией автоматов", "",
              "В обоих столбцах используется точная эквивалентность. Старую оценку по выборке строк не используем. "
              "Размеры выборок могут отличаться; сравнение описательное, без вывода о статистической значимости. "
              "Формат автоматов в прошлом эксперименте допускал Markdown, формат регулярок здесь строгий — это различие протоколов.", "",
              "| Тесткейс | Модель | n автоматов | Автоматы, % | n регулярок | Регулярки, % | Разность, п.п. |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for case in [*TESTCASES, "Итого"]:
        for model in models:
            rs = [r for r in rows if r["model"] == model and (case == "Итого" or r["testcase"] == case)]
            ats = [r for r in automata_rows if r["model"] == model and (case == "Итого" or r["testcase"] == case)]
            delta = "—"
            if rs and ats:
                delta = f"{100 * (sum(r['is_correct'] is True for r in rs) / len(rs) - sum(r.get('is_equivalent') is True for r in ats) / len(ats)):+.1f}"
            lines.append(f"| {case} | {model} | {len(ats)} | {_percentage(ats, 'is_equivalent')} | {len(rs)} | {_percentage(rs, 'is_correct')} | {delta} |")
    lines += ["", "## Наблюдения и интерпретация", ""]
    if not rows:
        lines += ["Реальных ответов на регулярки пока нет. Численные выводы не делаем."]
    for model in models:
        rs = [r for r in rows if r["model"] == model]
        ats = [r for r in automata_rows if r["model"] == model]
        if not rs:
            continue
        valid = sum(r["is_format_valid"] is True for r in rs)
        correct = sum(r["is_correct"] is True for r in rs)
        unknown = sum(r["is_correct"] is None for r in rs)
        lines += [f"- **{model}**: {len(rs)} ответов, {valid} валидных, {correct} эквивалентных; "
                  f"{valid - correct - sum(r['is_format_valid'] is True and r['is_correct'] is None for r in rs)} "
                  f"синтаксически допустимых выражений задают неверный язык; не оценены: {unknown}."]
        if ats:
            rp = 100 * correct / len(rs)
            ap = 100 * sum(r.get("is_equivalent") is True for r in ats) / len(ats)
            winner = "регулярки" if rp > ap else "автоматы" if ap > rp else "оба представления одинаково"
            lines += [f"  В этой выборке лучше: {winner} ({rp:.1f}% у регулярок против {ap:.1f}% у автоматов)."]
    witnessed = []
    seen = set()
    for row in rows:
        pair = row["model"], row["testcase"]
        if row.get("counterexample") is not None and pair not in seen:
            seen.add(pair)
            witnessed.append(row)
    if witnessed:
        lines += ["", "## Конкретные доказательства ошибок", "",
                  "По одному найденному контрпримеру на пару модель × тесткейс. "
                  "Это слова, на которых выражение и ground truth расходятся; ε означает пустое слово.", "",
                  "| Модель | Тесткейс | Контрпример | Принимается ground truth | Исходный ответ |",
                  "|---|---|---|---|---|"]
        for row in witnessed:
            word = row["counterexample"]
            expected = "да" if TESTCASES[row["testcase"]].ground_truth(word) else "нет"
            lines.append(f"| {row['model']} | {row['testcase']} | `{word or 'ε'}` | {expected} | `{row['raw_file_path']}` |")
    lines += ["", "Возможное объяснение различий: выражения компактно задают повторение и позицию с конца "
              "(4th-symbol), а автомату нужна явная таблица переходов. Для intersection нужно сначала "
              "исключить операцию пересечения, для employer — выразить запрет SPB0 без lookahead. "
              "Это гипотезы о причинах, а не измеренные свойства моделей. Короткая запись сама по себе не доказывает корректность.", "",
              "Лимиты: 10000 символов ответа, глубина скобок 100, до 20000 состояний при детерминизации. "
              "Сырые ответы и параметры запросов: `data/raw_regex/`; детальные вердикты: `data/results/runs_regex.jsonl`."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20, choices=range(20, 51))
    args = parser.parse_args()
    config = yaml.safe_load((PROJECT_ROOT / "config/models.yaml").read_text(encoding="utf-8"))
    models = [name for name, cfg in config["models"].items() if not cfg.get("only_2dfa")]
    def read(path):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
    REPORT.write_text(render_report(read(RESULTS), read(PROJECT_ROOT / "data/results/runs.jsonl"), models, args.runs), encoding="utf-8")


if __name__ == "__main__":
    main()
