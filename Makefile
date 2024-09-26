.PHONY: test
test:
	pytest -s

.PHONY: lint
lint:
	ruff check

.PHONY: beancount_toolbox/data/beancount-toolbox-export-schema.json
beancount_toolbox/data/beancount-toolbox-export-schema.json:
	python3 -c 'from beancount_toolbox.cli.export import RootConfig; from json import dumps; print(dumps(RootConfig.model_json_schema()))' | jq '.' > $@

.PHONY: setup
setup:
	./scripts/$@.sh
