# coding=utf-8
# !/usr/bin/env python
"""
:mod:"ChASM_parser" -- PLY based parser for ChASM files
===================================

.. module:: ChASM_parser
   :platform: Windows, Unix
   :synopsis: PLY based parser for ChASM files
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2017 The Cronin Group, University of Glasgow

Contains grammar and functions for parsing a ChASM input file. Essentially, all input is ultimately converted
into a list of instructions consisting of a P or S for Parallel or Sequential, an opcode as documented in the
COMMAND_LIST, and parameters.

For style guide used see http://xkcd.com/1513/
"""

import inspect
import logging
import os
import sys
from copy import deepcopy

# system imports
import ply.yacc as yacc

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(HERE, '..'))

from tools.parsing.ChASM_lexer import tokens

yacc_logger = logging.getLogger("main_logger.yacc_logger")
error_logger = logging.getLogger()
error_logger.setLevel(logging.CRITICAL)  # ignoring all unnecessary yacc output

variables = {}
functions = {}


def p_script(p):
    """script : assign_var
              | assign_func
              | main
              | script assign_var
              | script assign_func
              | script main
    """
    if p[0] is None:  # initialise as list
        p[0] = []
    if (len(p) == 2) and type(p[1]) is list:
        p[0] = p[1]
    else:
        try:
            p[0] = p[1] + p[2]
        except(TypeError, IndexError):
            pass


def p_main(p):
    """main : MAIN CURLY_BRACE_OPEN body CURLY_BRACE_CLOSED"""
    p[0] = p[3]


def p_body(p):
    """body : instruction
            | function
            | for_loop
            | body instruction
            | body function
            | body for_loop
    """
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2]


def p_instruction(p):
    """instruction : PS_TOK OPCODE PARENTHESIS_OPEN arg_list PARENTHESIS_CLOSED SEMICOLON
                   | PS_TOK OPCODE PARENTHESIS_OPEN PARENTHESIS_CLOSED SEMICOLON
    """
    if len(p) == 7:  # with arguments
        p[0] = [[p[1], p[2]] + p[4]]
    elif len(p) == 6:  # no arguments
        p[0] = [[p[1], p[2]]]


def p_arg_list(p):
    """arg_list : arg_list arg
                | arg
    """
    if len(p) == 1:  # empty case
        p[0] = []
    elif len(p) == 2:  # single argument
        p[0] = [p[1]]
    else:  # list plus argument
        p[0] = p[1] + [p[2]]


def p_arg(p):
    """arg : NUMBER
           | variable
    """
    p[0] = p[1]


def p_assign_var(p):
    """assign_var : DEF variable EQUAL_SIGN variable SEMICOLON
                  | DEF variable EQUAL_SIGN NUMBER SEMICOLON
    """
    variables[p[2]] = p[4]


def p_variable(p):
    """variable : WORD"""
    p[0] = variables.get(p[1], p[1])  # get() returns the value of WORD if it's listed in the dict, else it returns WORD


def p_assign_func(p):
    """assign_func : DEF variable PARENTHESIS_OPEN arg_list PARENTHESIS_CLOSED CURLY_BRACE_OPEN body CURLY_BRACE_CLOSED
                   | DEF variable PARENTHESIS_OPEN PARENTHESIS_CLOSED CURLY_BRACE_OPEN body CURLY_BRACE_CLOSED
    """
    func_name = p[2]
    if len(p) == 9:  # with arguments
        arg_list = p[4]
        body = p[7]
    elif len(p) == 8:  # no arguments
        arg_list = []
        body = p[6]
    else:  # in case some dumb fuck defines an empty function
        arg_list = []
        body = []
    functions[func_name] = (arg_list, body)


def p_function(p):
    """function : variable PARENTHESIS_OPEN arg_list PARENTHESIS_CLOSED SEMICOLON
                | variable PARENTHESIS_OPEN PARENTHESIS_CLOSED SEMICOLON
    """
    func_name = p[1]
    if len(p) == 6:
        arg_list = p[3]
    else:
        arg_list = []

    # those operations require a deep copy, otherwise it messes with the original function
    body = deepcopy(functions[func_name][1])
    required_args = deepcopy(functions[func_name][0])

    if len(arg_list) != len(required_args):
        p[0] = []

    arg_mapper = dict(zip(required_args, arg_list))

    for instruction in body:
        for position, string in enumerate(instruction):  # Quote stackoverflow: "This is a bad and very un-pythonic solution. Consider using list comprehension." Answer: fuck you.
            if string in required_args:
                instruction[position] = arg_mapper[string]

    p[0] = body


def p_for_loop(p):
    """for_loop : FOR PARENTHESIS_OPEN NUMBER PARENTHESIS_CLOSED CURLY_BRACE_OPEN body CURLY_BRACE_CLOSED"""
    iterator = int(p[3])
    body = p[6]
    return_list = []
    for i in range(iterator):
        return_list += body
    p[0] = return_list


def p_error(p):
    yacc_logger.error("Syntax error in line {0}: offending token: {1}".format(p.lineno, p))
    raise Exception("Syntax error in line {0}: offending token: {1}".format(p.lineno, p))

parser = yacc.yacc(errorlog=error_logger, debug=False)

if __name__ == "__main__":
    with open("E:\\git_repositories\\Chempiler\\experiments\\chemputer_rig_3.chasm") as input_file:
        input_string = input_file.read()
        command_queue = parser.parse(input=input_string, debug=True)
        while command_queue:
            cmd = command_queue.pop(0)
            print(cmd)
