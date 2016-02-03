#!/usr/bin/python
#

import argparse
import collections
import io
import pprint
import sys
import traceback

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

    def __init__(self, non_subunit_name='stdout'):
        super(FileAccumulator, self).__init__()
        self.route_codes = collections.defaultdict(io.BytesIO)
        self.non_subunit_name = non_subunit_name

    def status(self, **kwargs):
        if kwargs.get('file_name') != self.non_subunit_name:
            return
        file_bytes = kwargs.get('file_bytes')
        if not file_bytes:
            return
        route_code = kwargs.get('route_code')
        stream = self.route_codes[route_code]
        stream.write(file_bytes)


class VerifyArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        desc = "Verifies status of tests against subunit output."
        usage_string = """
            subunit-verify [-s/--subunit] [-t/--test-list]
                [-n/--non-subunit-name] [-o/--output-file]
        """

        super (VerifyArgumentParser, self).__init__(
            usage=usage_string, description=desc)

        self.prog = "Argument Parser"

        self.add_argument(
            "-s", "--subunit", metavar="<subunit file>",
            default=None, help="The path to the subunit output file.")

        self.add_argument(
            "-t", "--test-list", metavar="<test list file>", default=None,
            help="The path to the test list file to be verified.")

        # This defaults to stdout as that's the tempest convention
        self.add_argument(
            "-n", "--non-subunit-name", metavar="<non subunit name>",
            default="stdout",
            help="The name used in subunit to describe the file contents.")

        self.add_argument(
            "-o", "--output-file", metavar="<output file>", default=None,
            help="The output file name, if not given defaults to stdout.")


def verify_subunit(subunit_file, test_list, non_subunit_name, output_file):
    verify_result = VerifyOutput(test_list)
    stream = open(subunit_file, 'rb')
    suite = subunit.ByteStreamToStreamResult(
        stream, non_subunit_name=non_subunit_name)
    result = testtools.StreamToExtendedDecorator(verify_result)
    accumulator = FileAccumulator(non_subunit_name)
    result = testtools.StreamResultRouter(result)
    result.add_rule(accumulator, 'test_id', test_id=None)
    result.startTestRun()
    suite.run(result)
    for bytes_io in accumulator.route_codes.values(): # v1 processing
        bytes_io.seek(0)
        suite = subunit.ProtocolTestCase(bytes_io)
        suite.run(verify_result)
    result.stopTestRun()

    if not output_file:
        # using pformat over pprint to keep consistency between stdout & file
        print pprint.pformat(result.test_list)
    else:
        with open(output_file, 'w') as outfile:
            outfile.write(pprint.pformat(test_list))


def entry_point():
    cl_args = VerifyArgumentParser().parse_args()
    verify_subunit(
        cl_args.subunit, cl_args.test_list,
        cl_args.non_subunit_name, cl_args.output_file)
