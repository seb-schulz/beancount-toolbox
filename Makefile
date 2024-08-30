.PHONY: test
test:
	pytest -s

.PHONY: beancount_toolbox/data/beancount-toolbox-export-schema.json
beancount_toolbox/data/beancount-toolbox-export-schema.json:
	python3 -c 'from beancount_toolbox.cli.export import RootConfig; from json import dumps; print(dumps(RootConfig.model_json_schema()))' > $@
