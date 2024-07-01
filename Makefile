COVERAGE_FOLDER := "src_folder"

run-tests:
	pytest tests/${TESTS_FOLDER} -rA --cov=${COVERAGE_FOLDER} --cov-report term-missing --junitxml=report.xml
#	--cov-report term-missing --cov-report xml:coverage.xml --cov-append

unit-tests:
	make run-tests TESTS_FOLDER="unit"

e2e-tests:
	make run-tests TESTS_FOLDER="e2e"

test:
	pytest tests -rA --cov=${COVERAGE_FOLDER} --cov-report term-missing --junitxml=report.xml --asyncio-mode=auto

lint:
	pre-commit install
	pre-commit run --all-files # --show-diff-on-failure

patch:
	bump2version patch

minor:
	bump2version minor

migration:
	alembic revision -m "$(msg)" --autogenerate

pull:
	git switch master && git pull --rebase

up:
	docker-compose -f docker-compose-local.yaml up -d --force-recreate

rm:
	docker-compose -f docker-compose-local.yaml rm -sf

db-recreate:
	docker-compose -f docker-compose-local.yaml rm db -sf
	docker-compose -f docker-compose-local.yaml up db -d
