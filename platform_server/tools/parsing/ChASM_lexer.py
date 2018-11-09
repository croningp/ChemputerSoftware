# coding=utf-8
# !/usr/bin/env python
"""
:mod:"ChASM_lexer" -- PLY based lexer for ChASM files
===================================

.. module:: ChASM_lexer
   :platform: Windows, Unix
   :synopsis: PLY based lexer for ChASM files
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

Contains tokens and functions for lexical analysis of the ChASM input file.

For style guide used see http://xkcd.com/1513/
"""

# system imports
import ply.lex as lex
import logging

lex_logger = logging.getLogger("main_logger.lex_logger")

# define token list
tokens = [
    "IGNORED",
    "PARENTHESIS_OPEN",
    "PARENTHESIS_CLOSED",
    "CURLY_BRACE_OPEN",
    "CURLY_BRACE_CLOSED",
    "SEMICOLON",
    "PLUS",
    "MINUS",
    "MULTIPLY",
    "DIVIDE",
    "EQUAL_SIGN",
    "BOOL_EQUAL",
    "BOOL_NOT_EQUAL",
    "BOOL_GREATER",
    "BOOL_LESSER",
    "BOOL_GREATER_QUAL",
    "BOOL_LESSER_EQUAL",
    "PS_TOK",
    "OPCODE",
    "WORD",
    "NUMBER",
    "RESERVED"
]

reserved = {
    "FOR": "FOR",
    "DEF": "DEF",
    "MAIN": "MAIN"
}

# unify tokens and reserved words
tokens += list(reserved.values())

# list the token patterns
t_PARENTHESIS_OPEN = r"\("
t_PARENTHESIS_CLOSED = r"\)"
t_CURLY_BRACE_OPEN = r"\{"
t_CURLY_BRACE_CLOSED = r"\}"
t_SEMICOLON = r"\;"
t_PLUS = r"\+"
t_MINUS = r"\-"
t_MULTIPLY = r"\*"
t_DIVIDE = r"\/"
t_EQUAL_SIGN = r"="  # this works because it looks for the longer boolean operators first
t_BOOL_EQUAL = r"=="
t_BOOL_NOT_EQUAL = r"!="
t_BOOL_GREATER = r">"
t_BOOL_LESSER = r"<"
t_BOOL_GREATER_QUAL = r"<="
t_BOOL_LESSER_EQUAL = r">="
t_WORD = r"\b[\w]+\b"  # upper and lower case letters, numbers and underscores. Essentially anything else.
t_NUMBER = r"\-{0,1}\d+\.*\d*\b"  # int or float, with optional minus, with a non-word character at the end


# special action tokens
def t_IGNORED(t):
    r"\#.*\n|\#.*\Z|\s+|,"
    # comments, whitespace, and for now commas, are just ignored first.
    for i in range(t.value.count("\n")):
        t.lexer.lineno += 1


def t_PS_TOK(t):
    r"\b[PS]\b"
    # "P" and "S" labels are consumed next, to not confuse them with opcodes
    return t


def t_OPCODE(t):
    r"\b[A-Z_]+\b"
    # if it's all caps, and if it's a reserved word, it's a reserved word. Else it's an opcode.
    t.type = reserved.get(t.value, "OPCODE")
    return t


def t_error(t):
    lex_logger.error("Illegal character {0}".format(t.value[0]))
    t.lexer.skip(1)

# build lexer
lexer = lex.lex(debug=False)

if __name__ == "__main__":
    with open("E:\\git_repositories\\Chempiler\\experiments\\chemputer_rig_3.chasm") as input_file:
        input_string = input_file.read()
        lexer.input(input_string)
        while True:
            tok = lexer.token()
            if not tok:
                break
            print(tok)
