import ocptv.output as tv
import sh
import re
from memtester_parsing import MemtesterObserver

def main():
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
                if failed_loop_count > 0:
                    step.add_diagnosis(tv.DiagnosisType.FAIL, verdict="memtester-failed")
                else:
                    step.add_diagnosis(tv.DiagnosisType.PASS, verdict="memtester-passed")
            observer.callbacks.run_ready = run_callback
            
            # Report parsing errors (supposed to only happen with unknown memtester versions)
            def parsing_error_callback(desc):
                step.add_error(symptom="memtester-parsing-error", message=desc)
            observer.callbacks.parsing_error = parsing_error_callback
            
            # Run memtester (finally!)
            try:
                # TODO: forward command line parameters to memtester
                observer.run(sh.memtester("100m", 3, _iter=True))
            except sh.CommandNotFound as e:
                step.add_log(tv.LogSeverity.ERROR, "Memtester not found: {}".format(e))
                step.add_diagnosis(tv.DiagnosisType.FAIL, verdict="memtester-not-found")
            
            bad_addrs.end()
               
if __name__ == '__main__':
    main()
