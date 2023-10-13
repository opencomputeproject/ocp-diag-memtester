from unittest import TestCase
from unittest.mock import MagicMock, call
from pathlib import Path
from src.memtester_parsing import MemtesterObserver, Test, Loop
from src.memtester_parsing import OkResult, BadAddress, BadLine


class TestMemtesterObserver(TestCase):
    def run_observer(self, filename):
        fn = Path(__file__).parent.joinpath("test_input", filename)
        with fn.open("r") as f:
            observer = MemtesterObserver()
            observer.callbacks = MagicMock()
            observer.run(f.readlines())
            return observer.callbacks
    
    def test_memtester_v4_6_0_with_faults(self):
        m = self.run_observer("mt-4.6.0-output-with-faults.txt")

        # If the last line of the output is reported,
        # most likely the other lines are reported too 
        m.line_ready.assert_called_with("Done.\n")

        # The output must not cause parsing errors
        m.parsing_error.assert_not_called()

        # Version must be correct
        m.version_ready.assert_called_once_with("4.6.0", True)
        
        # The output contains 3 memory testing loops
        m.run_ready.assert_called_once_with(3)

        # Make sure that at least one of the loops is parsed correctly
        # (testing all three loops is too lengthy)
        m.loop_ready.assert_any_call(Loop(index=2, tests=[
            Test("Stuck Address", [BadLine(0)]), 
            Test("Random Value", OkResult()), 
            Test("Compare XOR", OkResult()), 
            Test("Compare SUB", OkResult()), 
            Test("Compare MUL", OkResult()), 
            Test("Compare DIV", OkResult()), 
            Test("Compare OR", OkResult()), 
            Test("Compare AND", OkResult()), 
            Test("Sequential Increment", OkResult()), 
            Test("Solid Bits", OkResult()), 
            Test("Block Sequential", OkResult()), 
            Test("Checkerboard", OkResult()), 
            Test("Bit Spread", [
                BadAddress(43093696, 20, 20), 
                BadAddress(43093704, 18446744073709551595, 18446744073709551595),
                BadAddress(43093712, 20, 20),
                BadAddress(43093720, 18446744073709551595, 18446744073709551595), 
                BadAddress(43093728, 20, 20),
                BadAddress(43093736, 18446744073709551595, 18446744073709551595),
                BadAddress(43093744, 20, 20),
                BadAddress(43093752, 18446744073709551595, 18446744073709551595),
                BadAddress(43093760, 20, 20)
            ]),
            Test("Bit Flip", OkResult()), 
            Test("Walking Ones", OkResult()), 
            Test("Walking Zeroes", [
                BadAddress(12215744, 32768, 32768),
                BadAddress(12215752, 32768, 32768),
                BadAddress(12215760, 32768, 32768), 
                BadAddress(12215768, 32768, 32768), 
                BadAddress(12215776, 32768, 32768), 
                BadAddress(12215784, 32768, 32768), 
                BadAddress(12215792, 32768, 32768), 
                BadAddress(12215800, 32768, 32768), 
                BadAddress(12215808, 32768, 32768),
            ]),
            Test("8-bit Writes", OkResult()),
            Test("16-bit Writes", OkResult()),
        ]))

        # Pick a few tests with different results
        m.test_ready.assert_any_call(Test("Stuck Address", [BadLine(160)]))
        m.test_ready.assert_any_call(Test("Solid Bits", OkResult()))
        m.test_ready.assert_any_call(Test("Bit Flip", [
            BadAddress(21546928, 65536, 65536), 
            BadAddress(21546936, 18446744073709486079, 18446744073709486079), 
            BadAddress(21546944, 65536, 65536), 
            BadAddress(21546952, 18446744073709486079, 18446744073709486079), 
            BadAddress(21546960, 65536, 65536), 
            BadAddress(21546968, 18446744073709486079, 18446744073709486079), 
            BadAddress(21546976, 65536, 65536), 
            BadAddress(21546984, 18446744073709486079, 18446744073709486079), 
            BadAddress(21546992, 65536, 65536)
        ]))

    def test_bad_output(self): 
        m = self.run_observer("mt-4.6.0-bad-output.txt")
        m.parsing_error.assert_has_calls([
            call("Illegal character 'S' at line 102:80"),
            call("Illegal character 'T' at line 102:81"),
            call("Illegal character 'U' at line 102:82"),
            call("Illegal character 'F' at line 102:83"),
            call("Illegal character 'F' at line 102:84"),
        ])


if __name__ == '__main__':
    unittest.main()
