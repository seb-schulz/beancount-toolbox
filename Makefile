.PHONY: test
test:
	pytest -s

.PHONY: watch
watch:
	/bin/bash -c "while true; do $(MAKE) test ; sleep 2 && inotifywait -r -e modify tests beancount_toolbox; done"

.PHONY: lint
lint:
	ruff check

.PHONY: beancount_toolbox/data/beancount-toolbox-export-schema.json
beancount_toolbox/data/beancount-toolbox-export-schema.json:
	python3 -c 'from beancount_toolbox.cli.export import RootConfig; from json import dumps; print(dumps(RootConfig.model_json_schema()))' | jq '.' > $@

.PHONY: setup
setup:
	./scripts/$@.sh
