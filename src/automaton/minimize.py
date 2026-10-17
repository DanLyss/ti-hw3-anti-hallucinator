from collections import deque
from pathlib import Path

from src.automaton.determinize import determinize
from src.automaton.model import Automaton
from src.automaton.serializer import write_automaton
from src.automaton.validator import is_deterministic


def minimize(dfa: Automaton) -> Automaton:
    """Минимизация DFA алгоритмом Мура [1956] — ровно Алгоритм 1 из лекции:
    1) удалить недостижимые состояния;
    2) начальное разбиение R0 = Q \\ F, R1 = F;
    3) пока какой-то класс можно разделить: для каждого класса R и каждого символа a
       смотрим, в какие классы ведут переходы по a из состояний R; если в разные —
       заменяем R на классы R'_1..R'_k, переходы из каждого R'_j по a идут в один класс.
    Выход: DFA на классах, старт [q0], финальные — классы из F, δ'(R, a) = [δ(r, a)].

    В лекции δ — всюду определённая функция, а модели часто выдают частичные DFA, поэтому
    после шага 1 недостающие переходы ведём в sink-состояние. Результат — полный минимальный
    DFA (с sink, если он нужен языку); состояния пронумерованы BFS-ом от старта, символы по
    возрастанию, так что у эквивалентных DFA результат совпадает буквально."""
    if not is_deterministic(dfa):
        raise ValueError("minimize() принимает только DFA — NFA сначала determinize()")

    reachable, delta = _reachable_complete(dfa)
    finals = {q for q in reachable if q in dfa.finals}

    classes = [cls for cls in (reachable - finals, finals) if cls]
    class_of = {q: i for i, cls in enumerate(classes) for q in cls}

    changed = True
    while changed:
        changed = False
        for index in range(len(classes)):
            for symbol in range(dfa.m):
                groups: dict[int, set] = {}
                for q in classes[index]:
                    groups.setdefault(class_of[delta[(q, symbol)]], set()).add(q)
                if len(groups) > 1:
                    first, *rest = groups.values()
                    classes[index] = first  # R'_1 занимает место R, остальные — новые классы
                    for part in rest:
                        classes.append(part)
                        for q in part:
                            class_of[q] = len(classes) - 1
                    changed = True
                    break  # R больше нет — дальше по следующему классу

    return _quotient(dfa, classes, class_of, delta, finals)


def minimize_to_file(automaton: Automaton, path: Path) -> Automaton:
    """Минимизирует и пишет результат в файл в формате из домашки. NFA сначала
    детерминизируется (минимизировать по Муру можно только DFA)."""
    minimal = minimize(determinize(automaton))
    write_automaton(minimal, path)
    return minimal


_SINK = "sink"


def _reachable_complete(dfa: Automaton) -> tuple[set, dict]:
    """Шаг 1 (только достижимые от старта) + достройка до полного DFA: отсутствующие
    переходы ведут в одно sink-состояние, которое появляется, только если оно нужно."""
    (start,) = dfa.starts
    reachable = {start}
    queue = deque([start])
    delta: dict = {}
    while queue:
        q = queue.popleft()
        for symbol in range(dfa.m):
            targets = dfa.transitions.get((q, symbol)) if q != _SINK else None
            target = next(iter(targets)) if targets else _SINK
            delta[(q, symbol)] = target
            if target not in reachable:
                reachable.add(target)
                queue.append(target)
    return reachable, delta


def _quotient(dfa: Automaton, classes: list[set], class_of: dict, delta: dict, finals: set) -> Automaton:
    """Автомат на классах эквивалентности, нумерация классов — BFS от [q0]."""
    (start,) = dfa.starts
    index_of = {class_of[start]: 0}
    queue = deque([class_of[start]])
    transitions: dict[tuple[int, int], set[int]] = {}
    while queue:
        cls = queue.popleft()
        representative = next(iter(classes[cls]))
        for symbol in range(dfa.m):
            target = class_of[delta[(representative, symbol)]]
            if target not in index_of:
                index_of[target] = len(index_of)
                queue.append(target)
            transitions[(index_of[cls], symbol)] = {index_of[target]}

    return Automaton(
        n=len(index_of),
        m=dfa.m,
        starts={0},
        finals={index_of[cls] for cls in index_of if classes[cls] <= finals},
        transitions=transitions,
    )
