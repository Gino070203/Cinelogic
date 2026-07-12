.PHONY: build-scala run install setup

build-scala:
	cd scala && sbt assembly

run:
	cd python && uvicorn api.main:app --reload

install:
	pip install -r python/requirements.txt

setup: install build-scala
