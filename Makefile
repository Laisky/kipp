test:
	@tox --recreate
	@tox

changelog: CHANGELOG.md
	python setup.py develop
	sh ./.scripts/generate_changelog.sh
