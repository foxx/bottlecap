PACKAGE_NAME = bottlecap
PIPENV_RUN := pipenv run
DOCKER_OPTS := --rm -t -i -v `pwd`:/app

all:

test:
	$(PIPENV_RUN) python3 -m pytest

test_pdb:
	$(PIPENV_RUN) python3 -m pytest --pdb

shell:
	pipenv shell

pyshell:
	pipenv run ipython

dbuild:
	docker build -t $(PACKAGE_NAME):dev -f Dockerfile.dev .

dshell: dbuild
	docker run $(DOCKER_OPTS) $(PACKAGE_NAME):dev /bin/bash -i


clean:
	rm -rf *.egg *.egg-info .tox .benchmarks .cache pytestdebug.log \
		.coverage dist build .eggs
	find . -name "*.pyc" -exec rm -rf {} \;
	find . -name "__pycache__" -exec rm -rf {} \;

submit:
	python setup.py sdist upload
