from setuptools import setup, find_packages

# parse from pipenv files
from pipenv.project import Project
from pipenv.utils import convert_deps_to_pip
pfile = Project(chdir=False).parsed_pipfile
requirements = convert_deps_to_pip(pfile['packages'], r=False)
test_requirements = convert_deps_to_pip(pfile['dev-packages'], r=False)

setup(
    name="bottlecap",
    description="Framework for implementing APIs with Bottle",
    author='Cal Leeming',
    author_email='cal@iops.io',
    url='https://github.com/foxx/bottlecap',
    keywords=['bottle', 'bottlecap'],
    version="1.0",
    packages=['bottlecap'],
    setup_requires=[
        'pytest-runner>=2.6',
        'yanc>=0.3'
    ],
    tests_require=test_requirements
    install_requires=requirements,
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4'
    ]
)
