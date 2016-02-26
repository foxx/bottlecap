from setuptools import setup, find_packages

base_requirements = [
    'werkzeug>=0.11',
    'click>=6.2',
    'six>=1.10',
    'bottle>=0.12',
    'helpful>=0.8',
    'webtest>=2.0'
]

setup(
    name="bottlecap",
    description="Extras for Bottle",
    author='Cal Leeming',
    author_email='cal@iops.io',
    url='https://github.com/imsofly/bottlecap',
    keywords=['bottle', 'bottlecap'],
    version="0.8.0",
    packages=['bottlecap'],
    setup_requires=[
        'pytest-runner>=2.6',
        'yanc>=0.3'
    ],
    tests_require=[
        "pytest>=2.8",
        "pytest-cov>=2.2",
        "pytest-benchmark>=3.0",
        "pytest-raisesregexp>=2.1",
        "python-coveralls>=2.6",
        "tox>=2.3"
    ],
    install_requires=base_requirements,
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4'
    ]
)
