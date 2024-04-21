.PHONY: refresh build install build_dist json release lint test clean

refresh: clean build install lint

build:
	python -m build

install:
	pip install .

build_dist:
	make clean
	python -m build
	pip install dist/*.whl
	make test

release:
	python -m twine upload dist/*

lint:
	flake8 src/ tests/ --count --ignore=W503 --max-line-length=127 --statistics
	mypy src/

test:
	python -m unittest

clean:
	rm -rf __pycache__
	rm -rf tests/__pycache__
	rm -rf src/coredumpy/__pycache__
	rm -rf build
	rm -rf dist
	rm -rf coredumpy.egg-info
	rm -rf src/coredumpy.egg-info
	pip uninstall -y coredumpy