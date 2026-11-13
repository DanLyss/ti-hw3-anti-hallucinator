from collections import defaultdict
from dataclasses import dataclass, field

from src.automaton.model import Automaton
from src.regex.generated.RegexVisitor import RegexVisitor
from src.regex.parser import parse_regex


@dataclass
class EpsilonNFA:
    n: int
    m: int
    start: int
    final: int
    transitions: dict = field(default_factory=lambda: defaultdict(set))

    def without_epsilon(self) -> Automaton:
        """δ'(q,a)=ε-closure(δ(ε-closure(q),a)); retain ε-acceptance."""
        closures = []
        for q in range(self.n):
            reached, stack = {q}, [q]
            while stack:
                for target in self.transitions.get((stack.pop(), None), ()):
                    if target not in reached:
                        reached.add(target)
                        stack.append(target)
            closures.append(reached)
        transitions = {}
        for q, closure in enumerate(closures):
            for symbol in range(self.m):
                targets = {
                    end for state in closure
                    for target in self.transitions.get((state, symbol), ())
                    for end in closures[target]
                }
                if targets:
                    transitions[q, symbol] = targets
        return Automaton(self.n, self.m, {self.start}, {
            q for q, closure in enumerate(closures) if self.final in closure
        }, transitions)


class ThompsonVisitor(RegexVisitor):
    """Each visit returns the (entry, exit) pair of a Thompson fragment."""
    def __init__(self, alphabet):
        self.symbols = {ch: i for i, ch in enumerate(alphabet)}
        self.n = 0
        self.transitions = defaultdict(set)

    def state(self):
        q = self.n
        self.n += 1
        return q

    def edge(self, source, symbol, target):
        self.transitions[source, symbol].add(target)

    def visitRoot(self, ctx):
        return self.visit(ctx.expression())

    def visitExpression(self, ctx):
        fragments = [self.visit(child) for child in ctx.concatenation()]
        if len(fragments) == 1:
            return fragments[0]
        start, end = self.state(), self.state()
        for left, right in fragments:
            self.edge(start, None, left)
            self.edge(right, None, end)
        return start, end

    def visitConcatenation(self, ctx):
        fragments = [self.visit(child) for child in ctx.repetition()]
        for (_, right), (left, _) in zip(fragments, fragments[1:]):
            self.edge(right, None, left)
        return fragments[0][0], fragments[-1][1]

    def visitRepetition(self, ctx):
        left, right = self.visit(ctx.atom())
        for _ in range(ctx.getChildCount() - 1):
            start, end = self.state(), self.state()
            for source, target in [(start, left), (start, end), (right, left), (right, end)]:
                self.edge(source, None, target)
            left, right = start, end
        return left, right

    def visitAtom(self, ctx):
        if ctx.SYMBOL() is None:
            return self.visit(ctx.expression())
        start, end = self.state(), self.state()
        self.edge(start, self.symbols[ctx.SYMBOL().getText()], end)
        return start, end


def from_tree(tree, alphabet) -> EpsilonNFA:
    visitor = ThompsonVisitor(alphabet)
    start, final = visitor.visit(tree)
    return EpsilonNFA(visitor.n, len(alphabet), start, final, visitor.transitions)


def thompson(text: str, alphabet: tuple[str, ...]) -> EpsilonNFA:
    return from_tree(parse_regex(text, alphabet), alphabet)
