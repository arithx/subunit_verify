#!/usr/bin/python
#

import argparse
import collections
import io
import json
import re
import traceback

import subunit
import testtools


class VerifyOutput(testtools.TestResult):
    def __init__(self, test_file='test_list'):
        super(VerifyOutput, self).__init__()
        self.test_list = {line: {"status": "Not Ran", "message": None}
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

        if "setUpClass" in output:  # a fixture failure
            pat = re.compile("\((.*)\)")
            match = pat.findall(output)
            if match:
                module = match[0].rsplit(".", 1)[0]
                for key in self.test_list:
                    if key.startswith(module):
                        self.test_list[key]["status"] = "Skip"

    def addError(self, test, err):
        output = test.shortDescription() or test.id()
        if output in self.test_list:
            self.test_list[output]["status"] = "Error"
            self.test_list[output]["message"] = self.formatErr(err)

    def addFailure(self, test, err):
        output = test.shortDescription() or test.id()
        if output in self.test_list:  # if the test itself failed
            self.test_list[output]["status"] = "Fail"
            self.test_list[output]["message"] = self.formatErr(err)

        if "setUpClass" in output:  # a fixture failure
            pat = re.compile("\((.*)\)")
            match = pat.findall(output)
            if match:
                module = match[0].rsplit(".", 1)[0]
                for key in self.test_list:
                    if key.startswith(module):
                        self.test_list[key]["status"] = "Fixture Failure"

    def formatErr(self, err):
        exctype, value, tb = err
        return ''.join(traceback.format_exception(exctype, value, tb))

    def stopTestRun(self):
        super(VerifyOutput, self).stopTestRun()

    def startTestRun(self):
        super(VerifyOutput, self).startTestRun()

    def print_stats(self):
        print "====="
        print "Stats"
        print "====="
        print " - Total: {0}".format(len(self.test_list))
        print " - Passed: {0}".format(sum([
            1 for key, val in self.test_list.iteritems()
            if val["status"] == "Pass"]))
        print " - Failed: {0}".format(sum([
            1 for key, val in self.test_list.iteritems()
            if val["status"] == "Fail"]))
        print " - Errored: {0}".format(sum([
            1 for key, val in self.test_list.iteritems()
            if val["status"] == "Error"]))
        print " - Skipped: {0}".format(sum([
            1 for key, val in self.test_list.iteritems()
            if val["status"] == "Skip"]))
        print " - Fixture Failures: {0}".format(sum([
            1 for key, val in self.test_list.iteritems()
            if val["status"] == "Fixture Failure"]))
        print " - Not Ran: {0}".format(sum([
            1 for key, val in self.test_list.iteritems()
            if val["status"] == "Not Ran"]))


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

        super(VerifyArgumentParser, self).__init__(
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
            help="The output file name for the json.")


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
    for bytes_io in accumulator.route_codes.values():  # v1 processing
        bytes_io.seek(0)
        suite = subunit.ProtocolTestCase(bytes_io)
        suite.run(verify_result)
    result.stopTestRun()

    verify_result.print_stats()
    if output_file:
        with open(output_file, 'w') as outfile:
            outfile.write(json.dumps(verify_result.test_list))


def entry_point():
    cl_args = VerifyArgumentParser().parse_args()
    verify_subunit(
        cl_args.subunit, cl_args.test_list,
        cl_args.non_subunit_name, cl_args.output_file)
