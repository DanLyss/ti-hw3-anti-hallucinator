grammar Regex;

root: expression EOF;
expression: concatenation ('|' concatenation)*;
concatenation: repetition+;
repetition: atom '*'*;
atom: SYMBOL | '(' expression ')';

SYMBOL: [a-zA-Z0-9];
WS: [ \t\r\n]+ -> skip;
