clean:
	rm -rf *.egg *.egg-info .tox .benchmarks .cache pytestdebug.log \
		.coverage dist build .eggs
	find . -name "*.pyc" -exec rm -rf {} \;
	find . -name "__pycache__" -exec rm -rf {} \;

submit:
	python setup.py sdist upload