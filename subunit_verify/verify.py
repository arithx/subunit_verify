#!/usr/bin/python
#

import collections
import datetime
import io
import sys
import traceback
from xml.sax import saxutils

import subunit
import testtools


class VerifyOutput(testtools.TestResult):
    def __init__(self, test_file='test_list'):
        super(VerifyOutput, self).__init__()
        self.test_list = {line: {"status": "Not Found", "message": None}
                          for line in open(
                            test_file).read().split("\n") if line}

    def addSuccess(self, test):
        output = test.shortDescription() or test.id()
        if output in self.test_list:
            self.test_list[output]["status"] = "Pass"

    def addSkip(self, test, err):
        output = test.shortDescription() or test.id()
        if output in self.test_list:
            self.test_list[output]["status"] = "Skip"
            self.test_list[output]["message"] = self.formatErr(err)

    def addError(self, test, err):
        output = test.shortDescription() or test.id()
        if output in self.test_list:
            self.test_list[output]["status"] = "Error"
            self.test_list[output]["message"] = self.formatErr(err)

    def addFailure(self, test, err):
        output = test.shortDescription() or test.id()
        if output in self.test_list:
            self.test_list[output]["status"] = "Fail"
            self.test_list[output]["message"] = self.formatErr(err)

    def formatErr(self, err):
        exctype, value, tb = err
        return ''.join(traceback.format_exception(exctype, value, tb))

    def stopTestRun(self):
        super(VerifyOutput, self).stopTestRun()

    def startTestRun(self):
        super(VerifyOutput, self).startTestRun()


class FileAccumulator(testtools.StreamResult):

    def __init__(self):
        super(FileAccumulator, self).__init__()
        self.route_codes = collections.defaultdict(io.BytesIO)

    def status(self, **kwargs):
        if kwargs.get('file_name') != 'stdout':
            return
        file_bytes = kwargs.get('file_bytes')
        if not file_bytes:
            return
        route_code = kwargs.get('route_code')
        stream = self.route_codes[route_code]
        stream.write(file_bytes)


def main():
    if len(sys.argv) < 2:
        print("Need at least one argument: path to subunit log.")
        exit(1)
    subunit_file = sys.argv[1]
    if len(sys.argv) > 2:
        test_file = sys.argv[2]
    else:
        test_file = 'test_list'

    verify_result = VerifyOutput(test_file)
    stream = open(subunit_file, 'rb')
    suite = subunit.ByteStreamToStreamResult(stream, non_subunit_name='stdout')
    result = testtools.StreamToExtendedDecorator(verify_result)
    accumulator = FileAccumulator()
    result = testtools.StreamResultRouter(result)
    result.add_rule(accumulator, 'test_id', test_id=None)
    result.startTestRun()
    suite.run(result)
    for bytes_io in accumulator.route_codes.values(): # v1 processing
        bytes_io.seek(0)
        suite = subunit.ProtocolTestCase(bytes_io)
        suite.run(html_result)
    result.stopTestRun()
    print result.test_list


if __name__ == '__main__':
    main()
