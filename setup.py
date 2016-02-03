from setuptools import setup, find_packages

setup(
    name='subunit-verify',
    version='0.0.1',
    description='Verifies status of tests against subunit output.',
    author='Stephen Lowrie',
    author_email='stephen.lowrie@rackspace.com',
    url='https://github.com/arithx/subunit_verify',
    packages=find_packages(exclude=('tests*', 'docs')),
    install_requires=open('requirements.txt').read(),
    license=open('LICENSE').read(),
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: Other/Proprietary License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ),
    entry_points={
        'console_scripts': [
            'subunit-verify = subunit_verify.verify:entry_point']})
