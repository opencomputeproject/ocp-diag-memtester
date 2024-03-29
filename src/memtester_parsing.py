# (c) OCP Test & Validation
# (c) Google LLC
# 
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

from sly import Lexer, Parser
from dataclasses import dataclass
from typing import Union, Callable, Iterator
import re

@dataclass
class BadAddress:
    """
    Contains bad address info reported by memtester.
    Currently reported by all tests except 'Stuck Address'.
    """

    addr: int
    """Address that is considered bad."""

    left_val: int
    """
    One of the values that were supposed to match
    when read from memory, but miscompared.
    """

    right_val: int
    """
    One of the values that were supposed to match
    when read from memory, but miscompared.
    """

@dataclass
class BadLine:
    """ 
    Contains bad address line info reported by memtester.
    Reported by the 'Stuck Address' test only.
    """

    addr: int
    """Address of the line that is considered bad."""

@dataclass
class OkResult:
    """A unit object for indicating a passing memory test."""    
    pass

@dataclass
class Test:
    """Contains info about one of the memory tests."""

    name: str
    """Test name as reported by memtester."""

    result: Union[OkResult, list[Union[BadAddress, BadLine]]]
    """Test result (pass or a list of bad addresses)."""

    def passed(self) -> bool:
        """Checks whether this test passed or not."""
        return type(self.result) is OkResult

@dataclass
class Loop:
    """Contains info about one iteration of memory testing."""

    index: int
    """Sequence number of this iteration."""

    tests: list[Test]
    """A list of tests that ran during this iteration."""
    
    def failed_tests(self) -> list[Test]:
        """Fetches failed tests of this iteration."""
        return [t for t in self.tests if not t.passed()]

@dataclass
class MemtesterCallbacks:
    """
    A collection of callbacks that are invoked
    when certain output fragments are read from memtester.
    """

    line_ready: Callable[[str], None] = lambda line: None
    """Called when the next output line is read from memtester."""
 
    parsing_error: Callable[[str], None] = lambda desc: None
    """Called when a lexing or parsing error occurs."""
    
    version_ready: Callable[[str, bool], None] = lambda version, is_known: None
    """Called when memtester version is read."""
    
    run_ready: Callable[[int], None] = lambda failed_loop_count: None
    """Called when all loops finish."""
    
    loop_ready: Callable[[Loop], None] = lambda loop: None
    """Called when a loop of memory testing finish."""
    
    test_ready: Callable[[Test], None] = lambda test: None
    """Called when a test within a loop finishes."""


# https://sly.readthedocs.io/en/latest/sly.html#writing-a-lexer
class MemtesterLexer(Lexer):
    tokens = { VER, OK, FAIL, LOOP, TEST, HEX }

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
    
    FAIL = r"FAILURE"
    OK = r"ok"
    
    # String containing ignored characters (between tokens)
    ignore = " \n\t\b:\\/|!=.-"
    
    # Ignored sequences
    ignore_header = r"^(Copyright|Licensed|pagesize|pagesizemask|want|got).+\n"
    ignore_status = r"(testing|setting)\s+[0-9]+"
    ignore_fail1_desc = r"possible\sbad\saddress\sline\sat\s(physical\saddress|offset)"
    ignore_fail3_desc = r"at\s(physical\saddress|offset)"
    ignore_skip = r"Skipping\sto\snext\stest\.\.\."
    ignore_done = r"Done\."
    
    def __init__(self, callbacks: MemtesterCallbacks):
        self._callbacks = callbacks
    
    def error(self, t):
        m = "Illegal character '{}' at line {}:{}".format(t.value[0], t.lineno, t.index)
        self._callbacks.parsing_error(m)
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
        
    @_("FAIL HEX HEX HEX")
    def failure(self, p):
        return BadAddress(addr=p.HEX2, left_val=p.HEX0, right_val=p.HEX1)      
        
    @_("FAIL HEX")
    def failure(self, p):
        return BadLine(addr=p.HEX) 
    
    def error(self, p):
        if p: # Do not report EOF as error
            m = "{} was unexpected".format(p)
            self._callbacks.parsing_error(m)

      
class MemtesterObserver:
    def __init__(self):
        self.callbacks = MemtesterCallbacks()
        
    def _token_generator(self, stdout: Iterator[str]):
        lexer = MemtesterLexer(self.callbacks)
        for lineno, line in enumerate(stdout, 1):
            self.callbacks.line_ready(line)
            for token in lexer.tokenize(line, lineno=lineno):
                yield token
                
    def run(self, stdout: Iterator[str]):
        parser = MemtesterParser(self.callbacks)
        parser.parse(self._token_generator(stdout))           
