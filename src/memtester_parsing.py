# (c) OCP Test & Validation
# (c) Google LLC
# 
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

from sly import Lexer, Parser
from dataclasses import dataclass
from typing import Union, Callable
import re

@dataclass
class BadAddress:
    addr: int
    left_val: int
    right_val: int
    
@dataclass
class BadLine:
    addr: int
    
@dataclass
class OkResult:
    pass

@dataclass
class Test:
    name: str
    result: Union[OkResult, list[Union[BadAddress, BadLine]]]
    def passed(self) -> bool:
        return type(self.result) is OkResult
    
@dataclass
class Loop:
    index: int
    tests: list[Test]
    def failed_tests(self) -> list[Test]:
        return [t for t in self.tests if not t.passed()]

@dataclass
class MemtesterCallbacks:
    # Called when the next output line is read from memtester
    line_ready: Callable[[str], None] = lambda line: None

    # Called when a lexing or parsing error occurs
    parsing_error: Callable[[str], None] = lambda desc: None
    
    # Called when memtester version is read
    version_ready: Callable[[str, bool], None] = lambda version, is_known: None
    
    # Called when all loops finish
    run_ready: Callable[[int], None] = lambda failed_loop_count: None
    
    # Called when a loop of memory testing finish
    loop_ready: Callable[[Loop], None] = lambda loop: None
    
    # Called when a test within a loop finishes
    test_ready: Callable[[Test], None] = lambda test: None


# https://sly.readthedocs.io/en/latest/sly.html#writing-a-lexer
class MemtesterLexer(Lexer):
    tokens = { VER, OK, FLR, LOOP, TEST, HEX }

    TEST = (
        r"Stuck\sAddress|Random\sValue|Compare\s(XOR|SUB|MUL|DIV|OR|AND)|"
        r"Sequential\sIncrement|Solid\sBits|Block\sSequential|Checkerboard|"
        r"Bit\sSpread|Bit\sFlip|Walking\s(Ones|Zeroes)|(8|16)-bit\sWrites"
    )
    
    @_(r"Loop\s[0-9]+/[0-9]+:")
    def LOOP(self, t):
        m = re.search(r"([0-9]+)/[0-9]+", t.value)
        t.value = int(m.group(1)) if m else None
        return t
    
    @_(r"memtester\sversion\s[0-9]+\.[0-9]+\.[0-9]+.+")
    def VER(self, t):
        m = re.search(r"[0-9]+\.[0-9]+\.[0-9]+", t.value)
        t.value = m.group() if m else None
        return t
        
    @_(r"0x[0-9a-f]+")
    def HEX(self, t):
        t.value = int(t.value, 16)
        return t
    
    FLR = r"FAILURE"
    OK = r"ok"
    
    # String containing ignored characters (between tokens)
    ignore = " \n\t\b:\\/|!=.-"
    
    # Ignored sequences
    ignore_header = r"(Copyright|Licensed|pagesize|pagesizemask|want|got).+\n"
    ignore_status = r"(testing|setting)\s+[0-9]+"
    ignore_flr1_desc = r"possible\sbad\saddress\sline\sat\s(physical\saddress|offset)"
    ignore_flr3_desc = r"at\s(physical\saddress|offset)"
    ignore_skip = r"Skipping\sto\snext\stest\.\.\."
    ignore_done = r"Done\."
    
    def __init__(self, callbacks: MemtesterCallbacks):
        self._callbacks = callbacks
    
    def error(self, t):
        m = "Illegal character '{}' at line {}:{}".format(t.value[0], t.lineno, t.index)
        self._callbacks.parsing_error(m);
        self.index += 1


# https://sly.readthedocs.io/en/latest/sly.html#writing-a-parser
class MemtesterParser(Parser):
    # A list of supported memtester versions
    _known_versions = ["4.6.0", "4.5.1", "4.5.0"]

    # Get the token list from the lexer (required)
    tokens = MemtesterLexer.tokens

    def __init__(self, callbacks: MemtesterCallbacks):
        self._callbacks = callbacks

    @_("version loops")  
    def run(self, p):
        self._callbacks.run_ready(p.loops)

    @_("VER")  
    def version(self, p):
        self._callbacks.version_ready(p.VER, p.VER in self._known_versions)
        
    @_("loops loop", "loop")   
    def loops(self, p):
        self._callbacks.loop_ready(p.loop)
        
        # Count failed loops
        prev_failed_loops = p.loops if len(p) == 2 else 0
        curr_failed_loop = 1 if len(p.loop.failed_tests()) > 0 else 0
        return prev_failed_loops + curr_failed_loop
        
    @_("LOOP tests")   
    def loop(self, p):
        return Loop(p.LOOP, p.tests)
    
    @_("tests test", "test")     
    def tests(self, p):
        self._callbacks.test_ready(p.test)
        return ([] if len(p) == 1 else p.tests) + [p.test]
    
    @_("TEST OK")     
    def test(self, p):
        return Test(p.TEST, OkResult())
        
    @_("TEST failures")     
    def test(self, p):
        return Test(p.TEST, p.failures)

    @_("failures failure", "failure")
    def failures(self, p):
        return ([] if len(p) == 1 else p.failures) + [p.failure]
        
    @_("FLR HEX HEX HEX")
    def failure(self, p):
        return BadAddress(addr=p.HEX2, left_val=p.HEX0, right_val=p.HEX1)      
        
    @_("FLR HEX")
    def failure(self, p):
        return BadLine(addr=p.HEX) 
    
    def error(self, p):
        if p: # Do not report EOF as error
            m = "{} was unexpected".format(p)
            self._callbacks.parsing_error(m)

      
class MemtesterObserver:
    def __init__(self):
        self.callbacks = MemtesterCallbacks()
        
    def _token_generator(self, stdout_gen):
        lexer = MemtesterLexer(self.callbacks)
        for lineno, line in enumerate(stdout_gen, 1):
            self.callbacks.line_ready(line)
            for token in lexer.tokenize(line, lineno=lineno):
                yield token
                
    def run(self, stdout_gen):
        parser = MemtesterParser(self.callbacks)
        parser.parse(self._token_generator(stdout_gen))           
