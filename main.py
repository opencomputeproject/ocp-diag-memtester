import ocptv.output as tv
import argparse
import sh
import re
from memtester_parsing import MemtesterObserver
from contextlib import redirect_stderr

def main():
    parser = argparse.ArgumentParser(description="OCP-compliant memtester wrapper.")
    parser.add_argument("--mt_path", default="memtester",
        help="Path to memtester executable")
    parser.add_argument("--mt_args", default="",
        help="Memtester arguments packed into a string. See `man memtester` for more detail")
    args = parser.parse_args()

    run = tv.TestRun(name="memtester", version="1.0")
    dut = tv.Dut(id=sh.hostid().strip(), name=sh.hostname().strip())
    
    with run.scope(dut=dut):
        with (step := run.add_step("run-memtester")).scope():
            observer = MemtesterObserver()
            bad_addrs = step.start_measurement_series(name="bad_addrs")
            
            # Check if a supported version of memtester is installed in the system
            def version_callback(version, is_known):
                step.add_log(tv.LogSeverity.INFO, "Memtester v{} was found".format(version))
                if (not is_known):
                    m = "This version of memtester was not tested. Expect parsing errors"
                    step.add_log(tv.LogSeverity.WARNING, m)
            observer.callbacks.version = version_callback
            
            # Report loop results
            def loop_callback(loop):
                tests = loop.failed_tests()
                if (len(tests) == 0):
                    m = "Loop #{} finished with success".format(loop.index)
                    step.add_log(tv.LogSeverity.INFO, m)
                else:
                    # Log failed tests
                    names = ", ".join([t.name for t in tests])
                    m = "Loop #{} failed {} tests: {}".format(loop.index, len(tests), names)
                    step.add_error(symptom="loop-failure", message=m)
                    
                    # Record failed addresses
                    for test in tests:
                        for r in test.result:
                            bad_addrs.add_measurement(value=r.addr)
            observer.callbacks.loop_ready = loop_callback
            
            # Report individual tests to make long runs more responsive
            def test_callback(test):
                if test.passed():
                    step.add_log(tv.LogSeverity.INFO, "Test '{}' passed".format(test.name))
                else:
                    step.add_log(tv.LogSeverity.ERROR, "Test '{}' failed".format(test.name))
            observer.callbacks.test_ready = test_callback
            
            # Report diagnosis
            def run_callback(failed_loop_count):
                if failed_loop_count == 0:
                    step.add_diagnosis(tv.DiagnosisType.PASS, verdict="memtester-passed")
                else:
                    step.add_diagnosis(tv.DiagnosisType.FAIL, verdict="memtester-failed")
            observer.callbacks.run_ready = run_callback
            
            # Report parsing errors (supposed to only happen with unknown memtester versions)
            def parsing_error_callback(desc):
                step.add_error(symptom="memtester-parsing-error", message=desc)
            observer.callbacks.parsing_error = parsing_error_callback
            
            # Run memtester (finally!)
            try:  
                mt_cmd = sh.Command(args.mt_path)
                mt_args = args.mt_args.split(" ")
                with redirect_stderr(None): # Magic to silence sh lib
                    # For _ok_code see https://linux.die.net/man/8/memtester
                    observer.run(mt_cmd(*mt_args, _iter=True, _ok_code=(0, 2, 4)))
            except sh.CommandNotFound as e:
                m = "Memtester not found: {}".format(e)
                step.add_error(symptom="memtester-not-found", message=m)
            except sh.ErrorReturnCode as e:
                m = "Memtester returned code {}".format(e.exit_code)
                step.add_error(symptom="memtester-error-code", message=m)
                step.add_log(tv.LogSeverity.ERROR, "Memtester error description: {}".format(e))
            
            bad_addrs.end()
               
if __name__ == '__main__':
    main()
