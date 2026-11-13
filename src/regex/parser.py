from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from src.regex.generated.RegexLexer import RegexLexer
from src.regex.generated.RegexParser import RegexParser


class RegexFormatError(ValueError):
    pass


class _Errors(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # Lexer errors must fail too: ANTLR otherwise skips an illegal character.
        raise RegexFormatError(f"{line}:{column + 1}: {msg}")


def parse_regex(text: str, alphabet: tuple[str, ...]):
    """Parse the entire raw answer; no Markdown or unsupported regex syntax repair.

    Alphabet symbols are single ASCII letters/digits, as in all homework cases.
    Resource limits are reported separately from grammatical errors by the evaluator.
    """
    if not alphabet or len(set(alphabet)) != len(alphabet) or any(
        len(ch) != 1 or not ch.isascii() or not ch.isalnum() for ch in alphabet
    ):
        raise ValueError("alphabet must contain distinct ASCII letters/digits")
    if len(text) > 10000:
        raise RegexResourceError("answer exceeds 10000 characters")
    depth = 0
    for ch in text:
        depth += (ch == '(') - (ch == ')')
        if depth > 100:
            raise RegexResourceError("parenthesis depth exceeds 100")
    lexer = RegexLexer(InputStream(text))
    errors = _Errors()
    lexer.removeErrorListeners()
    lexer.addErrorListener(errors)
    tokens = CommonTokenStream(lexer)
    tokens.fill()
    for token in tokens.tokens:
        if token.type == RegexLexer.SYMBOL and token.text not in alphabet:
            raise RegexFormatError(f"symbol {token.text!r} is outside the alphabet")
    parser = RegexParser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(errors)
    return parser.root()


class RegexResourceError(RuntimeError):
    pass


def validate_regex(text: str, alphabet: tuple[str, ...]) -> bool:
    try:
        parse_regex(text, alphabet)
    except RegexFormatError:
        return False
    return True
