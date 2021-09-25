.PHONY: all build clean pyclean test

all: build

build: clean
	python setup.py bdist_wheel

clean:
	rm -rf *.egg-info/ build/ dist/

pyclean:
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

test:
	python -m unittest discover -s afb/ -p '*_test.py'
