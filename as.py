# Copyright (c) 2026 Caleb Reeves
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# CPU Doc:
# Destinations:
# 0: Zero Register
# 1: Accumulator
# 2-61: General-Purpose Registers
# 62: Stack Pointer
# 63: Instruction Pointer
#
# ALU ops (Bit 31 enabled):
# Bit 30: ADD
# Bit 29: SUB
# Bit 28: MUL
# Bit 27: DIV
# Bit 26: SHL
# Bit 25: SHR
# Bit 24: NOT
#
# Memory/Register-to-Register ops (Bit 31 disabled, bit 30 enabled):
# Bit 29: MOVLO, use a SOURCE offset into memory
# Bit 28: MOVLI, use an IMMEDIATE offset into memory
# Bit 28 + 29: MOVLIO: use a SOURCE + IMMEDIATE offset into memory
# Bit 27: MOVR, move a register to another
# Bit 26: POP, pop a value from the stack into DEST
#
# Register-to-Memory ops (Bit 31 and bit 30 disabled):
# Bit 29: MOVSO, store SOURCE at a DEST offset into memory
# Bit 28: MOVSI, store SOURCE at IMMEDIATE offset into memory
# Bit 28 + 29: MOVSIO, store SOURCE at a IMMEDIATE + DEST offset into memory
# Bit 27: Reserved
# Bit 26: PUSH, put a value at the "top" of the stack
#
# This block does nothing for Register-to-Memory ops:
# Bit 14: Skip the next instruction if item in DEST is non-zero, negative
# Bit 13: Skip the next instruction if item in DEST is non-zero, positive
# Bit 12: Skip the next instruction if item in DEST is zero
#
# Bits 6-11: DEST register
# Bits 0-5: SOURCE register

import argparse
import sys

from enum import Flag, auto

class SymType(Flag):
    LITRL = auto() # Literal
    DRCTV = auto() # Directive
    MARKS = auto() # Punctuation mark
    SYMBL = auto() # Misc symbol
    RGSTR = auto() # Register

class File:
    def __init__(self, fname, fdata):
        self.fname = fname
        self.fdata = fdata

        self.fdata_len = len(self.fdata)

    def __getitem__(self, subscript):
        return self.fdata[subscript]

    def __len__(self):
        return len(self.fdata)

    def get_line_of_index(self, index: int) -> int:
        ret = 0
        for idx, char in enumerate(self.fdata, start = 0):
            if idx > index:
                break;
            if char == '\n':
                ret += 1
        else:
            raise IndexError("Invalid argument to `File.get_line_of_index(index)`: `index` was beyond length of `self.fdata`!")

        return ret

    def get_line_as_string(self, index: int):
        start_splice = index
        end_splice = index

        for s in range(index, -1, -1):
            if self.fdata[s] == '\n':
                start_splice += 1
                break
            start_splice -= 1

        for e in range(index, self.fdata_len):
            if self.fdata[e] == '\n':
                break

            end_splice += 1

        return self.fdata[start_splice : end_splice]

    def get_fname(self) -> str:
        return self.fname
    def get_data(self) -> str:
        return self.fdata

    def inject(self, data: str, index: int):
        self.fdata = self.fdata[0:index] + data + self.fdata[index:len(self.fdata)]

class Symbol:
    mark_symbols = ("\'", "\"", ":", ";", "{", "}", "(", ")", "[", "]", ",", "#")

    def __init__(self, str_repr, index, findex, data: File):
        self.str_repr = str_repr.lower()

        self.stype = SymType(0)
        self.value = 0

        self.index = index
        self.findex = findex

        self.src_data = data

        if self.str_repr in Symbol.mark_symbols:
            self.stype |= SymType.MARKS
        elif self.str_repr.startswith("%"):
            self.stype |= SymType.DRCTV
        elif self.str_repr.startswith("&"):
            self.stype |= SymType.RGSTR
        elif self.str_repr.startswith("$"):
            self.stype |= SymType.LITRL
        else:
            self.stype |= SymType.SYMBL

    def __str__(self):
        return f"<'{self.str_repr}', type {self.stype}>"

def raise_assembly_error(msg: str, index: int, data: File):
    line = data.get_line_of_index(index)
    line_str = data.get_line_as_string(index)

    final_message = "as.py: {0}, line {1}: {2} \n> {3}"

    print(final_message.format(data.get_fname(), line, msg, line_str), file=sys.stderr)

class Lexer:
    whitespace_tokens = (' ', '\n', '\t', '\r')

    def __init__(self):
        self.data_to_consume = []
        self.lexed_tokens = []

        self.index = 0
        self.findex = 0

        self.fline = 0
        self.fname = 0

        self.registered_macros = {"blank" : ""}

    def add_data(self, name: str, data: str):
        if not isinstance(data, str):
            raise TypeError("Invalid call to `Lexer.add_data(data)`: `data` must be of type `str`!")

        self.data_to_consume.append(File(name, data))

    def reset_index(self, index, findex):
        self.index = index
        self.findex = findex

        try:
            self.fline = self.data_to_consume[self.findex].get_line_of_index(index)
            self.fname = self.data_to_consume[self.findex].get_fname()
        except IndexError:
            if self.findex >= len(self.data_to_consume):
                return
            else:
                raise_assembly_error("Unexpected EOFin reset_index()", self.index - 1, cur_d)

    def __consume_next_wrapper(self) -> Symbol | None:
        entree = ""

        try:
            cur_d = self.data_to_consume[self.findex]
        except IndexError:
            return None

        while True:
            if self.index >= len(cur_d):
                if not entree:
                    self.reset_index(0, self.findex + 1)
                else:
                    sym = Symbol(entree, self.index - 1, self.findex, cur_d)
                    is_macro = entree in self.registered_macros
                    if is_macro:
                        cur_d.inject(self.registered_macros[entree], self.index)
                        entree = ""
                    else:
                        return sym

            if self.findex >= len(self.data_to_consume):
                if not entree:
                    return None
                else:
                    sym = Symbol(entree, self.index, self.findex - 1, cur_d)
                    is_macro = entree in self.registered_macros
                    if is_macro:
                        cur_d.inject(self.registered_macros[entree], self.index)
                        entree = ""
                    else:
                        return sym

            cur_d = self.data_to_consume[self.findex]
            cc = cur_d[self.index]

            if cc in Symbol.mark_symbols:
                if cc == "#":
                    while not (cur_d[self.index] == "\n"):
                        self.index += 1
                elif not entree:
                    self.index += 1
                    sym = Symbol(cc, self.index, self.findex, cur_d)
                    is_macro = entree in self.registered_macros
                    if is_macro:
                        cur_d.inject(self.registered_macros[entree], self.index)
                        entree = ""
                    else:
                        return sym
                else:
                    sym = Symbol(entree, self.index, self.findex, cur_d)
                    is_macro = entree in self.registered_macros
                    if is_macro:
                        cur_d.inject(self.registered_macros[entree], self.index)
                        entree = ""
                    else:
                        return sym
            elif cc in Lexer.whitespace_tokens:
                self.index += 1
                if entree:
                    sym = Symbol(entree, self.index, self.findex, cur_d)
                    is_macro = entree in self.registered_macros
                    if is_macro:
                        cur_d.inject(self.registered_macros[entree], self.index)
                        entree = ""
                    else:
                        return sym
            else:
                entree = entree + cc
                self.index += 1

    def consume_next_token(self) -> Symbol | None:
        ret = self.__consume_next_wrapper()

        if ret != None:
            if ret.stype & SymType.DRCTV:
                if ret.str_repr == f"%macro":
                    name = self.__consume_next_wrapper().str_repr
                    compound = ""
                    while True:
                        sym = self.__consume_next_wrapper()
                        if sym.str_repr == f"%endmacro": break
                        compound = compound + " " + sym.str_repr

                    self.registered_macros[name] = compound + " "
                elif ret.str_repr == f"%sect":
                    return ret
                else:
                    raise_assembly_error("Unexpected directive", ret.index, ret.src_data)

                ret = self.consume_next_token()

        return ret

class Opcode:
    def __init__(self, str_repr: str, opc: int, src: bool = True, dest: bool = True, immediate: bool = False):
        self.str_repr = str_repr
        self.opc = opc
        self.t_src = src
        self.t_dest = dest
        self.t_immediate = immediate

class SoeMachine:
    opcodes = {"add" : Opcode("add", 0xC0000000),
               "movr" : Opcode("movr", 0x48000000)}

    def get_opcode(sym: Symbol, source: Symbol | None = None, dest: Symbol | None = None, immediate: symbol | None = None) -> int | None:
        return SoeMachine.opcodes[sym.str_repr]

class Parser:
    def __init__(self, lexer: Lexer):
        self.symbol_table = {}
        self.lex = lexer

if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(description="Assembler for the Scratch Optimized Emulator")
    argument_parser.add_argument("files", nargs='+', help="the files to assemble and link")
    argument_parser.add_argument("-o", "--out", nargs=1, help="the output filename", default="rom.out", metavar="<file name>")
    argument_parser.add_argument("--dump", help="dump the resulting executable to stdout", action="store_true")
    argument_parser.add_argument("-v", "--verbose", help="enable verbose output", action="store_true")

    parsed = argument_parser.parse_args()
    verbose = parsed.verbose
    if verbose:
        print("Opening files for compilation...")

    lex = Lexer()

    for f in parsed.files:
        try:
            with open(f, "r") as fh:
                string = fh.read()
                lex.add_data(f, string)

            print(f"Added file {f}...")
        except FileNotFoundError:
            print(f"as.py: file \"{f}\" does not exist! Expect compilation errors!")

    while True:
        tok = lex.consume_next_token()
        if tok == None:
            break
        print(tok)
