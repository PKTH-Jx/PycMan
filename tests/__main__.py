"""Run framework checks, then score a cumulative prefix of student tasks."""

import argparse
import sys
import unittest

from . import test_framework

# Points per stage.
STAGE_POINTS = {'S1': 14, 'S2': 12, 'S3': 14, 'S4': 8, 'S5': 12}


def run_suite(suite: unittest.TestSuite) -> unittest.TestResult:
    return unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)


def stage_suite(stage: str) -> unittest.TestSuite:
    from . import test_basic

    loader = unittest.TestLoader()
    names = [name for name in loader.getTestCaseNames(test_basic.PublicTaskTest)
             if name.startswith(f'test_{stage.lower()}_')]
    if not names:
        raise RuntimeError(f'No public tests found for {stage}')
    return unittest.TestSuite(test_basic.PublicTaskTest(name) for name in names)


def integration_suite(stage: str) -> unittest.TestSuite:
    from . import test_basic

    return unittest.TestSuite([
        test_basic.BasicIntegrationTest(f'test_integration_{stage.lower()}')
    ])


def complete(result: unittest.TestResult, expected: int) -> bool:
    return result.testsRun == expected and result.wasSuccessful() and not result.skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Check and score PycMan tasks')
    parser.add_argument('target', nargs='?', default='all',
                        help='framework, all, or S1 through S5 (cumulative)')
    args = parser.parse_args(argv)
    target = args.target.upper()
    if target not in ('FRAMEWORK', 'ALL', *STAGE_POINTS):
        parser.error('target must be framework, all, or S1 through S5')

    print('Framework integrity tests')
    framework_suite = unittest.defaultTestLoader.loadTestsFromModule(test_framework)
    framework_count = framework_suite.countTestCases()
    if framework_count == 0:
        print('No framework tests found. Student tests were not run.')
        return 2
    framework_result = run_suite(framework_suite)
    if not complete(framework_result, framework_count):
        print('Framework tests failed. Student tests were not run; no score was assigned.')
        return 2
    if target == 'FRAMEWORK':
        return 0

    stages = list(STAGE_POINTS)
    if target != 'ALL':
        stages = stages[:stages.index(target) + 1]

    earned = 0
    maximum = sum(STAGE_POINTS[stage] for stage in stages)
    all_passed = True
    for stage in stages:
        suite = stage_suite(stage)
        expected = suite.countTestCases()
        print(f'\n{stage} student tests')
        result = run_suite(suite)
        public_passed = complete(result, expected)
        integration_passed = False
        integration_status = 'skipped'
        if public_passed:
            print(f'\n{stage} cumulative game check')
            cumulative = integration_suite(stage)
            cumulative_result = run_suite(cumulative)
            integration_passed = complete(cumulative_result, cumulative.countTestCases())
            integration_status = 'passed' if integration_passed else 'failed'
        passed = public_passed and integration_passed
        points = STAGE_POINTS[stage] if passed else 0
        earned += points
        all_passed &= passed
        print(f'{stage}: {points}/{STAGE_POINTS[stage]} points '
              f'({expected - len(result.failures) - len(result.errors) - len(result.skipped)}/{expected} '
              f'public tests passed; cumulative check {integration_status})')

    print(f'\nBasic task score: {earned}/{maximum}')
    return 0 if all_passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
