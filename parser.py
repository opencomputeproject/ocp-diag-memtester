from sly import Lexer, Parser
from dataclasses import dataclass
from typing import Union
import re
import sys
import sh

# https://sly.readthedocs.io/en/latest/sly.html
class MemtesterLexer(Lexer):
    tokens = { VER, OK, FLR, LOOP, TEST, HEX }

    # String containing ignored characters (between tokens)
    ignore = " \t\b\n:\\/|!=.-"

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
    
    ignore_header = r"(Copyright|Licensed|pagesize|pagesizemask|want|got).+\n"
    ignore_status = r"(testing|setting)\s+[0-9]+"
    ignore_desc = r"(possible\sbad\saddress\sline\s)?at physical address"
    ignore_skip = r"Skipping\sto\snext\stest\.\.\."
    ignore_done = r"Done\."


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
class TestResult:
    name: str
    test_result: Union[OkResult, Union[BadAddress, BadLine]]
    
@dataclass
class LoopResult:
    index: int
    loop_results: list[TestResult]
    #def passed() -> bool: all([for r in loop_results.]) 


class MemtesterParser(Parser):
    # Get the token list from the lexer (required)
    tokens = MemtesterLexer.tokens
    debugfile = 'debug.txt'
    
    @_("VER loops")  
    def top_rule(self, p): pass
    
    @_("loops loop", "loop")   
    def loops(self, p): pass
        
    @_("LOOP tests")   
    def loop(self, p):
        r = LoopResult(p.LOOP, p.tests)
        print(r)
    
    @_("tests test")     
    def tests(self, p):
        return p.tests + [p.test]
        
    @_("test")
    def tests(self, p):
        return [p.test] 
    
    @_("TEST OK")     
    def test(self, p):
        return TestResult(p.TEST, OkResult())
        
    @_("TEST failures")     
    def test(self, p):
        return TestResult(p.TEST, p.failures)

    @_("failures failure")
    def failures(self, p):
        return p.failures + [p.failure]
        
    @_("failure")
    def failures(self, p):
        return [p.failure]
        
    @_("FLR HEX HEX HEX")
    def failure(self, p):
        return BadAddress(addr=p.HEX0, left_val=p.HEX1, right_val=p.HEX2)      
        
    @_("FLR HEX")
    def failure(self, p):
        return BadLine(addr=p.HEX) 
'''    
    def error(self, p):
       if not p:
            self.errok()
'''
def gen():
    lexer = MemtesterLexer()
    for l in sh.memtester("10k", 1000, _iter=True):
        #print(l)
        for t in lexer.tokenize(l):
            #print('type=%r, value=%r' % (t.type, t.value))
            yield t
            
def main():
    parser = MemtesterParser()
    parser.parse(gen())
        
                
if __name__ == '__main__':
    main()            
      
