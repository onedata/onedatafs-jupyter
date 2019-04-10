.PHONY: readme
readme:
	pandoc --from=markdown --to=rst --output=README.rst README.md

.PHONY: release
release: readme
	python setup.py sdist bdist_wheel

.PHONY: test
test:
	nosetests --with-coverage --cover-erase --logging-level=ERROR --cover-package=fs_onedatafs -a "!slow" fs_onedatafs/tests
	rm .coverage

.PHONY: slowtest
slowtest:
	nosetests --with-coverage --cover-erase --logging-level=ERROR --cover-package=fs_onedatafs fs_onedatafs/tests
	rm .coverage

.PHONY: testall
testall:
	tox

.PHONY: docs
docs:
	cd docs && make html
	python -c "import os, webbrowser; webbrowser.open('file://' + os.path.abspath('./docs/_build/html/index.html'))"
