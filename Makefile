all: build

build: clean
	python setup.py bdist_wheel

clean:
	rm -rf *.egg-info/ build/ dist/
