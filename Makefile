test:
	@tox --recreate
	@tox

changelog: CHANGELOG.md
	python setup.py develop
	sh ./.scripts/generate_changelog.sh

release:
	python3 -m build --wheel
	python -m build --sdist
	twine upload dist/* --verbose
