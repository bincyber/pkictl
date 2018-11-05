VERSION=$(shell awk -F\" '/version =/ { print $$2 }' setup.py)
VAULT_VERSION=0.11.4
VAULT_URL=https://localhost:8200
PKICTL=python -m pkictl
E2E_YAML_FILE=pkictl/tests/manifests/pki.yaml
E2E_YAML_DIR=pkictl/tests/manifests/multi
E2E_TEST_CMD=VAULT_TOKEN=`cat .vault-token` $(PKICTL) -d apply -u $(VAULT_URL) --tls-skip-verify

help:
	@echo "Please use \`make <target>' where <target> is one of:"
	@echo "  dev                 to create virtualenv and install dependencies"
	@echo "  lint                to lint the codebase using flake8"
	@echo "  tests               to run the test suit"
	@echo "  static-analysis     to perform static analysis of the codebase using mypy"
	@echo "  scan                to run a security scan of the codebase using bandit"
	@echo "  e2e-test            to run end-to-end tests"

dev:
	pipenv install --python 3.6 --dev

lint:
	flake8 --statistics pkictl/*

static-analysis:
	mypy pkictl/*

test:
	nose2 -v -s pkictl/tests/ --with-coverage --coverage-report html

scan:
	bandit -s B322 -r pkictl/ --exclude pkictl/tests/

e2e-test:
	$(PKICTL) init -u $(VAULT_URL) --tls-skip-verify

	# apply runs twice to verify idempotency
	$(E2E_TEST_CMD) -f $(E2E_YAML_DIR) && $(E2E_TEST_CMD) -f $(E2E_YAML_DIR)
	$(E2E_TEST_CMD) -f $(E2E_YAML_FILE) && $(E2E_TEST_CMD) -f $(E2E_YAML_FILE)

clean:
	find . -name "*pyc" -exec rm -f "{}" \;
	rm -f .vault-token vault.log
	rm -rf htmlcov .coverage .mypy_cache .eggs pkictl.egg-info build dist

package:
	python setup.py sdist bdist_wheel

upload-package:
	twine upload dist/*

build-container:
	docker build -t pkictl:$(VERSION) .

build-vault-container:
	docker build --build-arg VAULT_VERSION=$(VAULT_VERSION) -t vault:$(VAULT_VERSION) pkictl/tests/e2e

run-vault-container:
	docker run --name hashicorp-vault-$(VAULT_VERSION) -d -p 8200:8200 vault:$(VAULT_VERSION)

stop-vault-container:
	docker stop hashicorp-vault-$(VAULT_VERSION) || /bin/true
	docker system prune -f
