VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

$(VENV):
	python3 -m venv $(VENV)

install: $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run: $(VENV)
	$(PYTHON) -m itsreg_builder $(ARGS)

clean:
	rm -rf $(VENV)
